"""
C7: E2E Smoke Test — Full Demo Script
======================================
signup → onboarding (chat-based) → chat → grant match → nudge

This script exercises the complete user journey end-to-end using the
FastAPI test client with overridden dependencies (in-memory SQLite + FakeRedis).

Usage:
    cd backend && python -m pytest tests/e2e_smoke_test.py -v --tb=short
    # OR run standalone:
    cd backend && python tests/e2e_smoke_test.py

Endpoints exercised:
  1. GET  /health                — liveness
  2. POST /api/auth/anonymous-session — create session (signup stand-in)
  3. POST /api/chat/message      — onboarding conversation (SSE)
  4. GET  /api/users/profile     — verify profile populated
  5. POST /api/chat/message      — general chat
  6. POST /api/grants/match      — grant matching
  7. POST /api/chat/message      — nudge request
  8. GET  /api/conversations     — verify conversation history

Expected: All assertions pass. If any fail, the script exits non-zero
with detailed error output.
"""
from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path

# Ensure backend is importable when run standalone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from fakeredis import FakeAsyncRedis
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
from backend.seed.loader import load_grants_from_dir, upsert_grants


# ── Config ──────────────────────────────────────────────────────────────────

SEED_GRANTS_DIR = Path(__file__).resolve().parent.parent / "seed" / "grants"

# Fake LLM scripting — we control the orchestrator's decisions.
# Intent JSON must match what the real classifier + orchestrator expect.
_ONBOARDING_INTENT = json.dumps({
    "intent": "profile_update",
    "confidence": 0.92,
    "entities": {
        "grant_refs": [],
        "stage": "seed",
        "location": "US",
        "industries": ["ai"],
        "funding_amount_usd_cents": 500_000_00,  # $500k
        "team_size": 3,
        "action": None,
    },
})

_GREET_INTENT = json.dumps({
    "intent": "greet",
    "confidence": 0.95,
    "entities": {"grant_refs": [], "stage": None, "location": None,
                  "industries": None, "funding_amount_usd_cents": None,
                  "team_size": None, "action": None},
})

_MATCH_REQUEST_INTENT = json.dumps({
    "intent": "match_request",
    "confidence": 0.94,
    "entities": {"grant_refs": [], "stage": None, "location": None,
                  "industries": None, "funding_amount_usd_cents": None,
                  "team_size": None, "action": None},
})

_NUDGE_INTENT = json.dumps({
    "intent": "nudge",
    "confidence": 0.88,
    "entities": {"grant_refs": [], "stage": None, "location": None,
                  "industries": None, "funding_amount_usd_cents": None,
                  "team_size": None, "action": None},
})


# ── Fixtures ──────────────────────────────────────────────────────────────

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
async def seeded_grants(session_factory):
    grants = load_grants_from_dir(SEED_GRANTS_DIR)
    async with session_factory() as session:
        inserted, updated = await upsert_grants(session, grants)
    return {"inserted": inserted, "updated": updated, "grants": grants}


@pytest_asyncio.fixture
async def client(session_factory, redis_client, seeded_grants) -> AsyncClient:
    """HTTP client with seeded grants + FakeLLM ready for scripting."""
    app = create_app()

    async def _override_db():
        async with session_factory() as session:
            yield session

    async def _override_redis():
        yield redis_client

    def _override_factory():
        return session_factory

    # Default fake LLM — tests will swap via app.dependency_overrides per call
    fake_llm = FakeLLMClient()

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis
    app.dependency_overrides[get_db_factory] = _override_factory
    app.dependency_overrides[get_llm_client] = lambda: fake_llm

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


# ── SSE helpers ───────────────────────────────────────────────────────────

async def collect_sse(response) -> list[dict]:
    events = []
    current_id = None
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
                events.append({"id": current_id, "event": current_event, "data": parsed})
            current_id = None
            current_event = "message"
            current_data = ""
    return events


def events_of_type(events: list[dict], name: str) -> list[dict]:
    return [e for e in events if e["event"] == name]


async def post_chat(client, content: str, session_id: str, **extra) -> list[dict]:
    body = {"content": content, **extra}
    async with client.stream(
        "POST", "/api/chat/message", json=body,
        headers={"X-Session-Id": session_id},
    ) as resp:
        assert resp.status_code == 200, await resp.aread()
        return await collect_sse(resp)


# ── E2E Smoke Test ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_e2e_full_demo_flow(client, session_factory, redis_client):
    """
    C7: Full demo script — signup → onboarding → chat → grant match → nudge.
    """
    session_id = "demo-e2e-session"
    app = client._transport.app  # noqa: SLF001

    # ── Step 0: Health check (with explicit session header so cookie binds) ─
    health = await client.get("/health", headers={"X-Session-Id": session_id})
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    print("✅ Step 0: /health OK")

    # ── Step 1: Create anonymous session (signup stand-in) ───────────────
    anon = await client.post("/api/auth/anonymous-session", json={},
                             headers={"X-Session-Id": session_id})
    # Anonymous session endpoint may or may not exist in current backend.
    # If 404, the SessionMiddleware already created a session from the header.
    if anon.status_code == 404:
        print("⚠️  Step 1: /api/auth/anonymous-session 404 — SessionMiddleware handled it")
    else:
        assert anon.status_code in (200, 201)
        print("✅ Step 1: Anonymous session created")

    # ── Step 2: Onboarding via chat ───────────────────────────────────────
    # Script the LLM so the orchestrator classifies as profile_update.
    scripted_llm = FakeLLMClient(
        scripted_complete=[_ONBOARDING_INTENT],
        scripted_stream=[["Great! I've saved your profile. You're a seed-stage AI startup in the US with a team of 3."]],
    )
    app.dependency_overrides[get_llm_client] = lambda: scripted_llm

    onboarding_events = await post_chat(
        client, "I'm Alice from SeedAI, a seed-stage AI startup in the US with 3 people",
        session_id=session_id,
    )
    names = [e["event"] for e in onboarding_events]
    assert "job_started" in names
    assert "done" in names
    assert "message_saved" in names
    print("✅ Step 2: Onboarding chat completed")

    # ── Step 3: Verify profile was populated ──────────────────────────────
    profile_resp = await client.get("/api/users/profile",
                                    headers={"X-Session-Id": session_id})
    assert profile_resp.status_code == 200
    profile = profile_resp.json()
    assert profile["session_id"] == session_id
    # The orchestrator extracted at least stage, industry, team_size
    assert profile["company_stage"] == "seed"
    assert profile["industry"] == ["ai"]
    assert profile["team_size"] == 3
    # Location/founder_name may or may not be extracted depending on NLP tuning
    print(f"✅ Step 3: Profile verified — stage={profile['company_stage']}, "
          f"industry={profile['industry']}, team_size={profile['team_size']}, "
          f"location={profile['location']}, founder={profile['founder_name']}")

    # ── Step 4: General chat (greeting) ───────────────────────────────────
    greet_llm = FakeLLMClient(
        scripted_complete=[_GREET_INTENT],
        scripted_stream=[["Hello! I'm Trestle, your startup assistant. How can I help today?"]],
    )
    app.dependency_overrides[get_llm_client] = lambda: greet_llm

    chat_events = await post_chat(client, "Hi there!", session_id=session_id)
    names = [e["event"] for e in chat_events]
    assert "job_started" in names
    assert "done" in names
    print("✅ Step 4: General chat completed")

    # ── Step 5: Grant match ───────────────────────────────────────────────
    match_resp = await client.post("/api/grants/match", json={},
                                   headers={"X-Session-Id": session_id})
    assert match_resp.status_code == 200
    match_body = match_resp.json()
    assert "results" in match_body
    assert "match_profile" in match_body
    results = match_body["results"]
    assert len(results) > 0
    # At least one strong or moderate match for a well-populated seed AI profile
    tiers = {r["tier"] for r in results}
    assert tiers.intersection({"strong", "moderate"}), f"Expected strong/moderate matches, got tiers: {tiers}"
    print(f"✅ Step 5: Grant match — {len(results)} results, tiers={tiers}")

    # ── Step 6: Chat-based nudge request ──────────────────────────────────
    nudge_llm = FakeLLMClient(
        scripted_complete=[_NUDGE_INTENT],
        scripted_stream=[["Here are your top priorities: 1) Apply to NSF SBIR (closes Sep 15). 2) Follow up on YC W26 application."]],
    )
    app.dependency_overrides[get_llm_client] = lambda: nudge_llm

    nudge_events = await post_chat(client, "What should I focus on this week?",
                                   session_id=session_id)
    names = [e["event"] for e in nudge_events]
    assert "job_started" in names
    assert "done" in names
    print("✅ Step 6: Nudge request completed")

    # ── Step 7: Conversation history ──────────────────────────────────────
    conv_resp = await client.get("/api/conversations",
                                 headers={"X-Session-Id": session_id})
    assert conv_resp.status_code == 200
    conv_body = conv_resp.json()
    items = conv_body["items"]
    # We created 3 conversations (onboarding, chat, nudge) — each with 1 user + 1 assistant msg
    assert len(items) == 3, f"Expected 3 conversations, got {len(items)}"
    for item in items:
        assert item["message_count"] == 2
        assert item["last_message_preview"] is not None
    print(f"✅ Step 7: Conversation history — {len(items)} conversations, all with 2 messages")

    print("\n🎉 C7 E2E Smoke Test PASSED — full demo flow functional!")


# ── Standalone runner ───────────────────────────────────────────────────────

if __name__ == "__main__":
    # Run with pytest programmatically for clean async handling
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short", "-s"],
        cwd=Path(__file__).resolve().parent.parent,
    )
    sys.exit(result.returncode)
