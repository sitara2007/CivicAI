"""Database model compatibility exports used by tests and services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Integer, String, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.schemas.process import SourceType


class AuditAction(StrEnum):
    INGESTED = "ingested"
    REDACTED = "redacted"
    CLASSIFIED = "classified"
    ROUTED_TO_DLQ = "routed_to_dlq"


class DocumentStatus(StrEnum):
    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    DLQ = "dlq"


@dataclass
class Document:
    id: UUID
    trace_id: UUID
    raw_text: str = ""
    source_type: SourceType = SourceType.TEXT
    status: DocumentStatus = DocumentStatus.RECEIVED
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Decision:
    id: UUID = field(default_factory=uuid4)
    document_id: UUID | None = None
    trace_id: UUID | None = None
    category: Any = None
    priority: Any = None
    department: str = ""
    confidence: float = 0.0
    decision_rationale: str = ""
    summary: str = ""
    hop_count: int = 0
    requires_review: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class AuditLog:
    id: UUID
    trace_id: UUID
    document_id: UUID
    action: AuditAction
    event_metadata: dict[str, Any]
    prev_hash: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
class Base(DeclarativeBase):
    pass

class SQLAuditLog(Base):
    __tablename__ = "audit_logs"

    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    prev_hash: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    hash: Mapped[str] = mapped_column(String, nullable=False)
