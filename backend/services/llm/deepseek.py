from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

import openai

from backend.core.config import get_settings
from backend.core.errors import UpstreamError
from backend.core.logging import get_logger
from backend.services.llm.types import (
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
    LLMToolCall,
    LLMUsage,
)

logger = get_logger(__name__)


def _map_openai_error(exc: Exception) -> UpstreamError:
    if isinstance(exc, openai.AuthenticationError):
        return UpstreamError("Deepseek authentication failed", code="auth_error")
    if isinstance(exc, openai.RateLimitError):
        return UpstreamError("Deepseek rate limit exceeded", code="rate_limited")
    if isinstance(exc, (openai.APITimeoutError, asyncio.TimeoutError)):
        return UpstreamError("Deepseek request timed out", code="timeout")
    if isinstance(exc, openai.InternalServerError):
        return UpstreamError("Deepseek internal error", code="upstream_5xx")
    if isinstance(exc, openai.APIConnectionError):
        return UpstreamError("Deepseek connection error", code="connection_error")
    return UpstreamError(f"Deepseek error: {exc}", code="upstream_error")


class DeepseekClient:
    def __init__(self) -> None:
        settings = get_settings()
        key = settings.DEEPSEEK_API_KEY.get_secret_value()
        self._model = settings.DEEPSEEK_MODEL
        self._timeout = settings.LLM_TIMEOUT_SECONDS
        self._max_retries = settings.LLM_MAX_RETRIES
        self._client = openai.AsyncOpenAI(
            api_key=key,
            base_url=settings.DEEPSEEK_BASE_URL,
            timeout=self._timeout,
            max_retries=self._max_retries,
        )

    def _to_openai_messages(self, messages: list[LLMMessage]) -> list[dict[str, Any]]:
        result = []
        for m in messages:
            msg: dict[str, Any] = {"role": m.role}
            if m.content is not None:
                msg["content"] = m.content
            if m.tool_calls:
                msg["tool_calls"] = m.tool_calls
            result.append(msg)
        return result

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        call_kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": self._to_openai_messages(messages),
            **kwargs,
        }
        if tools:
            call_kwargs["tools"] = tools
        if response_format:
            call_kwargs["response_format"] = response_format

        try:
            resp = await self._client.chat.completions.create(**call_kwargs)
        except (
            openai.AuthenticationError,
            openai.RateLimitError,
            openai.APITimeoutError,
            openai.InternalServerError,
            openai.APIConnectionError,
        ) as exc:
            raise _map_openai_error(exc) from exc

        choice = resp.choices[0]
        msg = choice.message
        tool_calls: list[LLMToolCall] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(
                    LLMToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                    )
                )

        usage = LLMUsage(
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=resp.usage.total_tokens if resp.usage else 0,
        )
        return LLMResponse(
            content=msg.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            usage=usage,
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamChunk]:
        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=self._to_openai_messages(messages),
                stream=True,
                **kwargs,
            )
        except (
            openai.AuthenticationError,
            openai.RateLimitError,
            openai.APITimeoutError,
            openai.InternalServerError,
            openai.APIConnectionError,
        ) as exc:
            raise _map_openai_error(exc) from exc

        async def _gen() -> AsyncIterator[LLMStreamChunk]:
            async for chunk in stream:
                choice = chunk.choices[0] if chunk.choices else None
                if choice is None:
                    continue
                delta_content = (
                    choice.delta.content if choice.delta else None
                )
                yield LLMStreamChunk(
                    delta=delta_content,
                    finish_reason=choice.finish_reason,
                )

        return _gen()
