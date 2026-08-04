from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set required env vars BEFORE importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests-only")
# Deterministic, no-key LLM for endpoints that run the reference journey via get_llm_provider().
os.environ.setdefault("LLM_PROVIDER", "stub")

# Hermetic tests: clear any ambient integration credentials so tool-adapter resolution stays fully
# offline and no test can accidentally reach a live system (the CI/session env may carry a real
# GITHUB_TOKEN). Live adapters are exercised against an in-process mock transport instead.
for _cred in (
    "GITHUB_TOKEN",
    "JIRA_BASE_URL",
    "JIRA_API_TOKEN",
    "CONFLUENCE_BASE_URL",
    "CONFLUENCE_TOKEN",
    "SLACK_BOT_TOKEN",
    "JENKINS_BASE_URL",
    "JENKINS_API_TOKEN",
):
    os.environ[_cred] = ""

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import create_app  # noqa: E402

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncGenerator[Any, None]:
    """Create in-memory SQLite engine and schema once per test session."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(test_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional session rolled back after each test."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with DB dependency overridden to use test session."""
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# Re-export pytest mark for convenience
pytestmark = pytest.mark.asyncio
