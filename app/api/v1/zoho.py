"""Zoho OAuth + contacts endpoints."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import get_settings
from app.db.models import ZohoToken
from app.integrations.zoho.client import fetch_contact
from app.integrations.zoho.errors import ZohoAPIError, ZohoAuthError
from app.integrations.zoho.oauth import (
    build_auth_url,
    exchange_code,
    refresh_access_token,
)

from pydantic import BaseModel
from typing import Any, Dict

router = APIRouter(prefix="/api/v1/zoho", tags=["zoho"])
logger = logging.getLogger(__name__)

_STATE_TTL = 600
_states: dict[str, float] = {}


def _store_state(state: str) -> None:
    now = time.time()
    _states[state] = now + _STATE_TTL
    for k in [k for k, v in _states.items() if v < now]:
        _states.pop(k, None)


def _consume_state(state: str) -> bool:
    expiry = _states.pop(state, None)
    return expiry is not None and expiry > time.time()


@router.get("/authorize")
async def authorize() -> RedirectResponse:
    settings = get_settings()
    if not settings.zoho_enabled:
        raise HTTPException(503, "Zoho not configured")
    url, state = build_auth_url()
    _store_state(state)
    return RedirectResponse(url)


@router.get("/callback")
async def callback(
    code: str | None = None,
    state: str | None = None,
    session: AsyncSession | None = Depends(get_db_session),
) -> dict:
    if not code or not state:
        raise HTTPException(400, "Missing code or state")
    if not _consume_state(state):
        raise HTTPException(400, "invalid state")
    if session is None:
        raise HTTPException(503, "Database disabled")

    try:
        tokens = await exchange_code(code)
    except ZohoAuthError as exc:
        raise HTTPException(502, f"Zoho auth failed: {exc}") from exc

    settings = get_settings()
    await session.execute(delete(ZohoToken).where(ZohoToken.dc == settings.zoho_dc))
    session.add(
        ZohoToken(
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token", ""),
            expires_at=tokens["expires_at"],
            scope=tokens.get("scope", ""),
            dc=settings.zoho_dc,
        )
    )
    await session.commit()

    logger.info(
        "zoho.oauth.callback",
        extra={
            "access_token_len": len(tokens["access_token"]),
            "scope": tokens.get("scope", ""),
        },
    )
    return {"status": "connected", "scope": tokens.get("scope")}


@router.get("/contacts/{contact_id}")
async def get_contact(
    contact_id: str,
    session: AsyncSession | None = Depends(get_db_session),
) -> dict:
    if session is None:
        raise HTTPException(503, "Database disabled")
    settings = get_settings()

    row = (
        await session.execute(
            select(ZohoToken)
            .where(ZohoToken.dc == settings.zoho_dc)
            .order_by(ZohoToken.updated_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Zoho not connected")

    access_token = row.access_token
    if row.expires_at <= datetime.now(UTC):
        try:
            refreshed = await refresh_access_token(row.refresh_token)
        except ZohoAuthError as exc:
            raise HTTPException(502, f"Refresh failed: {exc}") from exc
        access_token = refreshed["access_token"]
        row.access_token = access_token
        row.expires_at = refreshed["expires_at"]
        await session.commit()

    try:
        return await fetch_contact(access_token, contact_id)
    except ZohoAPIError as exc:
        if exc.retryable:
            raise HTTPException(503, str(exc)) from exc
        raise HTTPException(502, str(exc)) from exc


class ZohoWebhookPayload(BaseModel):
    module: str
    operation: str
    ids: list[str]
    data: Dict[str, Any]


@router.post("/webhook")
async def receive_zoho_webhook(payload: ZohoWebhookPayload):
    """
    Receives real-time triggers from Zoho CRM when a document is attached/updated.
    """
    logger.info(
        f"Received Zoho Webhook for module: {payload.module}, op: {payload.operation}"
    )

    if payload.module == "Attachments" or "document" in payload.operation.lower():
        logger.info("Document detected! Triggering CivicAI parsing pipeline...")
        # TODO: Call Celery task here: parse_document.delay(payload.ids[0])
        return {
            "status": "success",
            "message": "Document received and queued for parsing.",
        }

    return {"status": "ignored", "message": "Not a document event."}
