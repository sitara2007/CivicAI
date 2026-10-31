import sys
import types
import zlib
from unittest.mock import MagicMock, AsyncMock

import numpy as np
import pytest

from app.api.deps import get_db_session
from app.core.config import get_settings
from app.db.models import Decision, Document, DocumentStatus
from app.main import app
from app.services.audit.chain_store import AuditEntry

EMBEDDING_DIM = 384


def _fake_encode(sentences, *args, **kwargs):
    single = isinstance(sentences, str)
    items = [sentences] if single else list(sentences)
    vectors = np.stack([
        np.random.default_rng(zlib.crc32(s.encode("utf-8"))).random(
            EMBEDDING_DIM, dtype=np.float32
        )
        for s in items
    ])
    return vectors[0] if single else vectors


def _make_fake_model(*args, **kwargs):
    model = MagicMock(name="FakeSentenceTransformer")
    model.encode.side_effect = _fake_encode
    model.get_sentence_embedding_dimension.return_value = EMBEDDING_DIM
    return model


_stub = types.ModuleType("sentence_transformers")
_stub.SentenceTransformer = MagicMock(side_effect=_make_fake_model)
sys.modules["sentence_transformers"] = _stub


@pytest.fixture(autouse=True)
def no_hf_network(monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    monkeypatch.setenv("DATABASE_ENABLED", "false")
    monkeypatch.setenv("MOCK_LLM", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def mock_postgres_audit_store(monkeypatch):
    from app.api.v1 import process

    mock_store = AsyncMock()

    # YAHAN FIX HUA HAI: 64 characters ka fake hash banaya (SHA-256 length)
    fake_64_hash = "a" * 64

    mock_store.append.return_value = AuditEntry(
        sequence=1,
        prev_hash="genesis",
        payload={},
        hash=fake_64_hash
    )

    monkeypatch.setattr(
        process,
        "PostgresAuditStore",
        lambda session: mock_store
    )


@pytest.fixture(autouse=True)
def no_database_connection(monkeypatch):
    class _InMemorySession:
        def __init__(self):
            self.documents = {}
            self.decisions = {}
            self.entity_counts = {}

        async def commit(self):
            pass

    class _InMemoryDocumentRepository:
        def __init__(self, session):
            self._session = session

        async def create_document(self, *, document_id, trace_id, raw_text, source_type):
            self._session.documents[document_id] = Document(
                id=document_id,
                trace_id=trace_id,
                raw_text=raw_text,
                source_type=source_type,
            )

        async def mark_processing(self, document_id):
            self._session.documents[document_id].status = DocumentStatus.PROCESSING

        async def save_redacted(self, *, document_id, trace_id, redacted_text, entity_count):
            self._session.entity_counts[trace_id] = entity_count

        async def save_decision(
            self,
            *,
            document_id,
            trace_id,
            decision,
            hop_count,
            requires_review,
            latency_ms,
        ):
            self._session.decisions[document_id] = Decision(
                document_id=document_id,
                trace_id=trace_id,
                category=decision.category,
                priority=decision.priority,
                department=decision.department,
                confidence=decision.confidence,
                decision_rationale=decision.decision_rationale,
                summary=decision.summary,
                hop_count=hop_count,
                requires_review=requires_review,
            )
            self._session.documents[document_id].status = DocumentStatus.COMPLETED

        async def mark_dlq(self, *, document_id, trace_id, reason, hop_count):
            self._session.documents[document_id].status = DocumentStatus.DLQ

        async def get_document_with_decision(self, trace_id):
            document = next(
                (
                    item
                    for item in self._session.documents.values()
                    if item.trace_id == trace_id
                ),
                None,
            )
            if document is None:
                return None, None
            return document, self._session.decisions.get(document.id)

        async def get_redacted_entity_count(self, trace_id):
            return self._session.entity_counts.get(trace_id)

    from app.services import process_service

    session = _InMemorySession()
    monkeypatch.setattr(
        process_service, "DocumentRepository", _InMemoryDocumentRepository
    )

    async def _no_database_session():
        yield session

    app.dependency_overrides[get_db_session] = _no_database_session
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db_session, None)
