from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from backend.services.orchestrator.entity_application import (
    CONFIDENCE_THRESHOLD,
    apply_entities_to_profile,
)
from backend.services.orchestrator.events import OrchestratorEvent
from backend.services.orchestrator.prompts import build_correction_system_prompt
from backend.services.orchestrator.response_stream import stream_llm_response

if TYPE_CHECKING:
    from backend.services.orchestrator.context_loader import TurnContext


async def handle_correction(ctx: TurnContext) -> AsyncIterator[OrchestratorEvent]:
    # Memory was already persisted in run_turn. Apply any profile-relevant entities.
    entities = ctx.intent.entities
    has_profile_entities = any([
        entities.stage,
        entities.location,
        entities.industries,
        entities.team_size is not None,
        entities.funding_amount_usd_cents is not None,
    ])
    if has_profile_entities and ctx.intent.confidence >= CONFIDENCE_THRESHOLD:
        await apply_entities_to_profile(
            ctx.session_id, entities, ctx.intent.confidence, ctx.db
        )

    async for event in stream_llm_response(ctx, build_correction_system_prompt(ctx)):
        yield event
