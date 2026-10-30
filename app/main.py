"""FastAPI application entrypoint for CivicOs."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging

logger = logging.getLogger("app.main")

def validate_required_environment() -> None:
    """Fail fast when required startup environment variables are missing."""
    settings = get_settings()
    missing: list[str] = []

    if settings.database_enabled and not settings.database_url.strip():
        missing.append("POSTGRES_URL or DATABASE_URL")

    if not settings.use_mock_llm and not settings.openai_api_key.strip():
        missing.append("LLM_API_KEY or OPENAI_API_KEY")

    if missing:
        missing_vars = ", ".join(missing)
        raise RuntimeError(f"Missing required environment variable(s): {missing_vars}")

async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown concerns."""
    validate_required_environment()
    settings = get_settings()
    logger.info(
        "application_starting",
        extra={
            "service": settings.service_name,
            "version": settings.service_version,
            "environment": settings.environment,
        },
    )
    app.state.settings = settings
    try:
        yield
    finally:
        logger.info("application_stopping", extra={"service": settings.service_name})

def create_app() -> FastAPI:
    """Build and configure the CivicOs API application."""
    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(
        title=settings.service_name,
        version=settings.service_version,
        description="RAG-based government document assistant API.",
        lifespan=lifespan,
    )

    # EXCEPTION HANDLER (Yahan lagana tha!)
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"message": "Internal Server Error", "details": str(exc)},
        )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/ready")
    async def readiness() -> dict[str, str]:
        return {"status": "ok"}

    application.include_router(api_router)
    return application

app = create_app()
