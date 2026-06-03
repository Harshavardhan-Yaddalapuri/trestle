from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from backend.services.llm.types import LLMMessage
from backend.services.orchestrator.events import FinishEvent, LLMTokenEvent, OrchestratorEvent

if TYPE_CHECKING:
    from backend.services.orchestrator.context_loader import TurnContext

_EMPTY_FALLBACK = "I had trouble responding to that — could you rephrase?"


async def stream_llm_response(
    ctx: TurnContext,
    system_prompt: str,
) -> AsyncIterator[OrchestratorEvent]:
    """Build messages and stream LLM response, yielding token + finish events."""
    messages = [
        LLMMessage(role="system", content=system_prompt),
        *ctx.history,
        LLMMessage(role="user", content=ctx.user_message),
    ]

    finish_reason = "stop"
    got_any = False

    stream_iter = await ctx.llm_client.stream(messages)
    async for chunk in stream_iter:
        if chunk.delta:
            got_any = True
            yield LLMTokenEvent(delta=chunk.delta)
        if chunk.finish_reason:
            finish_reason = chunk.finish_reason

    if not got_any:
        yield LLMTokenEvent(delta=_EMPTY_FALLBACK)

    yield FinishEvent(reason=finish_reason)


def estimate_input_tokens(messages: list[LLMMessage]) -> int:
    total_chars = sum(len(m.content or "") for m in messages)
    return max(1, total_chars // 4)
