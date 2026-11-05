"""Celery task — async document processing (Phase 5+)."""

from __future__ import annotations

import logging
import uuid

from app.services.llm import AgenticHopExhausted, LLMService
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


class TransientError(Exception):
    """Retryable Celery failure."""


@celery_app.task(
    bind=True,
    name="process_document",
    queue="govflow",
    autoretry_for=(TransientError,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=300,
    acks_late=True,
)
def process_document_task(
    self,
    trace_id: str,
    document_id: str,
    redacted_text: str,
    source_type: str,
) -> dict[str, str]:
    _ = uuid.UUID(trace_id), uuid.UUID(document_id), source_type
    llm = LLMService()

    try:
        decision, hop_count = llm.classify(redacted_text)
        return {
            "status": "completed",
            "category": decision.category.value,
            "hop_count": str(hop_count),
        }
    except AgenticHopExhausted:
        logger.error(
            "task_dlq", extra={"trace_id": trace_id, "document_id": document_id}
        )
        return {"status": "dlq"}
    except Exception as exc:
        logger.warning("task_transient_error", extra={"error": str(exc)})
        raise TransientError(str(exc)) from exc
