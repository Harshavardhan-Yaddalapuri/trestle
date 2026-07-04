from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator, Protocol

from backend.services.orchestrator.events import OrchestratorEvent

if TYPE_CHECKING:
    from backend.services.orchestrator.context_loader import TurnContext


class IntentHandler(Protocol):
    async def __call__(self, ctx: TurnContext) -> AsyncIterator[OrchestratorEvent]: ...
