"""Real-Postgres tests for the audit hash chain. Skipped if DB is disabled."""
import asyncio
import json

import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine, get_session
from app.services.audit.postgres_store import PostgresAuditStore

def _run(coro):
    async def wrapper():
        try:
            from app.db.models import Base
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            return await coro
        finally:
            await engine.dispose()
    return asyncio.run(wrapper())


pytestmark = pytest.mark.skipif(
    not get_settings().database_enabled, reason="Postgres not enabled"
)


async def _truncate():
    async for s in get_session():
        await s.execute(text("TRUNCATE audit_logs"))
        await s.commit()
        break


async def _append(i: int) -> None:
    async for s in get_session():
        await PostgresAuditStore(s).append({"n": i})
        return  # Exit after the first iteration
    raise RuntimeError("No database session available")

async def _verify():
    async for s in get_session():
        return await PostgresAuditStore(s).verify()
    raise RuntimeError("No session available") 

def test_tamper_detected():
    async def run():
        await _truncate()
        for i in range(3):
            await _append(i)
        assert (await _verify()).ok

        async for s in get_session():
            row = (await s.execute(text(
                "SELECT payload::text FROM audit_logs WHERE sequence=1"))).scalar_one()
            bad = json.loads(row)
            bad["tampered"] = True
            await s.execute(text(
                "UPDATE audit_logs SET payload=CAST(:p AS json) WHERE sequence=1"),
                {"p": json.dumps(bad)})
            await s.commit()
            break

        result = await _verify()
        assert not result.ok
        assert "line 1" in result.message
    _run(run())


def test_concurrent_append_keeps_chain_valid():
    async def run():
        await _truncate()
        await asyncio.gather(*[_append(i) for i in range(20)])
        result = await _verify()
        assert result.ok, result.message
        assert result.entries == 20
    _run(run())
