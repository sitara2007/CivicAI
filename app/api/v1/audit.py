"""GET /audit/count — verifiable audit-chain state for pipeline A (Postgres)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.db.models import SQLAuditLog

router = APIRouter(tags=["audit"])


class AuditCountResponse(BaseModel):
    count: int
    max_sequence: int | None
    last_hash: str | None


@router.get("/audit/count", response_model=AuditCountResponse)
async def get_audit_count(
    session: AsyncSession | None = Depends(get_db_session),
) -> AuditCountResponse:
    if session is None:
        raise HTTPException(status_code=503, detail="Database persistence is disabled")

    result = await session.execute(
        select(
            func.count(SQLAuditLog.sequence).label("count"),
            func.max(SQLAuditLog.sequence).label("max_seq"),
        )
    )
    row = result.one()

    last_hash: str | None = None
    if row.max_seq is not None:
        h = await session.execute(
            select(SQLAuditLog.hash).where(SQLAuditLog.sequence == row.max_seq)
        )
        last_hash = h.scalar_one_or_none()

    return AuditCountResponse(
        count=int(row.count or 0),
        max_sequence=row.max_seq,
        last_hash=last_hash,
    )
