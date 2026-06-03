"""Shared test fixtures for Trestle backend tests.

Merged: Supabase mock fixtures (main) + async DB/LLM fixtures (orchestrator).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, AsyncIterator
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db.base import Base
from backend.db.session import get_db, get_db_factory
from backend.main import create_app
from backend.redis_client import get_redis
from backend.services.llm.dependency import get_llm_client
from backend.services.llm.fake import FakeLLMClient


# ============================================================
# Supabase mock fixtures (from main)
# ============================================================

@pytest.fixture(autouse=True)
def mock_settings_env(monkeypatch):
    """Override settings so tests don't need a real .env file."""
    monkeypatch.setenv("SUPABASE_URL", "https://test-project.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "test-model")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture
def mock_supabase():
    """Return a fully chainable supabase mock."""
    mock = MagicMock()
    mock_execute = MagicMock()
    mock_execute.data = []
    mock_execute.count = 0

    def _chain(*args, **kwargs):
        return mock

    mock.table = MagicMock(side_effect=_chain)
    mock.select = MagicMock(side_effect=_chain)
    mock.insert = MagicMock(side_effect=_chain)
    mock.update = MagicMock(side_effect=_chain)
    mock.delete = MagicMock(side_effect=_chain)
    mock.upsert = MagicMock(side_effect=_chain)
    mock.eq = MagicMock(side_effect=_chain)
    mock.neq = MagicMock(side_effect=_chain)
    mock.gt = MagicMock(side_effect=_chain)
    mock.lt = MagicMock(side_effect=_chain)
    mock.gte = MagicMock(side_effect=_chain)
    mock.lte = MagicMock(side_effect=_chain)
    mock.like = MagicMock(side_effect=_chain)
    mock.ilike = MagicMock(side_effect=_chain)
    mock.is_ = MagicMock(side_effect=_chain)
    mock.in_ = MagicMock(side_effect=_chain)
    mock.order = MagicMock(side_effect=_chain)
    mock.limit = MagicMock(side_effect=_chain)
    mock.range = MagicMock(side_effect=_chain)
    mock.single = MagicMock(side_effect=_chain)
    mock.execute = mock_execute
    return mock


@pytest.fixture
def mock_supabase_client():
    """Mock create_client to return a chainable mock."""
    mock = MagicMock()
    mock_execute = MagicMock()
    mock_execute.data = []
    mock_execute.count = 0

    def _chain(*args, **kwargs):
        return mock

    mock.table = MagicMock(side_effect=_chain)
    mock.select = MagicMock(side_effect=_chain)
    mock.insert = MagicMock(side_effect=_chain)
    mock.update = MagicMock(side_effect=_chain)
    mock.delete = MagicMock(side_effect=_chain)
    mock.upsert = MagicMock(side_effect=_chain)
    mock.eq = MagicMock(side_effect=_chain)
    mock.neq = MagicMock(side_effect=_chain)
    mock.gt = MagicMock(side_effect=_chain)
    mock.lt = MagicMock(side_effect=_chain)
    mock.gte = MagicMock(side_effect=_chain)
    mock.lte = MagicMock(side_effect=_chain)
    mock.like = MagicMock(side_effect=_chain)
    mock.ilike = MagicMock(side_effect=_chain)
    mock.is_ = MagicMock(side_effect=_chain)
    mock.in_ = MagicMock(side_effect=_chain)
    mock.order = MagicMock(side_effect=_chain)
    mock.limit = MagicMock(side_effect=_chain)
    mock.range = MagicMock(side_effect=_chain)
    mock.single = MagicMock(side_effect=_chain)
    mock.execute = mock_execute

    with patch("app.services.supabase.create_client", return_value=mock):
        yield mock


# ============================================================
# Async DB + Redis + LLM fixtures (from orchestrator)
# ============================================================

@pytest_asyncio.fixture
async def db_engine():
    """In-memory SQLite engine with tables created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncIterator[AsyncSession]:
    """Single async session per test, rolled back after."""
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def db_factory(db_engine):
    """Session factory for tests that need factory access."""
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def fake_redis() -> FakeAsyncRedis:
    """Fake Redis for tests using Redis pub/sub."""
    return FakeAsyncRedis()


@pytest.fixture
def llm_client() -> FakeLLMClient:
    """Pre-populated fake LLM for deterministic tests."""
    return FakeLLMClient()


@pytest_asyncio.fixture
async def async_app_client(
    db_engine, fake_redis, llm_client
) -> AsyncIterator[AsyncClient]:
    """Async HTTP client with overridden deps for orchestrator tests."""
    app = create_app()

    async def _override_db():
        factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            yield session

    async def _override_redis():
        yield fake_redis

    async def _override_factory():
        session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
        return session_factory

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_db_factory] = _override_factory
    app.dependency_overrides[get_llm_client] = lambda: llm_client

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")
