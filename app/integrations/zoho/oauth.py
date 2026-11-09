"""Zoho OAuth 2.0 — auth URL, code exchange, refresh."""

from __future__ import annotations

import secrets
import urllib.parse
from datetime import UTC, datetime, timedelta

import httpx

from app.core.config import get_settings
from app.integrations.zoho.errors import ZohoAuthError


def build_auth_url() -> tuple[str, str]:
    settings = get_settings()
    state = secrets.token_urlsafe(32)
    params = {
        "scope": settings.zoho_scopes,
        "client_id": settings.zoho_client_id,
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "redirect_uri": settings.zoho_redirect_uri,
        "state": state,
    }
    url = f"{_accounts_host()}/oauth/v2/auth?{urllib.parse.urlencode(params)}"
    return url, state


async def exchange_code(code: str) -> dict:
    settings = get_settings()
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.zoho_client_id,
        "client_secret": settings.zoho_client_secret,
        "redirect_uri": settings.zoho_redirect_uri,
        "code": code,
    }
    return _enrich(await _post_token(data))


async def refresh_access_token(refresh_token: str) -> dict:
    settings = get_settings()
    data = {
        "grant_type": "refresh_token",
        "client_id": settings.zoho_client_id,
        "client_secret": settings.zoho_client_secret,
        "refresh_token": refresh_token,
    }
    payload = await _post_token(data)
    payload.setdefault("refresh_token", refresh_token)
    return _enrich(payload)


def _accounts_host() -> str:
    return f"https://accounts.zoho.{get_settings().zoho_dc}"


def _enrich(payload: dict) -> dict:
    if "access_token" not in payload:
        raise ZohoAuthError(
            f"Token endpoint did not return access_token: {payload.get('error', 'unknown')}",
            zoho_error=str(payload.get("error", "")),
        )
    expires_in = int(payload.get("expires_in", 3600))
    payload["expires_at"] = datetime.now(UTC) + timedelta(seconds=expires_in)
    return payload


async def _post_token(data: dict) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.post(f"{_accounts_host()}/oauth/v2/token", data=data)
        except httpx.HTTPError as exc:
            raise ZohoAuthError(f"Network error calling token endpoint: {exc}") from exc
    try:
        return r.json()
    except Exception as exc:
        raise ZohoAuthError(
            f"Non-JSON token response (HTTP {r.status_code}): {r.text[:200]}"
        ) from exc
