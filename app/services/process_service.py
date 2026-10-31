"""Orchestrates pipeline execution with PostgreSQL persistence — Phase 4."""

from __future__ import annotations

import logging
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.document_repo import DocumentRepository
from app.schemas.process import (
    DecisionOutput,
    DocumentCategory,
    Priority,
    ProcessPollResponse,
    SourceType,
)
from app.services.pipeline import PipelineResult, PipelineService

logger = logging.getLogger(__name__)


class ProcessService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = DocumentRepository(session)
        self._pipeline = PipelineService()

    async def process(
        self,
        *,
        trace_id: uuid.UUID,
        document_id: uuid.UUID,
        text: str,
        source_type: SourceType,
    ) -> PipelineResult:
        started = time.perf_counter()

        await self._repo.create_document(
            document_id=document_id,
            trace_id=trace_id,
            raw_text=text,
            source_type=source_type,
        )
        await self._repo.mark_processing(document_id)

        result = await self._pipeline.run_sync(
            trace_id=trace_id,
            document_id=document_id,
            text=text,
            source_type=source_type,
            persist_redacted=self._persist_redacted_callback(document_id, trace_id),
        )

        elapsed_ms = (time.perf_counter() - started) * 1000

        if result.status == "completed" and result.decision is not None:
            await self._repo.save_decision(
                document_id=document_id,
                trace_id=trace_id,
                decision=result.decision,
                hop_count=result.hop_count,
                requires_review=result.requires_review,
                latency_ms=elapsed_ms,
            )
        elif result.status == "dlq":
            reason = "sanitization_failed" if result.hop_count == 0 else "hop_exhausted"
            await self._repo.mark_dlq(
                document_id=document_id,
                trace_id=trace_id,
                reason=reason,
                hop_count=result.hop_count or None,
            )

        await self._session.commit()
        return result

    def _persist_redacted_callback(
        self, document_id: uuid.UUID, trace_id: uuid.UUID
    ):
        async def _save(redacted_text: str, entity_count: int) -> None:
            await self._repo.save_redacted(
                document_id=document_id,
                trace_id=trace_id,
                redacted_text=redacted_text,
                entity_count=entity_count,
            )

        return _save

    async def get_by_trace_id(self, trace_id: uuid.UUID) -> ProcessPollResponse | None:
        doc, decision = await self._repo.get_document_with_decision(trace_id)
        if doc is None:
            return None

        decision_output: DecisionOutput | None = None
        hop_count: int | None = None
        requires_review = False

        if decision is not None:
            decision_output = DecisionOutput(
                category=DocumentCategory(decision.category.value),
                priority=Priority(decision.priority.value),
                department=decision.department,
                confidence=decision.confidence,
                decision_rationale=decision.decision_rationale,
                summary=decision.summary,
            )
            hop_count = decision.hop_count
            requires_review = decision.requires_review

        pii_count = 0
        audit_meta = await self._repo.get_redacted_entity_count(trace_id)
        if audit_meta is not None:
            pii_count = audit_meta

        return ProcessPollResponse(
            trace_id=doc.trace_id,
            document_id=doc.id,
            status=doc.status.value if hasattr(doc.status, "value") else str(doc.status),
            source_type=doc.source_type,
            decision=decision_output,
            hop_count=hop_count,
            requires_review=requires_review,
            pii_entities_masked=pii_count,
            created_at=doc.created_at,
            completed_at=decision.created_at if decision else None,
        )
