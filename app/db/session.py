"""Async database session factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


@lru_cache(maxsize=4)
def _get_session_factory(
    database_url: str,
    environment: str,
) -> async_sessionmaker[AsyncSession]:
    # GOD-LEVEL FIX: Ensure the URL uses the asyncpg driver
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(database_url, echo=environment == "development")
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    settings = get_settings()
    session_factory = _get_session_factory(settings.database_url, settings.environment)
    async with session_factory() as session:
        yield session
