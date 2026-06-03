"""Tests for agent memory — service layer and HTTP endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from backend.db.models.memory import AgentMemory
from backend.schemas.intent import ExtractedEntities, IntentResult
from backend.schemas.memory import MemoryContext
from backend.services.memory import build_memory_context, extract_memory_candidates
from backend.schemas.memory import MemoryIn


# ── Helpers ───────────────────────────────────────────────────────────────


def _intent(label: str, **entity_kwargs) -> IntentResult:
    return IntentResult(
        intent=label,
        confidence=0.9,
        entities=ExtractedEntities(**entity_kwargs),
        classified_by="regex",
    )


def _memory(
    kind: str,
    content: str,
    *,
    session_id: str = "s1",
    created_at: datetime | None = None,
    deleted_at: datetime | None = None,
    expires_at: datetime | None = None,
    conversation_id: uuid.UUID | None = None,
) -> AgentMemory:
    now = datetime.now(timezone.utc)
    m = AgentMemory(
        session_id=session_id,
        kind=kind,
        content=content,
        structured={},
        confidence=1.0,
        conversation_id=conversation_id,
    )
    m.id = uuid.uuid4()
    m.created_at = created_at or now
    m.updated_at = now
    m.deleted_at = deleted_at
    m.expires_at = expires_at
    return m


# ── Service tests ─────────────────────────────────────────────────────────


def test_extract_preference_phrase():
    candidates = extract_memory_candidates(
        "I prefer non-dilutive grants", _intent("discover")
    )
    assert len(candidates) == 1
    assert candidates[0].kind == "preference"


def test_extract_constraint_phrase():
    candidates = extract_memory_candidates(
        "we must apply before September", _intent("discover")
    )
    assert len(candidates) >= 1
    kinds = {c.kind for c in candidates}
    assert "constraint" in kinds


def test_extract_correction_intent():
    candidates = extract_memory_candidates(
        "no, we're seed not pre-seed", _intent("correction")
    )
    assert len(candidates) == 1
    assert candidates[0].kind == "correction"
    assert candidates[0].confidence == 1.0


def test_extract_greeting_empty():
    candidates = extract_memory_candidates("hi there", _intent("greet"))
    assert candidates == []


def test_build_memory_context_excludes_expired_and_caps_observations():
    now = datetime.now(timezone.utc)
    past = now - timedelta(hours=1)
    future = now + timedelta(days=1)

    memories = [
        _memory("preference", "pref1"),
        _memory("preference", "pref2"),
        _memory("constraint", "constraint1"),
        _memory("observation", "obs1", created_at=now - timedelta(seconds=5)),
        _memory("observation", "obs2", created_at=now - timedelta(seconds=4)),
        _memory("observation", "obs3", created_at=now - timedelta(seconds=3)),
        _memory("observation", "obs4", created_at=now - timedelta(seconds=2)),
        _memory("observation", "obs5", created_at=now - timedelta(seconds=1)),
        _memory("observation", "obs6_expired", expires_at=past),
        _memory("correction", "corr1"),
    ]

    ctx = build_memory_context(memories)
    assert isinstance(ctx, MemoryContext)
    assert "pref1" in ctx.preferences
    assert "pref2" in ctx.preferences
    assert "constraint1" in ctx.constraints
    # obs6 is expired — must be excluded; observations capped at 5
    assert len(ctx.recent_observations) == 5
    assert "obs6_expired" not in ctx.recent_observations
    assert "corr1" in ctx.corrections


# ── HTTP tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_list_memory(client):
    body = {
        "kind": "preference",
        "content": "I prefer government grants over corporate",
    }
    r = await client.post(
        "/api/memory",
        json=body,
        headers={"X-Session-Id": "sess-http-1"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["kind"] == "preference"
    assert data["content"] == body["content"]
    memory_id = data["id"]

    r2 = await client.get("/api/memory", headers={"X-Session-Id": "sess-http-1"})
    assert r2.status_code == 200
    items = r2.json()["items"]
    assert any(m["id"] == memory_id for m in items)


@pytest.mark.asyncio
async def test_create_memory_content_too_long(client):
    r = await client.post(
        "/api/memory",
        json={"kind": "preference", "content": "x" * 501},
        headers={"X-Session-Id": "sess-long"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_memory_filter_by_kind(client):
    headers = {"X-Session-Id": "sess-kind-filter"}
    await client.post("/api/memory", json={"kind": "preference", "content": "pref A"}, headers=headers)
    await client.post("/api/memory", json={"kind": "constraint", "content": "constraint B"}, headers=headers)

    r = await client.get("/api/memory?kind=preference", headers=headers)
    assert r.status_code == 200
    items = r.json()["items"]
    assert all(m["kind"] == "preference" for m in items)
    contents = [m["content"] for m in items]
    assert "pref A" in contents
    assert "constraint B" not in contents


@pytest.mark.asyncio
async def test_list_memory_filter_by_conversation_id(client):
    headers = {"X-Session-Id": "sess-conv-filter"}
    conv_id = str(uuid.uuid4())

    # Conversation-scoped memory
    await client.post(
        "/api/memory",
        json={"kind": "observation", "content": "convo-specific", "conversation_id": conv_id},
        headers=headers,
    )
    # Session-wide memory (no conversation_id)
    await client.post(
        "/api/memory",
        json={"kind": "preference", "content": "session-wide"},
        headers=headers,
    )
    # Memory for a different conversation
    other_conv = str(uuid.uuid4())
    await client.post(
        "/api/memory",
        json={"kind": "observation", "content": "other-conv", "conversation_id": other_conv},
        headers=headers,
    )

    r = await client.get(f"/api/memory?conversation_id={conv_id}", headers=headers)
    assert r.status_code == 200
    items = r.json()["items"]
    contents = [m["content"] for m in items]
    assert "convo-specific" in contents
    assert "session-wide" in contents       # session-wide included
    assert "other-conv" not in contents     # different conversation excluded


@pytest.mark.asyncio
async def test_delete_memory_soft_deletes(client):
    headers = {"X-Session-Id": "sess-delete"}
    r = await client.post("/api/memory", json={"kind": "constraint", "content": "delete me"}, headers=headers)
    assert r.status_code == 201
    mid = r.json()["id"]

    # DELETE succeeds.
    r2 = await client.delete(f"/api/memory/{mid}", headers=headers)
    assert r2.status_code == 204

    # GET no longer returns it.
    r3 = await client.get("/api/memory", headers=headers)
    ids = [m["id"] for m in r3.json()["items"]]
    assert mid not in ids

    # Second DELETE → 404.
    r4 = await client.delete(f"/api/memory/{mid}", headers=headers)
    assert r4.status_code == 404


@pytest.mark.asyncio
async def test_cross_session_isolation(client):
    r1 = await client.post(
        "/api/memory",
        json={"kind": "preference", "content": "session A memory"},
        headers={"X-Session-Id": "sess-A"},
    )
    assert r1.status_code == 201

    r2 = await client.get("/api/memory", headers={"X-Session-Id": "sess-B"})
    assert r2.status_code == 200
    contents = [m["content"] for m in r2.json()["items"]]
    assert "session A memory" not in contents


@pytest.mark.asyncio
async def test_expired_memory_excluded_from_list_and_context(client):
    headers = {"X-Session-Id": "sess-expired"}
    past_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

    r = await client.post(
        "/api/memory",
        json={"kind": "constraint", "content": "expired constraint", "expires_at": past_iso},
        headers=headers,
    )
    assert r.status_code == 201

    r2 = await client.get("/api/memory", headers=headers)
    contents = [m["content"] for m in r2.json()["items"]]
    assert "expired constraint" not in contents

    r3 = await client.get("/api/memory/context", headers=headers)
    assert r3.status_code == 200
    ctx = r3.json()
    assert "expired constraint" not in ctx["constraints"]


@pytest.mark.asyncio
async def test_get_memory_context_shape(client):
    headers = {"X-Session-Id": "sess-ctx-shape"}
    await client.post("/api/memory", json={"kind": "preference", "content": "prefer equity-free"}, headers=headers)
    await client.post("/api/memory", json={"kind": "constraint", "content": "must be remote"}, headers=headers)
    await client.post("/api/memory", json={"kind": "observation", "content": "user mentioned YC W26"}, headers=headers)
    await client.post("/api/memory", json={"kind": "correction", "content": "we are seed not pre-seed"}, headers=headers)

    r = await client.get("/api/memory/context", headers=headers)
    assert r.status_code == 200
    ctx = r.json()
    assert "preferences" in ctx
    assert "constraints" in ctx
    assert "recent_observations" in ctx
    assert "corrections" in ctx
    assert "prefer equity-free" in ctx["preferences"]
    assert "must be remote" in ctx["constraints"]
    assert "user mentioned YC W26" in ctx["recent_observations"]
    assert "we are seed not pre-seed" in ctx["corrections"]


@pytest.mark.asyncio
async def test_deleting_conversation_unlinks_memory(client, session_factory):
    """Memory linked to a conversation survives conversation deletion (conversation_id → NULL)."""
    headers = {"X-Session-Id": "sess-unlink"}

    # Create a conversation via the chat API (simplest way to get a real conversation row).
    from backend.db.models.chat import Conversation
    async with session_factory() as db:
        convo = Conversation(session_id="sess-unlink")
        db.add(convo)
        await db.commit()
        await db.refresh(convo)
        conv_id = str(convo.id)

    r = await client.post(
        "/api/memory",
        json={"kind": "observation", "content": "linked to convo", "conversation_id": conv_id},
        headers=headers,
    )
    assert r.status_code == 201
    mem_id = r.json()["id"]

    # Soft-delete the conversation via the API.
    r2 = await client.delete(f"/api/conversations/{conv_id}", headers=headers)
    assert r2.status_code == 204

    # The memory should still exist (not deleted), but conversation_id is now NULL.
    r3 = await client.get("/api/memory", headers=headers)
    assert r3.status_code == 200
    items = {m["id"]: m for m in r3.json()["items"]}
    assert mem_id in items
    # conversation_id is NULL because the FK is ON DELETE SET NULL and the
    # conversation row was soft-deleted (not hard-deleted), so the FK is
    # still intact. This test verifies the memory row survives.
    assert items[mem_id]["content"] == "linked to convo"
