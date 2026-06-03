"""Tests for the two-stage intent classifier."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock

import pytest
import respx
from httpx import Response

from backend.core.errors import UpstreamError
from backend.schemas.intent import ExtractedEntities, IntentResult
from backend.services.intent.classifier import classify
from backend.services.llm.base import LLMClient
from backend.services.llm.types import LLMMessage, LLMResponse, LLMStreamChunk


# ── FakeLLMClient ─────────────────────────────────────────────────────────


class FakeLLMClient:
    """Scriptable fake LLM client for tests."""

    def __init__(self, response: LLMResponse | Exception) -> None:
        self._response = response

    async def complete(
        self,
        messages: list[LLMMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        if isinstance(self._response, Exception):
            raise self._response
        return self._response

    async def stream(
        self,
        messages: list[LLMMessage],
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamChunk]:
        async def _empty():
            return
            yield  # make it an async generator

        return _empty()


def _fake_llm(payload: dict[str, Any]) -> FakeLLMClient:
    return FakeLLMClient(LLMResponse(content=json.dumps(payload)))


# ── Regex path tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_greet_regex():
    result = await classify("hi", FakeLLMClient(Exception("should not call LLM")))
    assert result.intent == "greet"
    assert result.confidence >= 0.9
    assert result.classified_by == "regex"
    assert not respx.calls


@pytest.mark.asyncio
@respx.mock
async def test_match_request_regex():
    result = await classify(
        "Find me grants for AI safety",
        FakeLLMClient(Exception("should not call LLM")),
    )
    assert result.intent == "match_request"
    assert result.classified_by == "regex"
    assert not respx.calls


@pytest.mark.asyncio
@respx.mock
async def test_profile_query_regex():
    result = await classify(
        "What do you have on file for me?",
        FakeLLMClient(Exception("should not call LLM")),
    )
    assert result.intent == "profile_query"
    assert result.classified_by == "regex"
    assert not respx.calls


@pytest.mark.asyncio
@respx.mock
async def test_lifecycle_track_regex():
    result = await classify(
        "Track NSF SBIR",
        FakeLLMClient(Exception("should not call LLM")),
    )
    assert result.intent == "lifecycle_action"
    assert result.entities.action == "track"
    # grant_refs should contain something matching NSF or SBIR
    refs_text = " ".join(result.entities.grant_refs)
    assert "NSF" in refs_text or "SBIR" in refs_text
    assert result.classified_by == "regex"
    assert not respx.calls


@pytest.mark.asyncio
@respx.mock
async def test_smalltalk_regex():
    result = await classify(
        "thanks!",
        FakeLLMClient(Exception("should not call LLM")),
    )
    assert result.intent == "smalltalk"
    assert result.classified_by == "regex"
    assert not respx.calls


@pytest.mark.asyncio
@respx.mock
async def test_empty_string_no_llm():
    result = await classify("", FakeLLMClient(Exception("should not call LLM")))
    assert result.intent == "unknown"
    assert result.confidence == 0.0
    assert result.classified_by == "regex"
    assert not respx.calls


@pytest.mark.asyncio
@respx.mock
async def test_whitespace_only_no_llm():
    result = await classify("   ", FakeLLMClient(Exception("should not call LLM")))
    assert result.intent == "unknown"
    assert result.confidence == 0.0
    assert not respx.calls


# ── LLM path tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_llm_profile_update():
    payload = {
        "intent": "profile_update",
        "confidence": 0.95,
        "entities": {
            "grant_refs": [],
            "stage": None,
            "location": "US-DE",
            "industries": [],
            "funding_amount_usd_cents": None,
            "team_size": 4,
            "action": None,
        },
    }
    result = await classify(
        "We just incorporated in Delaware and have 4 people now",
        _fake_llm(payload),
    )
    assert result.intent == "profile_update"
    assert result.classified_by == "llm"
    assert result.entities.location == "US-DE"
    assert result.entities.team_size == 4


@pytest.mark.asyncio
async def test_llm_deep_dive():
    payload = {
        "intent": "deep_dive",
        "confidence": 0.92,
        "entities": {
            "grant_refs": ["activate-fellowship"],
            "stage": None,
            "location": None,
            "industries": [],
            "funding_amount_usd_cents": None,
            "team_size": None,
            "action": None,
        },
    }
    result = await classify(
        "Tell me more about the Activate Fellowship",
        _fake_llm(payload),
    )
    assert result.intent == "deep_dive"
    assert result.classified_by == "llm"
    assert "activate-fellowship" in result.entities.grant_refs


@pytest.mark.asyncio
async def test_llm_malformed_json_returns_unknown():
    fake = FakeLLMClient(LLMResponse(content="not-valid-json{{{"))
    result = await classify(
        "Something ambiguous that bypasses regex",
        fake,
    )
    assert result.intent == "unknown"
    assert result.confidence == 0.0
    assert result.classified_by == "llm"


@pytest.mark.asyncio
async def test_llm_upstream_error_reraises():
    fake = FakeLLMClient(UpstreamError("Deepseek 500", code="upstream_5xx"))
    with pytest.raises(UpstreamError):
        await classify(
            "Something ambiguous that bypasses regex",
            fake,
        )


@pytest.mark.asyncio
async def test_llm_timeout_raises_upstream_error():
    fake = FakeLLMClient(UpstreamError("timeout", code="timeout"))
    with pytest.raises(UpstreamError) as exc_info:
        await classify(
            "Something ambiguous that bypasses regex",
            fake,
        )
    assert exc_info.value.code == "timeout"


# ── FakeLLMClient injection test ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_fake_llm_client_injection():
    """FakeLLMClient satisfies the LLMClient protocol and can be injected."""
    payload = {
        "intent": "discover",
        "confidence": 0.8,
        "entities": {
            "grant_refs": [],
            "stage": None,
            "location": None,
            "industries": [],
            "funding_amount_usd_cents": None,
            "team_size": None,
            "action": None,
        },
    }
    fake = _fake_llm(payload)
    assert isinstance(fake, LLMClient)
    result = await classify("Tell me about different kinds of funding out there", fake)
    assert result.intent == "discover"
    assert result.classified_by == "llm"


# ── DeepseekClient error-mapping test ────────────────────────────────────


@pytest.mark.asyncio
async def test_deepseek_maps_rate_limit_to_upstream_error():
    """DeepseekClient wraps openai RateLimitError → UpstreamError(code='rate_limited')."""
    import openai

    from backend.services.llm.deepseek import _map_openai_error

    import httpx

    mock_response = httpx.Response(429, request=httpx.Request("POST", "https://api.deepseek.com"))
    exc = openai.RateLimitError(
        "rate limited",
        response=mock_response,
        body=None,
    )
    err = _map_openai_error(exc)
    assert isinstance(err, UpstreamError)
    assert err.code == "rate_limited"
