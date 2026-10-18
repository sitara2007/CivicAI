"""Async persistence operations for processed documents."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Decision, Document, DocumentStatus
from app.schemas.process import DocumentCategory, Priority, SourceType


class DocumentRepository:
	"""Persist documents and their classification using the caller's transaction."""

	def __init__(self, session: AsyncSession) -> None:
		self._session = session

	async def create_document(
		self,
		*,
		document_id: UUID,
		trace_id: UUID,
		raw_text: str,
		source_type: SourceType,
	) -> None:
		await self._session.execute(
			text(
				"""INSERT INTO documents
				   (id, trace_id, raw_text, source_type, status, pii_entities_masked)
				   VALUES (:id, :trace_id, :raw_text, :source_type, :status, 0)"""
			),
			{
				"id": document_id,
				"trace_id": trace_id,
				"raw_text": raw_text,
				"source_type": source_type.value,
				"status": DocumentStatus.RECEIVED.value,
			},
		)
		await self._session.flush()

	async def mark_processing(self, document_id: UUID) -> None:
		await self._session.execute(
			text("UPDATE documents SET status = :status WHERE id = :id"),
			{"status": DocumentStatus.PROCESSING.value, "id": document_id},
		)
		await self._session.flush()

	async def save_redacted(
		self,
		*,
		document_id: UUID,
		trace_id: UUID,
		redacted_text: str,
		entity_count: int,
	) -> None:
		await self._session.execute(
			text(
				"""UPDATE documents
				   SET redacted_text = :redacted_text,
					   pii_entities_masked = :entity_count
				   WHERE id = :id AND trace_id = :trace_id"""
			),
			{
				"redacted_text": redacted_text,
				"entity_count": entity_count,
				"id": document_id,
				"trace_id": trace_id,
			},
		)
		await self._session.flush()

	async def save_decision(
		self,
		*,
		document_id: UUID,
		trace_id: UUID,
		decision: Any,
		hop_count: int,
		requires_review: bool,
		latency_ms: float,
	) -> None:
		await self._session.execute(
			text(
				"""INSERT INTO decisions
				   (document_id, trace_id, category, priority, department, confidence,
					decision_rationale, summary, hop_count, requires_review, latency_ms)
				   VALUES (:document_id, :trace_id, :category, :priority, :department,
						   :confidence, :decision_rationale, :summary, :hop_count,
						   :requires_review, :latency_ms)"""
			),
			{
				"document_id": document_id,
				"trace_id": trace_id,
				"category": decision.category.value,
				"priority": decision.priority.value,
				"department": decision.department,
				"confidence": decision.confidence,
				"decision_rationale": decision.decision_rationale,
				"summary": decision.summary,
				"hop_count": hop_count,
				"requires_review": requires_review,
				"latency_ms": latency_ms,
			},
		)
		await self._session.execute(
			text("UPDATE documents SET status = :status WHERE id = :id"),
			{"status": DocumentStatus.COMPLETED.value, "id": document_id},
		)
		await self._session.flush()

	async def mark_dlq(
		self,
		*,
		document_id: UUID,
		trace_id: UUID,
		reason: str,
		hop_count: int | None,
	) -> None:
		await self._session.execute(
			text(
				"""UPDATE documents
				   SET status = :status, dlq_reason = :reason, hop_count = :hop_count
				   WHERE id = :id AND trace_id = :trace_id"""
			),
			{
				"status": DocumentStatus.DLQ.value,
				"reason": reason,
				"hop_count": hop_count,
				"id": document_id,
				"trace_id": trace_id,
			},
		)
		await self._session.flush()

	async def get_document_with_decision(
		self, trace_id: UUID
	) -> tuple[Document | None, Decision | None]:
		result = await self._session.execute(
			text(
				"""SELECT d.id, d.trace_id, d.raw_text, d.source_type, d.status,
						  d.created_at, c.category, c.priority, c.department,
						  c.confidence, c.decision_rationale, c.summary, c.hop_count,
						  c.requires_review, c.created_at AS decision_created_at
				   FROM documents AS d
				   LEFT JOIN decisions AS c ON c.document_id = d.id
				   WHERE d.trace_id = :trace_id"""
			),
			{"trace_id": trace_id},
		)
		row = result.mappings().one_or_none()
		if row is None:
			return None, None

		document = Document(
			id=row["id"],
			trace_id=row["trace_id"],
			raw_text=row["raw_text"],
			source_type=SourceType(row["source_type"]),
			status=DocumentStatus(row["status"]),
			created_at=row["created_at"],
		)
		if row["category"] is None:
			return document, None

		decision = Decision(
			document_id=document.id,
			trace_id=document.trace_id,
			category=DocumentCategory(row["category"]),
			priority=Priority(row["priority"]),
			department=row["department"],
			confidence=row["confidence"],
			decision_rationale=row["decision_rationale"],
			summary=row["summary"],
			hop_count=row["hop_count"],
			requires_review=row["requires_review"],
			created_at=row["decision_created_at"],
		)
		return document, decision

	async def get_redacted_entity_count(self, trace_id: UUID) -> int | None:
		result = await self._session.execute(
			text(
				"SELECT pii_entities_masked FROM documents WHERE trace_id = :trace_id"
			),
			{"trace_id": trace_id},
		)
		count = result.scalar_one_or_none()
		return int(count) if count is not None else None
