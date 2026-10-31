"""POST /api/v1/process and GET /api/v1/process/{trace_id}."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import get_settings
from app.core.ids import new_uuid7
from app.schemas.process import (
    ErrorResponse,
    ProcessPollResponse,
    ProcessRequest,
    ProcessResponse,
)
from app.services.audit.chain_store import AuditChainError, audit_store
from app.services.pipeline import PipelineService

router = APIRouter(prefix="/api/v1", tags=["process"])
logger = logging.getLogger(__name__)


@router.post(
    "/process",
    response_model=ProcessResponse,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def process_document(
    body: ProcessRequest,
    response: Response,
    session: AsyncSession | None = Depends(get_db_session),
) -> ProcessResponse:
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Malformed or empty payload")

    trace_id = new_uuid7()
    document_id = new_uuid7()
    settings = get_settings()
    started = time.perf_counter()

    if settings.sync_mode:
        if session is not None:
            from app.services.process_service import ProcessService

            result = await ProcessService(session).process(
                trace_id=trace_id,
                document_id=document_id,
                text=body.text,
                source_type=body.source_type,
            )
        else:
            result = await PipelineService().run_sync(
                trace_id=trace_id,
                document_id=document_id,
                text=body.text,
                source_type=body.source_type,
            )
    else:
        pipeline = PipelineService()
        result = await pipeline.enqueue_async(
            trace_id=trace_id,
            document_id=document_id,
            text=body.text,
            source_type=body.source_type,
        )
        response.status_code = status.HTTP_202_ACCEPTED

    elapsed_ms = (time.perf_counter() - started) * 1000
    _ = elapsed_ms

    if result.status == "dlq":
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "DLQ_ROUTED",
                "message": "Document failed processing and was routed to DLQ",
                "trace_id": str(trace_id),
            },
        )

    created_at = datetime.now(UTC)
    audit_hash: str | None = None
    if result.status == "completed" and result.decision is not None and result.redacted_text is not None:
        audit_payload = {
            "trace_id": str(trace_id),
            "document_id": str(document_id),
            "redacted_text": result.redacted_text,
            "pii_entities_masked": result.pii_entities_masked,
            "decision": result.decision.model_dump(mode="json"),
            "created_at": created_at.isoformat(),
        }
        try:
            entry = await asyncio.to_thread(audit_store.append, audit_payload)
        except (AuditChainError, OSError, TypeError, ValueError) as exc:
            logger.error("audit_chain_append_failed", extra={"trace_id": str(trace_id), "error": str(exc)})
            raise HTTPException(status_code=500, detail="Audit record could not be written") from exc
        audit_hash = entry.hash

    return ProcessResponse(
        trace_id=trace_id,
        document_id=document_id,
        status=result.status,
        decision=result.decision,
        requires_review=result.requires_review,
        hop_count=result.hop_count or None,
        pii_entities_masked=result.pii_entities_masked,
        redacted_text=result.redacted_text,
        audit_hash=audit_hash,
        created_at=created_at,
    )


@router.get(
    "/process/{trace_id}",
    response_model=ProcessPollResponse,
    responses={404: {"model": ErrorResponse}},
)
async def poll_process(
    trace_id: str,
    session: AsyncSession | None = Depends(get_db_session),
) -> ProcessPollResponse:
    if session is None:
        raise HTTPException(status_code=503, detail="Database persistence is disabled")

    from app.services.process_service import ProcessService

    try:
        parsed_trace_id = uuid.UUID(trace_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid trace_id format") from exc

    result = await ProcessService(session).get_by_trace_id(parsed_trace_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return result
