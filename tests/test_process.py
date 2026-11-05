"""API contract tests for /api/v1/process — Phase 1."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.process import DecisionOutput, DocumentCategory, Priority


@pytest.fixture
def mock_decision() -> DecisionOutput:
    return DecisionOutput(
        category=DocumentCategory.COMPLAINT,
        priority=Priority.HIGH,
        department="Public Works",
        confidence=0.92,
        decision_rationale="Infrastructure damage complaint requiring urgent public works attention.",
        summary="Citizen reports pothole damage on Main Street routed to Public Works.",
    )


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_process_rejects_empty_text() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/process", json={"text": "   "})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_process_returns_valid_json(mock_decision: DecisionOutput) -> None:
    from app.services.pipeline import PipelineResult, PipelineService

    mock_result = PipelineResult(
        status="completed",
        decision=mock_decision,
        requires_review=False,
        hop_count=1,
        pii_entities_masked=2,
    )

    with patch.object(
        PipelineService, "run_sync", new_callable=AsyncMock, return_value=mock_result
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/process",
                json={
                    "text": "Pothole on Main Street damaged my car.",
                    "source_type": "text",
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert "trace_id" in data
    assert "document_id" in data
    assert data["status"] == "completed"
    assert data["decision"]["category"] == "Complaint"
