"""Zoho CRM API client."""

from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.integrations.zoho.errors import ZohoAPIError


def _api_host() -> str:
    return f"https://www.zohoapis.{get_settings().zoho_dc}"


async def fetch_contact(access_token: str, contact_id: str | None = None) -> dict:
    if contact_id:
        path = f"/crm/v2/Contacts/{contact_id}?fields=Last_Name,Email"
    else:
        path = "/crm/v2/Contacts?fields=Last_Name,Email&per_page=1"

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            f"{_api_host()}{path}",
            headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
        )
    if r.status_code != 200:
        raise ZohoAPIError(
            f"GET {path} failed: HTTP {r.status_code}",
            status_code=r.status_code,
            body=r.text[:500],
        )
    return r.json()
