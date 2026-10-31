"""Phase 4 — audit hash chain and schema tests."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from app.db.models import AuditAction, AuditLog
from app.services.audit import GENESIS_HASH, compute_prev_hash


def test_genesis_hash() -> None:
    assert GENESIS_HASH == hashlib.sha256(b"GENESIS").hexdigest()


def test_hash_chain_links_entries() -> None:
    first = AuditLog(
        id=uuid.uuid4(),
        trace_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        action=AuditAction.INGESTED,
        event_metadata={"source_type": "text"},
        prev_hash=GENESIS_HASH,
        timestamp=datetime.now(UTC),
    )
    second_hash = compute_prev_hash(first)
    assert len(second_hash) == 64
    assert second_hash != GENESIS_HASH

    second = AuditLog(
        id=uuid.uuid4(),
        trace_id=first.trace_id,
        document_id=first.document_id,
        action=AuditAction.REDACTED,
        event_metadata={"pii_entities_masked": 2},
        prev_hash=second_hash,
        timestamp=datetime.now(UTC),
    )
    third_hash = compute_prev_hash(second)
    assert third_hash != second_hash


def test_history_response_schema() -> None:
    from app.schemas.process import HistoryItem, HistoryResponse, SourceType

    item = HistoryItem(
        trace_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        status="completed",
        source_type=SourceType.TEXT,
        created_at=datetime.now(UTC),
    )
    response = HistoryResponse(items=[item], total=1, page=1, page_size=20, dlq_count=0)
    assert response.dlq_count == 0
    assert len(response.items) == 1
