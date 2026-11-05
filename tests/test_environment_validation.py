"""Startup environment validation tests."""

from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.main import validate_required_environment


def test_validate_required_environment_requires_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_ENABLED", "true")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="POSTGRES_URL or DATABASE_URL"):
        validate_required_environment()


def test_validate_required_environment_requires_llm_key_when_not_mocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MOCK_LLM", "false")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="LLM_API_KEY or OPENAI_API_KEY"):
        validate_required_environment()


def test_validate_required_environment_accepts_supported_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_ENABLED", "true")
    monkeypatch.setenv(
        "POSTGRES_URL", "postgresql+asyncpg://user:pass@localhost:5432/app"
    )
    monkeypatch.setenv("MOCK_LLM", "false")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    get_settings.cache_clear()

    validate_required_environment()
