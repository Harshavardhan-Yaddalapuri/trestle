from __future__ import annotations

from typing import Any, AsyncIterator, Protocol, runtime_checkable

from backend.services.llm.types import LLMMessage, LLMResponse, LLMStreamChunk


@runtime_checkable
class LLMClient(Protocol):
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> LLMResponse: ...

    async def stream(
        self,
        messages: list[LLMMessage],
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamChunk]: ...
