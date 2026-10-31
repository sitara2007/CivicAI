"""Async database session factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

database_url = settings.database_url

# AGAR LOCAL HAI AUR URL NAHI HAI, TOH DUMMY URL DAALO (Tests ke liye)
if not database_url:
    database_url = "postgresql+asyncpg://dummy:dummy@localhost:5432/dummy"

# URL normalize karo
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Global Engine
engine = create_async_engine(database_url, echo=settings.environment == "development")

# Session Factory
session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session
