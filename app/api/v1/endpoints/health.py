"""Operational health endpoints for CivicOs."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


def _health_payload(status: str) -> dict[str, str]:
    settings = get_settings()
    return {
        "status": status,
        "service": settings.service_name,
        "version": settings.service_version,
        "environment": settings.environment,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health/live", tags=["health"], operation_id="health_liveness")
async def liveness() -> dict[str, str]:
    return _health_payload("alive")


@router.get("/health/ready", tags=["health"], operation_id="health_readiness")
async def readiness() -> dict[str, str]:
    return _health_payload("ready")
