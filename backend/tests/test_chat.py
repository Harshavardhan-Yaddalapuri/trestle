from __future__ import annotations

import uuid

import pytest

from backend.services.chat_stream import job_key, stream_key

from .conftest import collect_sse


# ── Helpers ───────────────────────────────────────────────────────────────


async def _post_chat(client, content: str, session_id: str, **extra) -> list[dict]:
    body = {"content": content, **extra}
    async with client.stream(
        "POST",
        "/api/chat/message",
        json=body,
        headers={"X-Session-Id": session_id},
    ) as resp:
        assert resp.status_code == 200, await resp.aread()
        assert resp.headers["content-type"].startswith("text/event-stream")
        return await collect_sse(resp)


def _events_of_type(events: list[dict], name: str) -> list[dict]:
    return [e for e in events if e["event"] == name]


# ── Tests ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_creates_conversation_and_streams_events(client):
    events = await _post_chat(client, "hello there", session_id="sess-A")

    names = [e["event"] for e in events]
    # First event must be job_started, last must be done, with at least one
    # token and exactly one message_saved in between.
    assert names[0] == "job_started"
    assert names[-1] == "done"
    assert "message_saved" in names
    assert any(n == "token" for n in names)

    # Strict ordering: job_started → ... tokens ... → message_saved → done
    assert names.index("job_started") < names.index("message_saved") < names.index("done")
    for i, n in enumerate(names):
        if n == "token":
            assert names.index("message_saved") > i

    # job_started payload sanity
    started = _events_of_type(events, "job_started")[0]
    assert "job_id" in started["data"]
    assert "conversation_id" in started["data"]
    uuid.UUID(started["data"]["conversation_id"])  # parses

    # done finish_reason should be stop in the happy path
    done = _events_of_type(events, "done")[0]
    assert done["data"]["finish_reason"] == "stop"


@pytest.mark.asyncio
async def test_post_other_session_conversation_returns_404(
    client, session_factory
):
    # Seed a conversation owned by a different session.
    from backend.db.models.chat import Conversation

    async with session_factory() as db:
        other = Conversation(session_id="someone-else")
        db.add(other)
        await db.commit()
        await db.refresh(other)
        other_id = str(other.id)

    res = await client.post(
        "/api/chat/message",
        json={"content": "trespass", "conversation_id": other_id},
        headers={"X-Session-Id": "sess-attacker"},
    )
    assert res.status_code == 404
    assert res.headers["content-type"].startswith("application/problem+json")
    body = res.json()
    assert body["code"] == "not_found"


@pytest.mark.asyncio
async def test_get_resume_replays_full_sequence(client):
    post_events = await _post_chat(client, "ping", session_id="sess-resume")
    job_id = _events_of_type(post_events, "job_started")[0]["data"]["job_id"]

    async with client.stream(
        "GET",
        f"/api/chat/stream/{job_id}",
        headers={"X-Session-Id": "sess-resume"},
    ) as resp:
        assert resp.status_code == 200
        resumed = await collect_sse(resp)

    # Compare event-name sequences. IDs may match too, since Redis stream IDs
    # are stable.
    assert [e["event"] for e in resumed] == [e["event"] for e in post_events]


@pytest.mark.asyncio
async def test_get_resume_with_last_event_id_skips_earlier_events(client):
    post_events = await _post_chat(client, "ping", session_id="sess-lei")
    job_id = _events_of_type(post_events, "job_started")[0]["data"]["job_id"]

    # Use the first token's id as Last-Event-ID. XREAD is exclusive — that
    # event and everything before it should NOT replay.
    first_token = _events_of_type(post_events, "token")[0]
    last_event_id = first_token["id"]
    assert last_event_id is not None

    async with client.stream(
        "GET",
        f"/api/chat/stream/{job_id}",
        headers={
            "X-Session-Id": "sess-lei",
            "Last-Event-ID": last_event_id,
        },
    ) as resp:
        assert resp.status_code == 200
        resumed = await collect_sse(resp)

    resumed_ids = {e["id"] for e in resumed}
    # job_started and the chosen first-token id must NOT appear.
    assert _events_of_type(post_events, "job_started")[0]["id"] not in resumed_ids
    assert last_event_id not in resumed_ids
    # done must still appear.
    assert any(e["event"] == "done" for e in resumed)


@pytest.mark.asyncio
async def test_conversation_ordering_by_last_message(client):
    """Conversations are sorted by updated_at desc — a new message in A should
    move it above B even if B was created more recently."""
    session = "sess-order"
    events_a = await _post_chat(client, "first in A", session_id=session)
    convo_a = _events_of_type(events_a, "job_started")[0]["data"]["conversation_id"]

    events_b = await _post_chat(client, "first in B", session_id=session)
    convo_b = _events_of_type(events_b, "job_started")[0]["data"]["conversation_id"]

    # B is more recent — send a second message into A so A's updated_at advances.
    await _post_chat(
        client,
        "second in A",
        session_id=session,
        conversation_id=convo_a,
    )

    res = await client.get(
        "/api/conversations",
        headers={"X-Session-Id": session},
    )
    assert res.status_code == 200
    ids = [it["id"] for it in res.json()["items"]]
    # A was touched last, so it should appear first (index 0); B second (index 1).
    assert ids[0] == convo_a
    assert ids[1] == convo_b


@pytest.mark.asyncio
async def test_get_resume_after_ttl_expiry_returns_410(client, redis_client):
    post_events = await _post_chat(client, "ping", session_id="sess-gone")
    job_id = _events_of_type(post_events, "job_started")[0]["data"]["job_id"]

    # Simulate TTL expiry by removing both keys.
    await redis_client.delete(stream_key(job_id), job_key(job_id))

    res = await client.get(
        f"/api/chat/stream/{job_id}",
        headers={"X-Session-Id": "sess-gone"},
    )
    assert res.status_code == 410
    assert res.headers["content-type"].startswith("application/problem+json")
    body = res.json()
    assert body["code"] == "gone"
