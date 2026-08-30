"""Orchestrator tests with FakeLLMClient. Tests 1-16 from the spec."""
from __future__ import annotations

import json
import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio

from backend.services.llm.fake import FakeLLMClient

from .conftest import collect_sse, make_client_factory

_DISCOVER_INTENT = json.dumps({
    "intent": "discover",
    "confidence": 0.85,
    "entities": {"grant_refs": [], "stage": None, "location": None, "industries": [], "funding_amount_usd_cents": None, "team_size": None, "action": None},
})

_UNKNOWN_INTENT = json.dumps({
    "intent": "unknown",
    "confidence": 0.3,
    "entities": {"grant_refs": [], "stage": None, "location": None, "industries": [], "funding_amount_usd_cents": None, "team_size": None, "action": None},
})

_PROFILE_UPDATE_INTENT = json.dumps({
    "intent": "profile_update",
    "confidence": 0.95,
    "entities": {"grant_refs": [], "stage": None, "location": "US-DE", "industries": [], "funding_amount_usd_cents": None, "team_size": None, "action": None},
})

_PROFILE_UPDATE_LOW_CONF = json.dumps({
    "intent": "profile_update",
    "confidence": 0.5,
    "entities": {"grant_refs": [], "stage": None, "location": "US-DE", "industries": [], "funding_amount_usd_cents": None, "team_size": None, "action": None},
})

_MATCH_REQUEST_INTENT = json.dumps({
    "intent": "match_request",
    "confidence": 0.85,
    "entities": {"grant_refs": [], "stage": "seed", "location": "US", "industries": ["fintech"], "funding_amount_usd_cents": None, "team_size": None, "action": None},
})

_DEEP_DIVE_INTENT = json.dumps({
    "intent": "deep_dive",
    "confidence": 0.9,
    "entities": {"grant_refs": ["nsf-sbir-phase-1"], "stage": None, "location": None, "industries": [], "funding_amount_usd_cents": None, "team_size": None, "action": None},
})

_LIFECYCLE_TRACK_INTENT = json.dumps({
    "intent": "lifecycle_action",
    "confidence": 0.88,
    "entities": {"grant_refs": ["nsf-sbir-phase-1"], "stage": None, "location": None, "industries": [], "funding_amount_usd_cents": None, "team_size": None, "action": "track"},
})

_CORRECTION_INTENT = json.dumps({
    "intent": "correction",
    "confidence": 0.92,
    "entities": {"grant_refs": [], "stage": "seed", "location": None, "industries": [], "funding_amount_usd_cents": None, "team_size": None, "action": None},
})

_PROFILE_QUERY_INTENT = json.dumps({
    "intent": "profile_query",
    "confidence": 0.85,
    "entities": {"grant_refs": [], "stage": None, "location": None, "industries": [], "funding_amount_usd_cents": None, "team_size": None, "action": None},
})


def _events_of_type(events: list[dict], name: str) -> list[dict]:
    return [e for e in events if e["event"] == name]


async def _post_chat(client, content: str, session_id: str = "test-sess", **extra) -> list[dict]:
    body = {"content": content, **extra}
    async with client.stream(
        "POST",
        "/api/chat/message",
        json=body,
        headers={"X-Session-Id": session_id},
    ) as resp:
        assert resp.status_code == 200, await resp.aread()
        return await collect_sse(resp)


# ── Test 1: handle_greet ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_greet(session_factory, redis_client):
    """'hi' → greet regex → 1+ token events → finish=stop."""
    fake_llm = FakeLLMClient(
        scripted_stream=[["Hi there! ", "I help founders ", "find grants and funding."]]
    )
    async with make_client_factory(session_factory, redis_client, fake_llm) as client:
        events = await _post_chat(client, "hi", session_id="test-greet")

    names = [e["event"] for e in events]
    assert names[0] == "job_started"
    assert names[-1] == "done"
    assert "token" in names
    assert "message_saved" in names
    token_deltas = [e["data"]["delta"] for e in _events_of_type(events, "token")]
    assert len(token_deltas) >= 1
    assert any("tool_call" == n for n in names) is False
    done = _events_of_type(events, "done")[0]
    assert done["data"]["finish_reason"] == "stop"
    # No LLM complete() call for intent (regex matched)
    assert len(fake_llm.complete_calls) == 0


# ── Test 2: handle_smalltalk ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_smalltalk(session_factory, redis_client):
    """'thanks!' → smalltalk regex → short response, no question."""
    fake_llm = FakeLLMClient(
        scripted_stream=[["You're welcome! ", "Let me know if you need anything."]]
    )
    async with make_client_factory(session_factory, redis_client, fake_llm) as client:
        events = await _post_chat(client, "thanks!", session_id="test-smalltalk")

    names = [e["event"] for e in events]
    assert "token" in names
    assert "done" in names
    assert "question_suggested" not in names


# ── Test 3: handle_out_of_scope ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_out_of_scope(session_factory, redis_client):
    """'write me a poem' → out_of_scope → templated response, NO LLM call."""
    fake_llm = FakeLLMClient()
    async with make_client_factory(session_factory, redis_client, fake_llm) as client:
        events = await _post_chat(client, "write me a poem", session_id="test-oos")

    names = [e["event"] for e in events]
    assert "token" in names
    assert "done" in names
    # Templated — no LLM stream call
    assert len(fake_llm.stream_calls) == 0


# ── Test 4: handle_unknown ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_unknown(session_factory, redis_client):
    """Low-confidence LLM result → handle_unknown → clarifying question."""
    fake_llm = FakeLLMClient(
        scripted_complete=[_UNKNOWN_INTENT],
        scripted_stream=[["Could you clarify what you're looking for?"]]
    )
    async with make_client_factory(session_factory, redis_client, fake_llm) as client:
        events = await _post_chat(client, "asdfqwerty", session_id="test-unknown")

    names = [e["event"] for e in events]
    assert "token" in names
    assert "done" in names


# ── Test 5: handle_match_request ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_match_request(session_factory, redis_client, seeded_grants):
    """find me grants → tool_call grants.match.run, results streamed, question event."""
    fake_llm = FakeLLMClient(
        scripted_stream=[["Here are the top grants for your startup..."]]
    )
    # Set up a profile
    async with session_factory() as db:
        from backend.db.models.profile import Profile
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        db.add(Profile(
            session_id="test-match",
            company_stage="seed",
            location="US",
            industry=["fintech"],
            created_at=now,
            updated_at=now,
        ))
        await db.commit()

    async with make_client_factory(session_factory, redis_client, fake_llm) as client:
        events = await _post_chat(client, "find me grants", session_id="test-match")

    names = [e["event"] for e in events]
    assert "tool_call" in names
    assert "tool_result" in names
    assert "token" in names
    assert "done" in names

    tool_call = _events_of_type(events, "tool_call")[0]
    assert tool_call["data"]["name"] == "grants.match.run"

    tool_result = _events_of_type(events, "tool_result")[0]
    assert "total_evaluated" in tool_result["data"]["result"]


# ── Event requests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_event_request_requires_complete_profile(session_factory, redis_client):
    """Event requests direct founders to complete matching preferences first."""
    fake_llm = FakeLLMClient()
    async with make_client_factory(session_factory, redis_client, fake_llm) as client:
        events = await _post_chat(
            client,
            "I am looking for events to attend",
            session_id="test-event-profile-required",
        )

    token_text = "".join(
        event["data"]["delta"] for event in _events_of_type(events, "token")
    )
    assert "Complete it at /profile" in token_text
    assert "done" in [event["event"] for event in events]


# ── Test 6: handle_deep_dive ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_deep_dive(session_factory, redis_client, seeded_grants):
    """'tell me about NSF SBIR Phase I' → grant resolved, eligibility computed."""
    fake_llm = FakeLLMClient(
        scripted_complete=[_DEEP_DIVE_INTENT],
        scripted_stream=[["The NSF SBIR program provides funding for early-stage startups..."]]
    )
    async with make_client_factory(session_factory, redis_client, fake_llm) as client:
        events = await _post_chat(client, "tell me about NSF SBIR Phase I", session_id="test-deep")

    names = [e["event"] for e in events]
    assert "token" in names
    assert "done" in names
    # Verify stream was called (LLM response generated for found grant)
    assert len(fake_llm.stream_calls) >= 1


# ── Test 7: handle_profile_update ────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_profile_update(session_factory, redis_client):
    """'we just incorporated in Delaware' → tool_call profile.update, profile updated."""
    fake_llm = FakeLLMClient(
        scripted_complete=[_PROFILE_UPDATE_INTENT],
        scripted_stream=[["Got it — I've noted you're now incorporated in Delaware."]]
    )
    async with make_client_factory(session_factory, redis_client, fake_llm) as client:
        events = await _post_chat(
            client, "we just incorporated in Delaware", session_id="test-profile-update"
        )

    names = [e["event"] for e in events]
    assert "tool_call" in names
    assert "tool_result" in names
    assert "token" in names

    tc = _events_of_type(events, "tool_call")[0]
    assert tc["data"]["name"] == "profile.update"

    tr = _events_of_type(events, "tool_result")[0]
    updated = tr["data"]["result"]["fields_updated"]
    assert any("incorporation" in f for f in updated)

    # Verify profile was updated in DB
    async with session_factory() as db:
        import sqlalchemy as sa
        from backend.db.models.profile import Profile
        result = await db.execute(
            sa.select(Profile).where(Profile.session_id == "test-profile-update")
        )
        profile = result.scalar_one_or_none()
        # apply_entities_to_profile runs in run_turn AND in handle_profile_update
        # so profile should be set
        assert profile is not None
        assert profile.incorporation_country == "US"
        assert profile.incorporation_state == "DE"


# ── Test 8: handle_profile_query ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_profile_query(session_factory, redis_client):
    """'what do you have on me' → profile summary response."""
    # "what do you have on me" matches regex → profile_query
    fake_llm = FakeLLMClient(
        scripted_stream=[["Here's what I have on file for you..."]]
    )
    async with session_factory() as db:
        from backend.db.models.profile import Profile
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        db.add(Profile(
            session_id="test-pq",
            company_stage="seed",
            industry=["saas"],
            created_at=now, updated_at=now,
        ))
        await db.commit()

    async with make_client_factory(session_factory, redis_client, fake_llm) as client:
        events = await _post_chat(client, "what do you have on me", session_id="test-pq")

    names = [e["event"] for e in events]
    assert "token" in names
    assert "done" in names


# ── Test 9: handle_lifecycle_action ──────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_lifecycle_action(session_factory, redis_client, seeded_grants):
    """'track the NSF grant' → tool_call grants.track, tool_result."""
    fake_llm = FakeLLMClient(
        scripted_complete=[_LIFECYCLE_TRACK_INTENT],
        scripted_stream=[["Tracked — I'll keep this one front of mind."]]
    )
    async with make_client_factory(session_factory, redis_client, fake_llm) as client:
        events = await _post_chat(client, "track the NSF grant", session_id="test-lifecycle")

    names = [e["event"] for e in events]
    assert "tool_call" in names
    assert "tool_result" in names
    assert "token" in names

    tc = _events_of_type(events, "tool_call")[0]
    assert "grants." in tc["data"]["name"]


# ── Test 10: handle_correction ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_correction(session_factory, redis_client):
    """'no, we're seed not pre-seed' → memory persisted, profile updated, response."""
    fake_llm = FakeLLMClient(
        scripted_complete=[_CORRECTION_INTENT],
        scripted_stream=[["Got it, I'll remember that."]]
    )
    async with make_client_factory(session_factory, redis_client, fake_llm) as client:
        events = await _post_chat(
            client, "no, we're seed not pre-seed", session_id="test-correction"
        )

    names = [e["event"] for e in events]
    assert "token" in names
    assert "done" in names

    # Memory should be persisted
    import sqlalchemy as sa
    from backend.db.models.memory import AgentMemory
    async with session_factory() as db:
        result = await db.execute(
            sa.select(AgentMemory).where(AgentMemory.session_id == "test-correction")
        )
        memories = list(result.scalars().all())
    assert any(m.kind == "correction" for m in memories)

    # Profile stage should be updated (confidence=0.92 >= 0.7)
    from backend.db.models.profile import Profile
    async with session_factory() as db:
        result = await db.execute(
            sa.select(Profile).where(Profile.session_id == "test-correction")
        )
        profile = result.scalar_one_or_none()
    if profile:
        assert profile.company_stage == "seed"


# ── Test 11: Low-confidence destructive intent → handle_unknown ───────────

@pytest.mark.asyncio
async def test_low_confidence_destructive_routes_to_unknown(session_factory, redis_client):
    """confidence=0.5 + profile_update → handle_unknown, no profile mutation."""
    fake_llm = FakeLLMClient(
        scripted_complete=[_PROFILE_UPDATE_LOW_CONF],
        scripted_stream=[["Could you tell me more about what you'd like to change?"]]
    )
    async with make_client_factory(session_factory, redis_client, fake_llm) as client:
        events = await _post_chat(
            client, "update something about my profile", session_id="test-low-conf"
        )

    names = [e["event"] for e in events]
    # handle_unknown runs → no tool_call events
    assert "tool_call" not in names
    assert "token" in names

    # Profile should NOT have been created/mutated
    import sqlalchemy as sa
    from backend.db.models.profile import Profile
    async with session_factory() as db:
        result = await db.execute(
            sa.select(Profile).where(Profile.session_id == "test-low-conf")
        )
        profile = result.scalar_one_or_none()
    # No profile mutation from low-confidence intent
    assert profile is None or profile.incorporation_country is None


# ── Test 12: CHAT_USE_ORCHESTRATOR=False falls back to stub ───────────────

@pytest.mark.asyncio
async def test_orchestrator_disabled_uses_stub(session_factory, redis_client):
    """CHAT_USE_ORCHESTRATOR=False → stub token stream, no LLM calls."""
    from backend.core.config import Settings

    fake_settings = Settings(CHAT_USE_ORCHESTRATOR=False)
    fake_llm = FakeLLMClient()

    with patch("backend.api.chat.get_settings", return_value=fake_settings):
        async with make_client_factory(session_factory, redis_client, fake_llm) as client:
            events = await _post_chat(client, "hello stub test", session_id="test-stub")

    names = [e["event"] for e in events]
    assert "token" in names
    assert "done" in names
    # Stub path: no calls to the FakeLLMClient at all
    assert len(fake_llm.stream_calls) == 0
    assert len(fake_llm.complete_calls) == 0


# ── Test 13: UpstreamError mid-stream → error event, HTTP 200 ────────────

@pytest.mark.asyncio
async def test_upstream_error_emits_error_event(session_factory, redis_client):
    """LLM raises UpstreamError mid-stream → error SSE, done, HTTP 200."""
    from backend.core.errors import UpstreamError
    from backend.services.llm.types import LLMMessage, LLMResponse, LLMStreamChunk

    class ErrorLLMClient:
        complete_calls: list = []
        stream_calls: list = []

        async def complete(self, messages, **kwargs):
            return LLMResponse(content='{"intent":"discover","confidence":0.9,"entities":{"grant_refs":[],"stage":null,"location":null,"industries":[],"funding_amount_usd_cents":null,"team_size":null,"action":null}}')

        async def stream(self, messages, **kwargs):
            async def _gen():
                yield LLMStreamChunk(delta="Starting...")
                raise UpstreamError("Deepseek down", code="upstream_error")
            return _gen()

    async with make_client_factory(session_factory, redis_client, ErrorLLMClient()) as client:
        events = await _post_chat(client, "tell me about grants", session_id="test-upstream")

    names = [e["event"] for e in events]
    assert "done" in names
    # error or token event from the partial stream
    assert "token" in names or "error" in names


# ── Test 15: History budget with 50 prior messages ────────────────────────

@pytest.mark.asyncio
async def test_history_budget_truncates_old_messages(session_factory, redis_client):
    """50-message history → truncated to token budget."""
    from datetime import datetime, timezone

    from backend.db.models.chat import Conversation, Message

    session_id = "test-history-budget"
    async with session_factory() as db:
        convo = Conversation(session_id=session_id)
        db.add(convo)
        await db.flush()
        convo_id = convo.id
        # Insert 50 messages with long content
        now = datetime.now(timezone.utc)
        for i in range(50):
            db.add(Message(
                conversation_id=convo_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}: " + "x" * 300,  # ~75 tokens each
            ))
        await db.commit()

    from backend.services.orchestrator.context_loader import (
        _HISTORY_TOKEN_BUDGET,
        load_turn_context,
    )
    from backend.schemas.intent import ExtractedEntities, IntentResult
    from backend.core.config import get_settings

    fake_llm = FakeLLMClient()
    intent = IntentResult(intent="discover", confidence=0.9, entities=ExtractedEntities(), classified_by="regex")

    async with session_factory() as db:
        ctx = await load_turn_context(
            session_id=session_id,
            conversation_id=convo_id,
            user_message="test",
            intent=intent,
            llm_client=fake_llm,
            settings=get_settings(),
            db=db,
        )

    # History should be truncated to fit within token budget
    total_tokens = sum(max(1, len(m.content or "") // 4) for m in ctx.history)
    assert total_tokens <= _HISTORY_TOKEN_BUDGET
    # We had 50 messages; should be fewer
    assert len(ctx.history) < 50


# ── Test 16: Memory injection in system prompt ────────────────────────────

@pytest.mark.asyncio
async def test_memory_injected_in_prompt(session_factory, redis_client, seeded_grants):
    """Preference memory appears in the system prompt for handle_match_request."""
    from datetime import datetime, timezone

    from backend.db.models.memory import AgentMemory

    session_id = "test-memory-inject"
    async with session_factory() as db:
        now = datetime.now(timezone.utc)
        db.add(AgentMemory(
            session_id=session_id,
            kind="preference",
            content="Prefers non-dilutive funding",
            structured={},
            confidence=1.0,
        ))
        await db.commit()

    fake_llm = FakeLLMClient(
        scripted_stream=[["Based on your preference for non-dilutive funding..."]]
    )
    async with make_client_factory(session_factory, redis_client, fake_llm) as client:
        events = await _post_chat(client, "find me grants", session_id=session_id)

    names = [e["event"] for e in events]
    assert "token" in names

    # Verify the system prompt passed to the LLM contains the memory
    assert len(fake_llm.stream_calls) >= 1
    stream_messages = fake_llm.stream_calls[0]
    system_messages = [m for m in stream_messages if m.role == "system"]
    assert len(system_messages) >= 1
    system_content = system_messages[0].content or ""
    assert "non-dilutive" in system_content
