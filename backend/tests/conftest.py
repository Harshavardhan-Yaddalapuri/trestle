"""Shared test fixtures for Trestle backend tests.

Async DB/LLM/Redis fixtures (orchestrator base) + Supabase JWT mock (main).

The Supabase-only auth world means the only auth mock we need is
`mock_successful_jwt_verification` (patches `backend.middleware.auth._verify_token`).
The historical `mock_supabase_httpx_*` and `mock_supabase_client` fixtures
from the magic-link era were removed — they patched symbols
(`backend.api.auth.create_client`, `httpx.AsyncClient.post`) that no
longer exist in the Supabase-only flow.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from fakeredis import FakeAsyncRedis
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
# Env overrides (from main)
# ============================================================


@pytest.fixture(autouse=True)
def mock_settings_env(monkeypatch):
    """Override settings so tests don't need a real .env file."""
    monkeypatch.setenv("SUPABASE_URL", "https://test-project.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "test-model")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")

    # Clear settings cache so env changes take effect
    from backend.core.config import get_settings

    get_settings.cache_clear()


# ============================================================
# Supabase JWT mock (the only auth mock in the Supabase-only world)
# ============================================================


@pytest.fixture
def mock_successful_jwt_verification(monkeypatch):
    """Mock Supabase JWT verification to always return a valid payload.

    Patches `backend.middleware.auth._verify_token`. The middleware
    then binds a `UserCtx` derived from the returned payload to
    `request.state.user`, exactly as it would in production.
    """
    import backend.middleware.auth as auth_mod

    def mock_verify(token: str) -> dict:
        return {
            "sub": "user-123",
            "email": "test@example.com",
            "role": "authenticated",
            "exp": 9999999999,
            "iat": 1700000000,
        }

    monkeypatch.setattr(auth_mod, "_verify_token", mock_verify)
    return ("user-123", "test@example.com")


# ============================================================
# Async DB fixtures (orchestrator base)
# ============================================================


@pytest_asyncio.fixture
async def db_engine():
    """In-memory SQLite engine with all tables created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(db_engine) -> async_sessionmaker[AsyncSession]:
    """Async session factory — rollback between tests."""
    return async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)


# ============================================================
# Redis + LLM fixtures (orchestrator base)
# ============================================================


@pytest_asyncio.fixture
async def redis_client():
    """Fake Redis for pub/sub tests."""
    client = FakeAsyncRedis(decode_responses=True)
    try:
        yield client
    finally:
        try:
            await client.aclose()
        except AttributeError:
            await client.close()


@pytest_asyncio.fixture
def fake_llm():
    """Default FakeLLMClient. Override per-test with custom instance."""
    return FakeLLMClient()


# ============================================================
# HTTP client fixture (orchestrator base)
# ============================================================


@pytest_asyncio.fixture
async def client(session_factory, redis_client, fake_llm) -> AsyncIterator[AsyncClient]:
    """Async HTTP client with all deps overridden for orchestrator tests."""
    app = create_app()

    async def _override_db():
        async with session_factory() as session:
            yield session

    async def _override_redis():
        yield redis_client

    def _override_factory():
        return session_factory

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_db_factory] = _override_factory
    app.dependency_overrides[get_llm_client] = lambda: fake_llm

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


# ============================================================
# Grant seed fixture
# ============================================================


@pytest_asyncio.fixture
async def seeded_grants(session_factory) -> dict:
    """Load seed grants into DB. Returns {inserted, updated, grants}."""
    from backend.seed.loader import load_grants_from_dir, upsert_grants

    seed_dir = Path(__file__).parent.parent / "seed" / "grants"
    grants = load_grants_from_dir(seed_dir)
    async with session_factory() as session:
        inserted, updated = await upsert_grants(session, grants)
    return {"inserted": inserted, "updated": updated, "grants": grants}


# ============================================================
# Helper functions
# ============================================================


async def collect_sse(response) -> list[dict[str, Any]]:
    """Drain an SSE response into [{id, event, data}] frames."""
    events: list[dict[str, Any]] = []
    current_id: str | None = None
    current_event = "message"
    current_data = ""
    async for line in response.aiter_lines():
        if line.startswith("id: "):
            current_id = line[4:]
        elif line.startswith("event: "):
            current_event = line[7:]
        elif line.startswith("data: "):
            current_data += line[6:]
        elif line == "":
            if current_data:
                try:
                    parsed = json.loads(current_data)
                except json.JSONDecodeError:
                    parsed = current_data
                events.append(
                    {"id": current_id, "event": current_event, "data": parsed}
                )
            current_id = None
            current_event = "message"
            current_data = ""
    return events


def make_client_factory(session_factory, redis_client, llm_client):
    """Create an AsyncClient with custom LLM client for orchestrator tests."""
    app = create_app()

    async def _override_db():
        async with session_factory() as session:
            yield session

    async def _override_redis():
        yield redis_client

    def _override_factory():
        return session_factory

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_db_factory] = _override_factory
    app.dependency_overrides[get_llm_client] = lambda: llm_client

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")
