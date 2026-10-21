"""Pydantic v2 schemas for /api/v1/process — PRD Appendix A."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceType(StrEnum):
    TEXT = "text"
    PDF = "pdf"
    FORM = "form"

class DocumentCategory(StrEnum):
    COMPLAINT = "Complaint"
    REQUEST = "Request"
    REPORT = "Report"
    OTHER = "Other"


class Priority(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class ProcessRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    text: Annotated[str, Field(min_length=1, max_length=100_000)]
    source_type: SourceType = SourceType.TEXT

    @field_validator("text")
    @classmethod
    def reject_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty")
        return v


class DecisionOutput(BaseModel):
    """Instructor response_model — FR-2.1 through FR-2.5."""

    model_config = ConfigDict(extra="forbid")

    category: DocumentCategory
    priority: Priority
    department: Annotated[str, Field(min_length=1, max_length=128)]
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    decision_rationale: Annotated[str, Field(min_length=10, max_length=4000)]
    summary: Annotated[str, Field(min_length=10, max_length=1000)]


class ProcessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trace_id: UUID
    document_id: UUID
    status: str
    decision: DecisionOutput | None = None
    requires_review: bool = False
    hop_count: int | None = None
    pii_entities_masked: int = 0
    redacted_text: str | None = None
    audit_hash: str | None = None
    created_at: datetime


class ProcessPollResponse(BaseModel):
    """GET /api/v1/process/{trace_id}"""

    model_config = ConfigDict(from_attributes=True)

    trace_id: UUID
    document_id: UUID
    status: str
    source_type: SourceType
    decision: DecisionOutput | None = None
    hop_count: int | None = None
    requires_review: bool = False
    pii_entities_masked: int = 0
    created_at: datetime
    completed_at: datetime | None = None


class HistoryItem(BaseModel):
    trace_id: UUID
    document_id: UUID
    status: str
    source_type: SourceType
    category: DocumentCategory | None = None
    priority: Priority | None = None
    department: str | None = None
    confidence: float | None = None
    created_at: datetime


class HistoryResponse(BaseModel):
    items: list[HistoryItem]
    total: int
    page: int
    page_size: int
    dlq_count: int


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_code: str
    message: str
    trace_id: UUID | None = None
