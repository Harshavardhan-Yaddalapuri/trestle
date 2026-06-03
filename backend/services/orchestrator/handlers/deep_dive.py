from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, AsyncIterator

import sqlalchemy as sa

from backend.db.models.grant import Grant
from backend.schemas.match import MatchProfile
from backend.services.eligibility import evaluate_eligibility
from backend.services.orchestrator.context_loader import profile_out_to_match_profile
from backend.services.orchestrator.events import (
    FinishEvent,
    LLMTokenEvent,
    OrchestratorEvent,
    QuestionEvent,
)
from backend.services.orchestrator.prompts import build_deep_dive_system_prompt
from backend.services.orchestrator.response_stream import stream_llm_response
from backend.services.question_engine import suggest_question

if TYPE_CHECKING:
    from backend.services.orchestrator.context_loader import TurnContext


async def _resolve_grant(db, grant_ref: str) -> Grant | None:
    result = await db.execute(sa.select(Grant).where(Grant.source_id == grant_ref))
    grant = result.scalar_one_or_none()
    if grant:
        return grant
    try:
        gid = uuid.UUID(grant_ref)
        return await db.get(Grant, gid)
    except ValueError:
        pass
    result = await db.execute(
        sa.select(Grant).where(Grant.name.ilike(f"%{grant_ref}%")).limit(1)
    )
    return result.scalar_one_or_none()


def _format_grant_detail(grant: Grant) -> str:
    lines = [
        f"Name: {grant.name}",
        f"Provider: {grant.provider_name}",
        f"Type: {grant.type}",
        f"Description: {grant.description[:400]}",
    ]
    if grant.amount_min or grant.amount_max:
        mn = f"${grant.amount_min // 100:,}" if grant.amount_min else "?"
        mx = f"${grant.amount_max // 100:,}" if grant.amount_max else "?"
        lines.append(f"Amount: {mn} – {mx}")
    if grant.deadline:
        lines.append(f"Deadline: {grant.deadline}")
    elif grant.rolling:
        lines.append("Rolling deadline")
    if grant.stage:
        lines.append(f"Stage: {', '.join(grant.stage)}")
    if grant.industry:
        lines.append(f"Industries: {', '.join(grant.industry)}")
    if grant.location:
        lines.append(f"Location: {', '.join(grant.location)}")
    return "\n".join(lines)


def _format_eligibility(match_profile: MatchProfile, grant: Grant) -> str:
    elig = grant.eligibility or {}
    result = evaluate_eligibility(elig, match_profile)
    if result.passed:
        return "Eligible based on current profile."
    fails = "; ".join(f.detail for f in result.hard_fails)
    return f"Not eligible: {fails}"


async def handle_deep_dive(ctx: TurnContext) -> AsyncIterator[OrchestratorEvent]:
    grant_refs = ctx.intent.entities.grant_refs

    if not grant_refs:
        # No grant reference — fall back to clarification
        from backend.services.orchestrator.handlers.unknown import handle_unknown
        async for event in handle_unknown(ctx):
            yield event
        return

    grant = await _resolve_grant(ctx.db, grant_refs[0])
    if grant is None:
        yield LLMTokenEvent(
            delta=f"I couldn't find a grant matching '{grant_refs[0]}'. "
                  "Could you double-check the name or try a different search?"
        )
        yield FinishEvent(reason="stop")
        return

    match_profile = profile_out_to_match_profile(ctx.profile)
    grant_detail_text = _format_grant_detail(grant)
    eligibility_text = _format_eligibility(match_profile, grant)
    system_prompt = build_deep_dive_system_prompt(ctx, grant_detail_text, eligibility_text)

    finish_reason = "stop"
    async for event in stream_llm_response(ctx, system_prompt):
        if isinstance(event, FinishEvent):
            finish_reason = event.reason
        else:
            yield event

    question = suggest_question(match_profile, ctx.intent, ctx.match_context)
    if question is not None:
        yield QuestionEvent(
            question_text=question.question,
            profile_field=question.field,
            options=[{"label": o.label, "value": o.value} for o in question.response_options],
        )

    yield FinishEvent(reason=finish_reason)
