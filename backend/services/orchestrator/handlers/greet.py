from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from backend.services.orchestrator.events import OrchestratorEvent
from backend.services.orchestrator.prompts import build_greet_system_prompt
from backend.services.orchestrator.response_stream import stream_llm_response

if TYPE_CHECKING:
    from backend.services.orchestrator.context_loader import TurnContext


async def handle_greet(ctx: TurnContext) -> AsyncIterator[OrchestratorEvent]:
    async for event in stream_llm_response(ctx, build_greet_system_prompt(ctx)):
        yield event
