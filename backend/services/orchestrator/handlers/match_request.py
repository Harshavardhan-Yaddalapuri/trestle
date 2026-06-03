from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from backend.schemas.match import MatchRequest, MatchResponse
from backend.services.matching_orchestration import run_matching
from backend.services.orchestrator.context_loader import profile_out_to_match_profile
from backend.services.orchestrator.events import (
    FinishEvent,
    OrchestratorEvent,
    QuestionEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from backend.services.orchestrator.prompts import build_match_request_system_prompt
from backend.services.orchestrator.response_stream import stream_llm_response
from backend.services.question_engine import suggest_question

if TYPE_CHECKING:
    from backend.services.orchestrator.context_loader import TurnContext


def _format_results(match_response: MatchResponse) -> str:
    if not match_response.results:
        return "No eligible grants found in the current catalog."
    lines: list[str] = []
    for i, r in enumerate(match_response.results[:5], 1):
        g = r.grant
        line_parts = [f"{i}. **{g.name}** ({g.provider_name})"]
        line_parts.append(f"   Score: {r.score:.2f} | Tier: {r.tier} | Amount: {g.amount_display}")
        if g.deadline:
            line_parts.append(f"   Deadline: {g.deadline}")
        line_parts.append(f"   {r.explanation}")
        if r.hard_fails:
            line_parts.append(f"   Hard fails: {'; '.join(f.detail for f in r.hard_fails)}")
        lines.extend(line_parts)
        lines.append("")
    return "\n".join(lines)


async def handle_match_request(ctx: TurnContext) -> AsyncIterator[OrchestratorEvent]:
    entities = ctx.intent.entities
    overrides = MatchRequest(
        stage=entities.stage,
        location=entities.location,
        industry=entities.industries or None,
        limit=5,
    )

    yield ToolCallEvent(name="grants.match.run", args={"overrides": overrides.model_dump()})
    match_response = await run_matching(ctx.session_id, ctx.db, overrides=overrides, limit=5)
    yield ToolResultEvent(
        name="grants.match.run",
        result={
            "total_evaluated": match_response.total_evaluated,
            "total_returned": match_response.total_returned,
            "top_tiers": [r.tier for r in match_response.results[:3]],
        },
    )

    # Update match_context so question engine can boost relevant field questions
    ctx.match_context = match_response

    results_text = _format_results(match_response)
    system_prompt = build_match_request_system_prompt(ctx, results_text)

    finish_reason = "stop"
    async for event in stream_llm_response(ctx, system_prompt):
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
