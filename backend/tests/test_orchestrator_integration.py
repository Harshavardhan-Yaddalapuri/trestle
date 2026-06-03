"""End-to-end orchestrator integration tests via HTTP endpoint. Tests 17-18."""
from __future__ import annotations

import pytest

from backend.services.llm.fake import FakeLLMClient

from .conftest import collect_sse, make_client_factory


def _events_of_type(events: list[dict], name: str) -> list[dict]:
    return [e for e in events if e["event"] == name]


async def _post_chat(client, content: str, session_id: str, **extra) -> list[dict]:
    body = {"content": content, **extra}
    async with client.stream(
        "POST",
        "/api/chat/message",
        json=body,
        headers={"X-Session-Id": session_id},
    ) as resp:
        assert resp.status_code == 200, await resp.aread()
        return await collect_sse(resp)


# ── Test 17: Full SSE event sequence with real classifier + matching ───────

@pytest.mark.asyncio
async def test_full_sse_sequence_match_request(session_factory, redis_client, seeded_grants):
    """POST /chat/message → job_started, token+, tool_call, tool_result, message_saved, done."""
    fake_llm = FakeLLMClient(
        scripted_stream=[["Here are some great matches for your startup..."]]
    )
    async with make_client_factory(session_factory, redis_client, fake_llm) as client:
        events = await _post_chat(client, "find me grants", session_id="integ-match")

    names = [e["event"] for e in events]
    assert names[0] == "job_started"
    assert names[-1] == "done"
    assert "message_saved" in names

    # match_request intent → tool_call and tool_result
    assert "tool_call" in names
    assert "tool_result" in names
    assert "token" in names

    # Ordering: job_started ... tool_call ... tool_result ... token ... message_saved ... done
    ji = names.index("job_started")
    tci = names.index("tool_call")
    tri = names.index("tool_result")
    msi = names.index("message_saved")
    di = names.index("done")
    assert ji < tci < tri < msi < di

    done = _events_of_type(events, "done")[0]
    assert done["data"]["finish_reason"] in ("stop", "error")


# ── Test 18: Two-turn conversation: profile update then references it ──────

@pytest.mark.asyncio
async def test_two_turn_profile_update_then_match(session_factory, redis_client, seeded_grants):
    """Turn 1 updates profile. Turn 2 runs matching with updated profile."""
    import json
    session_id = "integ-two-turn"

    # Turn 1: profile update
    profile_update_intent = json.dumps({
        "intent": "profile_update",
        "confidence": 0.95,
        "entities": {
            "grant_refs": [], "stage": "seed", "location": "US",
            "industries": ["healthtech"], "funding_amount_usd_cents": None,
            "team_size": 5, "action": None,
        },
    })
    fake_llm_1 = FakeLLMClient(
        scripted_complete=[profile_update_intent],
        scripted_stream=[["Got it — I've noted you're a seed-stage healthtech startup."]]
    )
    async with make_client_factory(session_factory, redis_client, fake_llm_1) as client:
        events1 = await _post_chat(
            client, "we're seed stage in the US, healthtech, 5 people", session_id=session_id
        )

    names1 = [e["event"] for e in events1]
    assert "tool_call" in names1
    assert "tool_result" in names1

    # Get conversation_id from turn 1
    started1 = _events_of_type(events1, "job_started")[0]
    conv_id = started1["data"]["conversation_id"]

    # Verify profile was actually updated in DB
    import sqlalchemy as sa
    from backend.db.models.profile import Profile
    async with session_factory() as db:
        result = await db.execute(
            sa.select(Profile).where(Profile.session_id == session_id)
        )
        profile = result.scalar_one_or_none()

    assert profile is not None
    assert profile.company_stage == "seed"
    assert profile.team_size == 5

    # Turn 2: match request in same conversation
    fake_llm_2 = FakeLLMClient(
        scripted_stream=[["Based on your healthtech seed profile, here are your best matches..."]]
    )
    async with make_client_factory(session_factory, redis_client, fake_llm_2) as client:
        events2 = await _post_chat(
            client, "find me grants", session_id=session_id, conversation_id=conv_id
        )

    names2 = [e["event"] for e in events2]
    assert "token" in names2
    assert "done" in names2

    # The system prompt in turn 2 should contain the updated profile
    assert len(fake_llm_2.stream_calls) >= 1
    stream_msgs = fake_llm_2.stream_calls[0]
    system_msgs = [m for m in stream_msgs if m.role == "system"]
    assert any(m.content and "seed" in m.content for m in system_msgs)
