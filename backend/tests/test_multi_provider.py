"""Unit tests for MultiProviderClient, circuit breaker, and provider fallback.

Covers:
- Fallback chain when primary fails
- Circuit breaker open → skip provider
- Stream fallback (init failure only)
- All providers exhausted raises UpstreamError
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.core.errors import UpstreamError
from backend.services.llm.circuit import CircuitBreaker, CircuitOpenError
from backend.services.llm.multi_provider import MultiProviderClient
from backend.services.llm.types import LLMMessage, LLMResponse, LLMStreamChunk


def _make_client(fail_with: UpstreamError | None = None, stream_fail: bool = False) -> Any:
    """Build a mock LLM client."""
    client = MagicMock()
    if fail_with is not None:
        client.complete = AsyncMock(side_effect=fail_with)
        if stream_fail:
            client.stream = AsyncMock(side_effect=fail_with)
        else:
            async def _stream_coro(*a, **k):
                async def _gen():
                    yield LLMStreamChunk(delta="ok", finish_reason="stop")
                return _gen()
            client.stream = _stream_coro
    else:
        client.complete = AsyncMock(
            return_value=LLMResponse(content="ok", finish_reason="stop")
        )
        async def _stream_coro(*a, **k):
            async def _gen():
                yield LLMStreamChunk(delta="ok", finish_reason="stop")
            return _gen()
        client.stream = _stream_coro
    return client


# ── complete() fallback ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_complete_uses_primary_when_healthy():
    primary = _make_client()
    fallback = _make_client()
    mpc = MultiProviderClient(primary=primary, fallbacks=[fallback], primary_name="p")

    result = await mpc.complete([LLMMessage(role="user", content="hi")])

    assert result.content == "ok"
    primary.complete.assert_awaited_once()
    fallback.complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_complete_falls_back_when_primary_fails():
    primary = _make_client(fail_with=UpstreamError("boom", code="upstream_5xx"))
    fallback = _make_client()
    mpc = MultiProviderClient(primary=primary, fallbacks=[fallback], primary_name="p")

    result = await mpc.complete([LLMMessage(role="user", content="hi")])

    assert result.content == "ok"
    primary.complete.assert_awaited_once()
    fallback.complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_complete_raises_when_all_fail():
    primary = _make_client(fail_with=UpstreamError("p fail", code="upstream_5xx"))
    fb1 = _make_client(fail_with=UpstreamError("fb1 fail", code="rate_limited"))
    mpc = MultiProviderClient(primary=primary, fallbacks=[fb1], primary_name="p")

    with pytest.raises(UpstreamError) as exc_info:
        await mpc.complete([LLMMessage(role="user", content="hi")])

    assert exc_info.value.code == "all_providers_failed"


@pytest.mark.asyncio
async def test_complete_skips_open_circuit():
    primary = _make_client(fail_with=UpstreamError("boom", code="upstream_5xx"))
    # No fallback — once circuit opens we should get circuit_open error
    mpc = MultiProviderClient(primary=primary, fallbacks=[], primary_name="p")

    # Trip the circuit (threshold=3)
    for _ in range(3):
        with pytest.raises(UpstreamError):
            await mpc.complete([LLMMessage(role="user", content="hi")])

    # 4th call — primary circuit is open, no fallback
    with pytest.raises(UpstreamError) as exc_info:
        await mpc.complete([LLMMessage(role="user", content="hi")])

    assert exc_info.value.code == "all_providers_failed"
    # Primary should NOT have been called this time (circuit open)
    assert primary.complete.await_count == 3


# ── stream() fallback ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stream_falls_back_on_init_failure():
    primary = _make_client(fail_with=UpstreamError("stream fail", code="upstream_5xx"), stream_fail=True)
    fallback = _make_client()
    mpc = MultiProviderClient(primary=primary, fallbacks=[fallback], primary_name="p")

    chunks = []
    async for chunk in await mpc.stream([LLMMessage(role="user", content="hi")]):
        chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0].delta == "ok"


@pytest.mark.asyncio
async def test_stream_raises_when_all_fail():
    primary = _make_client(fail_with=UpstreamError("p fail", code="upstream_5xx"), stream_fail=True)
    fb1 = _make_client(fail_with=UpstreamError("fb1 fail", code="rate_limited"), stream_fail=True)
    mpc = MultiProviderClient(primary=primary, fallbacks=[fb1], primary_name="p")

    with pytest.raises(UpstreamError) as exc_info:
        async for _ in await mpc.stream([LLMMessage(role="user", content="hi")]):
            pass

    assert exc_info.value.code == "all_providers_failed"


# ── CircuitBreaker ──────────────────────────────────────────────────────────

def test_circuit_starts_closed():
    cb = CircuitBreaker("test")
    assert cb.can_call() is True


def test_circuit_opens_after_threshold():
    cb = CircuitBreaker("test", failure_threshold=2, window_seconds=60)
    cb.record_failure()
    cb.record_failure()
    assert cb.can_call() is False


def test_circuit_half_opens_after_cooldown():
    cb = CircuitBreaker("test", failure_threshold=1, cooldown_seconds=0.01)
    cb.record_failure()
    assert cb.can_call() is False
    # Wait for cooldown
    import time
    time.sleep(0.02)
    assert cb.can_call() is True  # half-open


def test_circuit_closes_on_probe_success():
    cb = CircuitBreaker("test", failure_threshold=1, cooldown_seconds=0.01)
    cb.record_failure()
    import time
    time.sleep(0.02)
    assert cb.can_call() is True
    cb.record_success()
    assert cb.can_call() is True


def test_circuit_open_error_detail():
    err = CircuitOpenError("my_provider")
    assert err.code == "circuit_open"
    assert "my_provider" in err.detail
