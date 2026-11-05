"""GET /api/v1/history — paginated document history with DLQ filter."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.db.repositories.document_repo import DocumentRepository
from app.schemas.process import DocumentCategory, HistoryItem, HistoryResponse, Priority

router = APIRouter(prefix="/api/v1", tags=["history"])


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filter by status, e.g. dlq"),
    session: AsyncSession | None = Depends(get_db_session),
) -> HistoryResponse:
    if session is None:
        raise HTTPException(status_code=503, detail="Database persistence is disabled")

    repo = DocumentRepository(session)
    rows, total, dlq_count = await repo.list_history(
        page=page,
        page_size=page_size,
        status=status,
    )

    items: list[HistoryItem] = []
    for doc, decision in rows:
        items.append(
            HistoryItem(
                trace_id=doc.trace_id,
                document_id=doc.id,
                status=doc.status.value
                if hasattr(doc.status, "value")
                else str(doc.status),
                source_type=doc.source_type,
                category=DocumentCategory(decision.category.value)
                if decision
                else None,
                priority=Priority(decision.priority.value) if decision else None,
                department=decision.department if decision else None,
                confidence=decision.confidence if decision else None,
                created_at=doc.created_at,
            )
        )

    return HistoryResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        dlq_count=dlq_count,
    )
