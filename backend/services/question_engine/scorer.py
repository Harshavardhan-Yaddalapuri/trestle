from __future__ import annotations

from backend.schemas.intent import ExtractedEntities, IntentLabel
from backend.schemas.match import MatchResponse

_MATCHING_FIELDS: frozenset[str] = frozenset({
    "company_stage",
    "incorporation_country",
    "incorporation_state",
    "industry",
    "team_size",
    "has_technical_cofounder",
    "funding_raised_usd_cents",
    "funding_target_usd_cents",
    "company_name",
})

# Maps eligibility rule keys → profile fields that produce insufficient_profile_data
ELIGIBILITY_FIELD_MAP: dict[str, list[str]] = {
    "required_stage": ["company_stage"],
    "required_location": ["incorporation_country"],
    "required_industry": ["industry"],
    "min_funding_target_usd": ["funding_target_usd_cents"],
    "min_team_size": ["team_size"],
    "requires_technical_cofounder": ["has_technical_cofounder"],
    "requires_incorporation": ["incorporation_country"],
}


def fields_blocked_by_match_context(match_context: MatchResponse) -> frozenset[str]:
    """Return profile fields that caused insufficient_profile_data hard-fails."""
    fields: set[str] = set()
    for result in match_context.results:
        for fail in result.hard_fails:
            if fail.code == "insufficient_profile_data":
                for f in ELIGIBILITY_FIELD_MAP.get(fail.rule, []):
                    fields.add(f)
    return frozenset(fields)


def relevance_for_intent(
    field: str,
    intent: IntentLabel,
    entities: ExtractedEntities,
    match_context: MatchResponse | None,
) -> float:
    """Return 0.0–1.0 relevance for this field given intent and optional match context."""
    base = _base_relevance(field, intent, entities)

    bonus = 0.0
    if match_context is not None:
        blocked = fields_blocked_by_match_context(match_context)
        if field in blocked:
            bonus = 0.3

    return min(1.0, base + bonus)


def _base_relevance(field: str, intent: IntentLabel, entities: ExtractedEntities) -> float:
    if intent in ("greet", "smalltalk", "profile_query", "out_of_scope", "unknown"):
        return 0.0

    if intent == "match_request":
        if field == "one_liner":
            return 0.2
        if field == "founder_name":
            return 0.1
        return 1.0

    if intent == "deep_dive":
        if not entities.grant_refs:
            return 0.2
        if field in ("one_liner", "founder_name"):
            return 0.2
        return 0.7

    if intent == "profile_update":
        return 1.0

    if intent == "discover":
        if field in _MATCHING_FIELDS:
            return 0.6
        return 0.2

    if intent == "lifecycle_action":
        if entities.action == "track":
            if field in _MATCHING_FIELDS:
                return 0.7
            return 0.0
        return 0.0

    return 0.0
