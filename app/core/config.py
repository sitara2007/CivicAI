"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("SKIP_DOTENV") == "true":
            return init_settings, env_settings, file_secret_settings
        return init_settings, env_settings, dotenv_settings, file_secret_settings

    environment: str = "development"

    log_level: str = "INFO"
    port: int = 8000
    service_name: str = "CivicOs"
    service_version: str = "0.1.0"
    api_prefix: str = "/api/v1"

    database_url: str = ""
    database_enabled: bool = True
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None
    qdrant_url: str = ""

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    rag_enabled: bool = True
    rag_embedding_model: str = "all-MiniLM-L6-v2"
    rag_qdrant_path: str = "data/qdrant_db"
    rag_collection_name: str = "gov_docs"
    rag_top_k: int = 3
    rag_context_max_chars: int = 4_000

    max_agentic_hops: int = 5
    review_confidence_threshold: float = 0.75
    max_input_tokens: int = 8000
    max_document_tokens: int = 10_000
    sync_mode: bool = True  # Phase 1-4: sync; Phase 5+: set False
    mock_llm: bool = True  # Set to True for mock responses

    @property
    def use_mock_llm(self) -> bool:
        if self.mock_llm:
            return True
        return self.environment == "development" and not self.openai_api_key

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url


def _load_env_alias(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip():
            return value
    return None


@lru_cache
def get_settings() -> Settings:
    overrides: dict[str, str] = {}
    database_url = _load_env_alias("DATABASE_URL", "POSTGRES_URL")
    if database_url is not None:
        overrides["database_url"] = database_url

    qdrant_url = _load_env_alias("QDRANT_URL")
    if qdrant_url is not None:
        overrides["qdrant_url"] = qdrant_url

    openai_api_key = _load_env_alias("OPENAI_API_KEY", "LLM_API_KEY")
    if openai_api_key is not None:
        overrides["openai_api_key"] = openai_api_key

    return Settings(**overrides)
