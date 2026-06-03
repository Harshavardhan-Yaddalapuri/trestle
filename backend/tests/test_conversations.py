from __future__ import annotations

import uuid

import pytest

from .conftest import collect_sse


# ── Helpers ───────────────────────────────────────────────────────────────


async def _create_conversation_via_chat(
    client, content: str, session_id: str
) -> str:
    """POST a chat message and return the conversation_id from job_started.

    Waits for `done` so the assistant message is persisted before returning,
    which keeps message_count assertions deterministic.
    """
    async with client.stream(
        "POST",
        "/api/chat/message",
        json={"content": content},
        headers={"X-Session-Id": session_id},
    ) as resp:
        assert resp.status_code == 200
        events = await collect_sse(resp)
    assert events[0]["event"] == "job_started"
    assert events[-1]["event"] == "done"
    return events[0]["data"]["conversation_id"]


# ── Tests ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_empty_returns_no_items(client):
    res = await client.get(
        "/api/conversations",
        headers={"X-Session-Id": "sess-empty"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body == {"items": [], "next_cursor": None}


@pytest.mark.asyncio
async def test_list_returns_conversations_with_count_and_preview(client):
    session = "sess-list"
    convo_a = await _create_conversation_via_chat(client, "first message", session)
    convo_b = await _create_conversation_via_chat(client, "second message", session)
    convo_c = await _create_conversation_via_chat(client, "third message", session)

    res = await client.get(
        "/api/conversations",
        headers={"X-Session-Id": session},
    )
    assert res.status_code == 200
    body = res.json()
    items = body["items"]
    assert body["next_cursor"] is None
    assert len(items) == 3

    # Order: most-recently-created first (we never bump updated_at after insert).
    ids_in_order = [it["id"] for it in items]
    assert ids_in_order == [convo_c, convo_b, convo_a]

    # Each conversation got one user message and one assistant message.
    for item in items:
        assert item["message_count"] == 2
        # Preview is the most recent message — the assistant reply.
        assert item["last_message_preview"] is not None
        assert len(item["last_message_preview"]) > 0
        assert len(item["last_message_preview"]) <= 120


@pytest.mark.asyncio
async def test_list_pagination_via_cursor(client):
    session = "sess-page"
    convo_a = await _create_conversation_via_chat(client, "a", session)
    convo_b = await _create_conversation_via_chat(client, "b", session)
    convo_c = await _create_conversation_via_chat(client, "c", session)

    first = await client.get(
        "/api/conversations",
        params={"limit": 2},
        headers={"X-Session-Id": session},
    )
    assert first.status_code == 200
    first_body = first.json()
    assert len(first_body["items"]) == 2
    assert first_body["next_cursor"] is not None
    assert [it["id"] for it in first_body["items"]] == [convo_c, convo_b]

    second = await client.get(
        "/api/conversations",
        params={"limit": 2, "cursor": first_body["next_cursor"]},
        headers={"X-Session-Id": session},
    )
    assert second.status_code == 200
    second_body = second.json()
    assert len(second_body["items"]) == 1
    assert second_body["items"][0]["id"] == convo_a
    assert second_body["next_cursor"] is None


@pytest.mark.asyncio
async def test_get_detail_returns_messages_in_created_at_order(client):
    session = "sess-detail"
    convo_id = await _create_conversation_via_chat(client, "hello detail", session)

    res = await client.get(
        f"/api/conversations/{convo_id}",
        headers={"X-Session-Id": session},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == convo_id
    roles = [m["role"] for m in body["messages"]]
    assert roles == ["user", "assistant"]
    # ASC ordering: created_at strictly non-decreasing.
    times = [m["created_at"] for m in body["messages"]]
    assert times == sorted(times)
    # metadata field is exposed (default {}) — not the SA Python attr `meta`.
    for m in body["messages"]:
        assert m["metadata"] == {}


@pytest.mark.asyncio
async def test_get_detail_other_session_returns_404(client, session_factory):
    from backend.db.models.chat import Conversation

    async with session_factory() as db:
        other = Conversation(session_id="someone-else")
        db.add(other)
        await db.commit()
        await db.refresh(other)
        other_id = str(other.id)

    res = await client.get(
        f"/api/conversations/{other_id}",
        headers={"X-Session-Id": "sess-attacker"},
    )
    assert res.status_code == 404
    assert res.headers["content-type"].startswith("application/problem+json")
    assert res.json()["code"] == "not_found"


@pytest.mark.asyncio
async def test_delete_soft_deletes_and_hides_from_list_and_detail(client):
    session = "sess-delete"
    keep_id = await _create_conversation_via_chat(client, "keep", session)
    gone_id = await _create_conversation_via_chat(client, "gone", session)

    del_res = await client.delete(
        f"/api/conversations/{gone_id}",
        headers={"X-Session-Id": session},
    )
    assert del_res.status_code == 204
    assert del_res.content == b""

    get_res = await client.get(
        f"/api/conversations/{gone_id}",
        headers={"X-Session-Id": session},
    )
    assert get_res.status_code == 404
    assert get_res.json()["code"] == "not_found"

    list_res = await client.get(
        "/api/conversations",
        headers={"X-Session-Id": session},
    )
    ids = [it["id"] for it in list_res.json()["items"]]
    assert ids == [keep_id]


@pytest.mark.asyncio
async def test_delete_twice_returns_404_second_call(client):
    session = "sess-del-twice"
    convo_id = await _create_conversation_via_chat(client, "byebye", session)

    first = await client.delete(
        f"/api/conversations/{convo_id}",
        headers={"X-Session-Id": session},
    )
    assert first.status_code == 204

    second = await client.delete(
        f"/api/conversations/{convo_id}",
        headers={"X-Session-Id": session},
    )
    assert second.status_code == 404
    assert second.json()["code"] == "not_found"


@pytest.mark.asyncio
async def test_list_with_malformed_cursor_returns_400(client):
    res = await client.get(
        "/api/conversations",
        params={"cursor": "not-base64-and-not-json!!"},
        headers={"X-Session-Id": "sess-bad-cursor"},
    )
    assert res.status_code == 400
    assert res.headers["content-type"].startswith("application/problem+json")
    assert res.json()["code"] == "invalid_cursor"
