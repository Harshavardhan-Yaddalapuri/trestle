from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from backend.services.orchestrator.events import FinishEvent, LLMTokenEvent, OrchestratorEvent

if TYPE_CHECKING:
    from backend.services.orchestrator.context_loader import TurnContext

_TEMPLATE = (
    "I'm focused on helping you find grants and funding for your startup. "
    "I'm not the right tool for that — but if you want to talk through anything related "
    "to your company or what funding might fit, I'm here for that."
)


async def handle_out_of_scope(ctx: TurnContext) -> AsyncIterator[OrchestratorEvent]:
    yield LLMTokenEvent(delta=_TEMPLATE)
    yield FinishEvent(reason="stop")
