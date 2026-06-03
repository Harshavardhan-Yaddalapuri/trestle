"""Scriptable LLM client for tests. Used via dep-override — never in production."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

from backend.services.llm.types import LLMMessage, LLMResponse, LLMStreamChunk

_DEFAULT_INTENT_JSON = json.dumps({
    "intent": "discover",
    "confidence": 0.85,
    "entities": {
        "grant_refs": [],
        "stage": None,
        "location": None,
        "industries": [],
        "funding_amount_usd_cents": None,
        "team_size": None,
        "action": None,
    },
})

_DEFAULT_STREAM_TOKENS = ["Hello! ", "I can help ", "you find grants."]


class FakeLLMClient:
    """Configurable fake LLM client for testing.

    Pass `scripted_complete` (list of JSON strings) for complete() calls.
    Pass `scripted_stream` (list of token-lists) for stream() calls.
    When the queue is empty, sensible defaults are returned.
    """

    def __init__(
        self,
        scripted_complete: list[str] | None = None,
        scripted_stream: list[list[str]] | None = None,
    ) -> None:
        self._complete_queue: list[str] = list(scripted_complete or [])
        self._stream_queue: list[list[str]] = list(scripted_stream or [])
        self.complete_calls: list[list[LLMMessage]] = []
        self.stream_calls: list[list[LLMMessage]] = []

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        self.complete_calls.append(messages)
        content = self._complete_queue.pop(0) if self._complete_queue else _DEFAULT_INTENT_JSON
        return LLMResponse(content=content, finish_reason="stop")

    async def stream(
        self,
        messages: list[LLMMessage],
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamChunk]:
        self.stream_calls.append(messages)
        tokens = self._stream_queue.pop(0) if self._stream_queue else list(_DEFAULT_STREAM_TOKENS)

        async def _gen() -> AsyncIterator[LLMStreamChunk]:
            for token in tokens:
                yield LLMStreamChunk(delta=token)
            yield LLMStreamChunk(finish_reason="stop")

        return _gen()
