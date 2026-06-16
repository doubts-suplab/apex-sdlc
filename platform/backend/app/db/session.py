from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings

# Module-level variables — initialised lazily via `init_engine`
_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(settings: Settings) -> None:
    """Initialise the async engine and session factory from settings."""
    global _engine, _async_session_factory  # noqa: PLW0603
    _engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    _async_session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


def get_engine() -> AsyncEngine:
    """Return the current engine, raising if not initialised."""
    if _engine is None:
        raise RuntimeError("Database engine has not been initialised. Call init_engine() first.")
    return _engine


async def get_db(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session per request."""
    if _async_session_factory is None:
        init_engine(settings)

    factory = _async_session_factory
    assert factory is not None  # for mypy

    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Annotated alias for use in route signatures
DbSession = Annotated[AsyncSession, Depends(get_db)]
