from __future__ import annotations

import hmac
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# FIX: AuditLog (dataclass) ki jagah SQLAuditLog (database model) import karo
from app.db.models import SQLAuditLog
from app.services.audit.chain_store import AuditEntry, VerificationResult
from app.services.audit.hash_chain import GENESIS_HASH, compute_prev_hash


class PostgresAuditStore:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def append(self, payload: dict[str, Any]) -> AuditEntry:
        # FIX: SQLAuditLog use karo
        stmt = select(SQLAuditLog).order_by(SQLAuditLog.sequence.desc()).limit(1)
        result = await self._session.execute(stmt)
        last_entry = result.scalar_one_or_none()

        prev_hash = last_entry.hash if last_entry else GENESIS_HASH
        sequence = last_entry.sequence + 1 if last_entry else 0

        chain_data = {"prev_hash": prev_hash, "payload": payload}
        entry_hash = compute_prev_hash(chain_data)

        # FIX: SQLAuditLog instance banao
        new_log = SQLAuditLog(
            sequence=sequence,
            prev_hash=prev_hash,
            payload=payload,
            hash=entry_hash
        )
        self._session.add(new_log)
        await self._session.commit()
        await self._session.refresh(new_log)

        return AuditEntry(
            sequence=new_log.sequence,
            prev_hash=new_log.prev_hash,
            payload=new_log.payload,
            hash=new_log.hash,
        )

    async def verify(self) -> VerificationResult:
        # FIX: SQLAuditLog use karo
        stmt = select(SQLAuditLog).order_by(SQLAuditLog.sequence.asc())
        result = await self._session.execute(stmt)
        logs = result.scalars().all()

        if not logs:
            return VerificationResult(ok=True, entries=0, message="empty chain")

        expected_prev_hash = GENESIS_HASH
        for i, log in enumerate(logs):
            if log.sequence != i:
                return VerificationResult(ok=False, entries=i, message=f"broken sequence at line {i}")
            if log.prev_hash != expected_prev_hash:
                return VerificationResult(ok=False, entries=i, message=f"broken link at line {i}")

            expected_hash = compute_prev_hash({"prev_hash": expected_prev_hash, "payload": log.payload})
            if not hmac.compare_digest(log.hash, expected_hash):
                return VerificationResult(ok=False, entries=i, message=f"hash mismatch at line {i}")

            expected_prev_hash = expected_hash

        return VerificationResult(ok=True, entries=len(logs), message="chain valid")
