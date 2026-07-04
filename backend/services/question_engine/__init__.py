"""Opportunistic question engine.

Given (profile, intent, optional match_context), decides whether to ask a
clarifying question and which one.  All phrasing is templated — no LLM here.
"""
from __future__ import annotations

from backend.schemas.intent import IntentResult
from backend.schemas.match import MatchProfile, MatchResponse
from backend.schemas.question import QuestionEngineConfig, QuestionRequest

from .gap_definitions import GAP_DEFINITIONS, Gap, _is_gap
from .scorer import ELIGIBILITY_FIELD_MAP, fields_blocked_by_match_context, relevance_for_intent
from .templates import FIELD_REASONS, QUESTION_TEMPLATES

__all__ = ["analyze_gaps", "suggest_question", "GAP_DEFINITIONS", "Gap"]

_DEFAULT_CONFIG = QuestionEngineConfig()


def analyze_gaps(profile: MatchProfile) -> list[Gap]:
    """Return all profile gaps with base weights.  Pure function, no intent context."""
    gaps: list[Gap] = []
    for gap_def in GAP_DEFINITIONS:
        # Check depends_on guard (e.g. incorporation_state only when country=US)
        if gap_def.depends_on is not None and not gap_def.depends_on(profile):
            continue
        value = getattr(profile, gap_def.field, None)
        if not _is_gap(value):
            continue
        question_text = QUESTION_TEMPLATES.get(gap_def.template_key, gap_def.field)
        gaps.append(
            Gap(
                field=gap_def.field,
                base_weight=gap_def.base_weight,
                question_text=question_text,
                response_options=gap_def.options or [],
            )
        )
    return gaps


def suggest_question(
    profile: MatchProfile,
    intent: IntentResult,
    match_context: MatchResponse | None = None,
    config: QuestionEngineConfig = _DEFAULT_CONFIG,
) -> QuestionRequest | None:
    """Return the highest-priority question above threshold, or None."""
    gaps = analyze_gaps(profile)
    if not gaps:
        return None

    # Build a map of field → detail from insufficient_profile_data fails in match_context
    context_reasons: dict[str, str] = {}
    if match_context is not None:
        for result in match_context.results:
            for fail in result.hard_fails:
                if fail.code == "insufficient_profile_data":
                    for f in ELIGIBILITY_FIELD_MAP.get(fail.rule, []):
                        if f not in context_reasons:
                            context_reasons[f] = fail.detail

    # Score each gap: priority = base_weight × relevance (with match_context bonus baked in)
    scored: list[tuple[float, int, Gap]] = []
    for idx, gap in enumerate(gaps):
        relevance = relevance_for_intent(
            gap.field, intent.intent, intent.entities, match_context
        )
        priority = round(gap.base_weight * relevance, 4)
        scored.append((priority, idx, gap))

    # Sort by priority descending; use list index as stable tiebreaker
    scored.sort(key=lambda x: (-x[0], x[1]))

    best_priority, _idx, best_gap = scored[0]
    if best_priority < config.min_priority_to_ask:
        return None

    reason = context_reasons.get(
        best_gap.field,
        FIELD_REASONS.get(best_gap.field, f"needed to evaluate grant eligibility for {best_gap.field}"),
    )

    return QuestionRequest(
        field=best_gap.field,
        question=best_gap.question_text,
        reason=reason,
        intent_context=intent.intent,
        response_options=best_gap.response_options,
        free_form_ok=True,
        priority_score=best_priority,
    )
