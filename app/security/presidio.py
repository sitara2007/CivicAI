"""Microsoft Presidio PII sanitization — FR-1.2, GDPR/HIPAA pre-LLM gate."""

from __future__ import annotations

import logging
import re

import pybreaker

from app.resilience.breakers import presidio_breaker

logger = logging.getLogger(__name__)

ENTITIES = [
    "PERSON",
    "PHONE_NUMBER",
    "US_SSN",
    "EMAIL_ADDRESS",
    "CREDIT_CARD",
    "US_DRIVER_LICENSE",
    "US_PASSPORT",
    "MEDICAL_LICENSE",
    "US_BANK_NUMBER",
]

_REGEX_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "<US_SSN>"),
    (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "<PHONE_NUMBER>"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "<EMAIL_ADDRESS>"),
]


class SanitizationError(Exception):
    """Raised when Presidio is unavailable — fail closed, no LLM call."""


def _regex_fallback(text: str) -> tuple[str, list[dict]]:
    entities = []
    redacted = text
    # FIX: Removed the duplicate append loop
    for pattern, replacement in _REGEX_PATTERNS:
        for match in pattern.finditer(text):
            entities.append(
                {
                    "type": "REGEX",
                    "start": match.start(),
                    "end": match.end(),
                    "score": 1.0,
                }
            )
        redacted = pattern.sub(replacement, redacted)
    return redacted, entities


def _analyze_and_anonymize(text: str) -> tuple[str, list[dict]]:
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine

        analyzer = AnalyzerEngine()
        results = analyzer.analyze(text=text, entities=ENTITIES, language="en")
        anonymized = AnonymizerEngine().anonymize(text=text, analyzer_results=results)
        entities = [
            {
                "type": r.entity_type,
                "start": r.start,
                "end": r.end,
                "score": round(r.score, 3),
            }
            for r in results
        ]
        return anonymized.text, entities
    except Exception as exc:
        # FIX: Fail closed. No silent regex bypass in production.
        logger.error("presidio_failed_failing_closed", extra={"error": str(exc)})
        raise SanitizationError(
            "Presidio engine crashed. Failing closed to prevent PII leak."
        ) from exc


def sanitize(text: str) -> tuple[str, list[dict]]:
    """Mask PII before any LLM transmission. Fail closed on circuit open."""
    try:
        return presidio_breaker.call(_analyze_and_anonymize, text)
    except pybreaker.CircuitBreakerError as exc:
        logger.error("presidio_circuit_open")
        raise SanitizationError("Presidio unavailable — refusing LLM pipeline") from exc
