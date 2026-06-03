from __future__ import annotations

import json
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

from backend.db.base import Base
from backend.db.session import get_db, get_db_factory
from backend.main import create_app
from backend.redis_client import get_redis
from backend.services.llm.dependency import get_llm_client
from backend.services.llm.fake import FakeLLMClient


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(db_engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture
async def redis_client():
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
    """Default FakeLLMClient for tests. Override per-test with a custom instance."""
    return FakeLLMClient()


@pytest_asyncio.fixture
async def client(session_factory, redis_client, fake_llm) -> AsyncIterator[AsyncClient]:
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


# ── grant seed fixture ────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def seeded_grants(session_factory) -> dict:
    from pathlib import Path

    from backend.seed.loader import load_grants_from_dir, upsert_grants

    seed_dir = Path(__file__).parent.parent / "seed" / "grants"
    grants = load_grants_from_dir(seed_dir)
    async with session_factory() as session:
        inserted, updated = await upsert_grants(session, grants)
    return {"inserted": inserted, "updated": updated, "grants": grants}


# ── helpers ───────────────────────────────────────────────────────────────


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
    from httpx import ASGITransport, AsyncClient

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
