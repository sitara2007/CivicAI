"""Document processing pipeline — sync MVP (Phase 1-4) with async hook (Phase 5+)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.core.config import get_settings
from app.schemas.process import DecisionOutput, SourceType
from app.security.presidio import SanitizationError, sanitize
from app.services.llm import AgenticHopExhausted, LLMService
from app.services.text_utils import enforce_token_limit, normalize_text

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    status: str
    decision: DecisionOutput | None
    requires_review: bool
    hop_count: int = 0
    pii_entities_masked: int = 0
    redacted_text: str | None = None


class PipelineService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._llm = LLMService()

    async def run_sync(
        self,
        *,
        trace_id: uuid.UUID,
        document_id: uuid.UUID,
        text: str,
        source_type: SourceType,
        persist_redacted: Callable[[str, int], Awaitable[None]] | None = None,
    ) -> PipelineResult:
        """Execute ingest → Presidio → LLM → decision (sync path)."""
        _ = document_id, source_type

        try:
            normalized = enforce_token_limit(
                normalize_text(text),
                max_tokens=self._settings.max_document_tokens,
            )
            redacted_text, entity_count = sanitize(normalized)
            if persist_redacted is not None:
                await persist_redacted(redacted_text, entity_count)
            logger.info("pii_redacted", extra={"trace_id": str(trace_id), "entities": entity_count})

            policy_context = self._retrieve_policy_context(redacted_text, trace_id)
            decision, hop_count = self._llm.classify(redacted_text, policy_context=policy_context)
            requires_review = decision.confidence < self._settings.review_confidence_threshold

            return PipelineResult(
                status="completed",
                decision=decision,
                requires_review=requires_review,
                hop_count=hop_count,
                pii_entities_masked=entity_count,
                redacted_text=redacted_text,
            )
        except SanitizationError:
            logger.error("pipeline_sanitization_failed", extra={"trace_id": str(trace_id)})
            return PipelineResult(status="dlq", decision=None, requires_review=False)
        except AgenticHopExhausted as exc:
            logger.error(
                "pipeline_hop_exhausted",
                extra={"trace_id": str(trace_id), "hop_count": exc.hop_count},
            )
            return PipelineResult(
                status="dlq",
                decision=None,
                requires_review=False,
                hop_count=exc.hop_count,
            )

    def _retrieve_policy_context(self, query: str, trace_id: uuid.UUID) -> str:
        if not self._settings.rag_enabled:
            return ""

        try:
            from app.services.rag.retriever import retrieve

            chunks = retrieve(query, top_k=self._settings.rag_top_k)
        except Exception as exc:
            logger.warning(
                "rag_context_unavailable",
                extra={"trace_id": str(trace_id), "error": str(exc)},
            )
            return ""

        context = "\n\n".join(chunk["text"] for chunk in chunks if chunk.get("text"))
        return context[: self._settings.rag_context_max_chars]

    async def enqueue_async(
        self,
        *,
        trace_id: uuid.UUID,
        document_id: uuid.UUID,
        text: str,
        source_type: SourceType,
    ) -> PipelineResult:
        """Phase 5+: dispatch to Celery instead of sync processing."""
        from app.tasks.process_document import process_document_task

        redacted_text, _ = sanitize(text)
        process_document_task.delay(
            str(trace_id),
            str(document_id),
            redacted_text,
            source_type.value,
        )
        return PipelineResult(status="pending", decision=None, requires_review=False)
