"""Create the PostgreSQL tables required by DocumentRepository for a pilot."""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings

DDL_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS documents (
        id UUID PRIMARY KEY,
        trace_id UUID NOT NULL UNIQUE,
        raw_text TEXT NOT NULL,
        redacted_text TEXT,
        source_type VARCHAR(16) NOT NULL
            CHECK (source_type IN ('text', 'pdf', 'form')),
        status VARCHAR(16) NOT NULL DEFAULT 'received'
            CHECK (status IN ('received', 'processing', 'completed', 'dlq')),
        pii_entities_masked INTEGER NOT NULL DEFAULT 0
            CHECK (pii_entities_masked >= 0),
        dlq_reason TEXT,
        hop_count INTEGER CHECK (hop_count IS NULL OR hop_count >= 0),
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS decisions (
        document_id UUID PRIMARY KEY REFERENCES documents (id) ON DELETE CASCADE,
        trace_id UUID NOT NULL UNIQUE,
        category VARCHAR(32) NOT NULL
            CHECK (category IN ('Complaint', 'Request', 'Report', 'Other')),
        priority VARCHAR(16) NOT NULL
            CHECK (priority IN ('Low', 'Medium', 'High', 'Critical')),
        department VARCHAR(128) NOT NULL,
        confidence DOUBLE PRECISION NOT NULL
            CHECK (confidence >= 0 AND confidence <= 1),
        decision_rationale TEXT NOT NULL,
        summary TEXT NOT NULL,
        hop_count INTEGER NOT NULL CHECK (hop_count >= 0),
        requires_review BOOLEAN NOT NULL,
        latency_ms DOUBLE PRECISION NOT NULL CHECK (latency_ms >= 0),
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE INDEX IF NOT EXISTS ix_documents_status_created_at
       ON documents (status, created_at)""",
)


async def initialize_database(database_url: str | None = None) -> None:
    """Create missing repository tables without modifying existing tables."""

    url = database_url or get_settings().database_url
    if not url.strip():
        raise RuntimeError("Set DATABASE_URL or POSTGRES_URL before initializing the database")

    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            for statement in DDL_STATEMENTS:
                await connection.execute(text(statement))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(initialize_database())
