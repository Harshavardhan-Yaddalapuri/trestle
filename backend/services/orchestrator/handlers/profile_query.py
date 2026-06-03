from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from backend.services.orchestrator.context_loader import profile_out_to_match_profile
from backend.services.orchestrator.events import FinishEvent, OrchestratorEvent, QuestionEvent
from backend.services.orchestrator.prompts import build_profile_query_system_prompt
from backend.services.orchestrator.response_stream import stream_llm_response
from backend.services.question_engine import suggest_question

if TYPE_CHECKING:
    from backend.services.orchestrator.context_loader import TurnContext


async def handle_profile_query(ctx: TurnContext) -> AsyncIterator[OrchestratorEvent]:
    finish_reason = "stop"
    async for event in stream_llm_response(ctx, build_profile_query_system_prompt(ctx)):
        if isinstance(event, FinishEvent):
            finish_reason = event.reason
        else:
            yield event

    match_profile = profile_out_to_match_profile(ctx.profile)
    question = suggest_question(match_profile, ctx.intent, ctx.match_context)
    if question is not None:
        yield QuestionEvent(
            question_text=question.question,
            profile_field=question.field,
            options=[{"label": o.label, "value": o.value} for o in question.response_options],
        )

    yield FinishEvent(reason=finish_reason)
