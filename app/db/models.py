"""Database model compatibility exports used by tests and services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, func, text
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

    sequence: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False
    )
    prev_hash: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    hash: Mapped[str] = mapped_column(String, nullable=False)


class SQLDocument(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    trace_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    redacted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    pii_entities_masked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dlq_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    hop_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SQLDecision(Base):
    __tablename__ = "decisions"

    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    document_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    trace_id: Mapped[UUID] = mapped_column(nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[str] = mapped_column(String, nullable=False)
    department: Mapped[str] = mapped_column(String, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    decision_rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    hop_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requires_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ZohoToken(Base):
    __tablename__ = "zoho_tokens"

    id: Mapped[UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    scope: Mapped[str] = mapped_column(String, nullable=False, default="")
    dc: Mapped[str] = mapped_column(String, nullable=False, default="in")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
