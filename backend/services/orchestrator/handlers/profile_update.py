from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from backend.services.orchestrator.entity_application import apply_entities_to_profile
from backend.services.orchestrator.events import (
    FinishEvent,
    OrchestratorEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from backend.services.orchestrator.prompts import build_profile_update_system_prompt
from backend.services.orchestrator.response_stream import stream_llm_response

if TYPE_CHECKING:
    from backend.services.orchestrator.context_loader import TurnContext


async def handle_profile_update(ctx: TurnContext) -> AsyncIterator[OrchestratorEvent]:
    entities = ctx.intent.entities
    yield ToolCallEvent(
        name="profile.update",
        args={
            "stage": entities.stage,
            "location": entities.location,
            "industries": entities.industries,
            "team_size": entities.team_size,
            "funding_amount_usd_cents": entities.funding_amount_usd_cents,
        },
    )

    fields_updated = await apply_entities_to_profile(
        ctx.session_id, entities, ctx.intent.confidence, ctx.db
    )
    yield ToolResultEvent(
        name="profile.update",
        result={"fields_updated": fields_updated},
    )

    system_prompt = build_profile_update_system_prompt(ctx, fields_updated)
    async for event in stream_llm_response(ctx, system_prompt):
        yield event
