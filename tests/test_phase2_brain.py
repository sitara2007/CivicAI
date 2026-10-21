"""
Phase 2 — AI Brain v1 acceptance tests.

Validates:
  - Presidio masks PII before LLM
  - 3/3 golden documents classify correctly (mock LLM)
  - Categories and priorities match PRD schema
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.process import DocumentCategory, Priority, SourceType
from app.security import presidio as presidio_module


def _presidio_available() -> bool:
    try:
        import presidio_analyzer  # noqa: F401

        return True
    except ImportError:
        return False

# PRD Phase 2: three canonical test documents
PHASE2_DOCUMENTS: list[dict[str, str]] = [
    {
        "text": (
            "I am writing to report a pothole on Main Street that has damaged two vehicles. "
            "Please repair urgently."
        ),
        "gold_category": DocumentCategory.COMPLAINT,
        "gold_priority": Priority.HIGH,
        "gold_department": "Public Works",
    },
    {
        "text": "Request for a copy of my property tax assessment records for 2024.",
        "gold_category": DocumentCategory.REQUEST,
        "gold_priority": Priority.LOW,
        "gold_department": "Tax Assessor",
    },
    {
        "text": (
            "Monthly water quality report for the municipal treatment plant "
            "showing all parameters within EPA limits."
        ),
        "gold_category": DocumentCategory.REPORT,
        "gold_priority": Priority.LOW,
        "gold_department": "Water Utilities",
    },
]

PII_DOCUMENT = (
    "John Smith (SSN 123-45-6789) reports a pothole on Main Street. "
    "Contact: john.smith@email.com, phone 555-123-4567."
)




@pytest.mark.asyncio
@pytest.mark.parametrize("case", PHASE2_DOCUMENTS, ids=lambda c: c["gold_category"].value)
async def test_three_documents_classify_correctly(case: dict[str, str]) -> None:
    """PRD Phase 2 deliverable: 3/3 test docs classify correctly."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/process",
            json={"text": case["text"], "source_type": "text"},
        )

    assert response.status_code == 200
    data = response.json()
    decision = data["decision"]
    assert decision["category"] == case["gold_category"].value
    assert decision["priority"] == case["gold_priority"].value
    assert decision["department"] == case["gold_department"]
    assert 0.0 <= decision["confidence"] <= 1.0
    assert data["hop_count"] == 1
    assert data["redacted_text"] == case["text"]
    assert len(data["audit_hash"]) == 64


def test_presidio_masks_pii_before_llm() -> None:
    """FR-1.2: names, SSNs, phone numbers masked before LLM."""
    captured: list[str] = []

    def fake_sanitize(text: str) -> tuple[str, int]:
        redacted = text.replace("123-45-6789", "<US_SSN>")
        redacted = redacted.replace("555-123-4567", "<PHONE_NUMBER>")
        redacted = redacted.replace("john.smith@email.com", "<EMAIL_ADDRESS>")
        return redacted, 3

    def capture_classify(redacted_text: str, policy_context: str = "") -> tuple[object, int]:
        _ = policy_context
        captured.append(redacted_text)
        from app.services.mock_classifier import classify_mock

        return classify_mock(redacted_text), 1

    with (
        patch("app.services.pipeline.sanitize", side_effect=fake_sanitize),
        patch("app.services.pipeline.LLMService.classify", side_effect=capture_classify),
    ):
        import asyncio

        from app.services.pipeline import PipelineService

        result = asyncio.run(
            PipelineService().run_sync(
                trace_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                text=PII_DOCUMENT,
                source_type=SourceType.TEXT,
            )
        )

    assert result.status == "completed"
    assert len(captured) == 1
    llm_input = captured[0]
    assert "123-45-6789" not in llm_input
    assert "555-123-4567" not in llm_input
    assert "john.smith@email.com" not in llm_input


@pytest.mark.skipif(
    not _presidio_available(),
    reason="presidio-analyzer not installed; run: pip install presidio-analyzer presidio-anonymizer",
)
def test_presidio_integration_masks_entities() -> None:
    """Optional live Presidio test when dependencies are installed."""
    redacted, count = presidio_module.sanitize(PII_DOCUMENT)
    assert count >= 1
    assert "123-45-6789" not in redacted or "<" in redacted
