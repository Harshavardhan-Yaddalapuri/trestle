from __future__ import annotations

from typing import Any, AsyncIterator

from backend.core.config import get_settings
from backend.services.llm import get_llm_client as _get_singleton_client
from backend.services.llm.base import LLMClient
from backend.services.llm.types import LLMMessage, LLMResponse, LLMStreamChunk


class _DisabledLLMClient:
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        raise RuntimeError("llm_client_disabled")

    async def stream(
        self,
        messages: list[LLMMessage],
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamChunk]:
        raise RuntimeError("llm_client_disabled")


_DISABLED_LLM_CLIENT = _DisabledLLMClient()


def get_llm_client() -> LLMClient:
    """FastAPI dependency returning the configured multi-provider LLM client."""
    settings = get_settings()
    if not settings.CHAT_USE_ORCHESTRATOR:
        return _DISABLED_LLM_CLIENT
    return _get_singleton_client()
