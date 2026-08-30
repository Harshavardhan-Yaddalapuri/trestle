from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from backend.db.models.event import Event
from backend.db.models.profile import Profile
from backend.schemas.event import EventMatchProfile, EventMatchRequest, EventMatchResult, EventSummary
from backend.services.events.location_normalization import event_is_in_country, event_is_in_state
from backend.services.matching import jaccard

_WEIGHTS = {
    "outcome": 0.35,
    "industry": 0.2,
    "stage": 0.15,
    "distance": 0.15,
    "host_quality": 0.15,
}

_GOAL_TO_BENEFIT: dict[str, tuple[str, ...]] = {
    "investor_access": ("raise", "fund", "investor", "vc", "demo day", "pitch"),
    "hiring": ("hire", "talent", "recruit", "engineer"),
    "customer_discovery": ("customer", "gtm", "sales", "pilot"),
    "networking": ("network", "community", "connections", "meet"),
    "partnerships": ("partner", "partnership", "corporate"),
    "lab_access": ("lab", "wet lab", "research"),
}


def _parse_goals(goals: list[str] | None, profile: Profile | None) -> list[str]:
    if goals:
        return [g.strip() for g in goals if g.strip()]
    if not profile or not profile.goals:
        return []
    return [chunk.strip() for chunk in profile.goals.split(",") if chunk.strip()]


def resolve_event_profile(profile: Profile | None, overrides: EventMatchRequest) -> EventMatchProfile:
    return EventMatchProfile(
        company_stage=overrides.stage if overrides.stage is not None else (profile.company_stage if profile else None),
        industry=overrides.industry if overrides.industry is not None else (profile.industry if profile else None),
        location=overrides.location if overrides.location is not None else (profile.location if profile else None),
        incorporation_country=profile.incorporation_country if profile else None,
        incorporation_state=profile.incorporation_state if profile else None,
        goals=_parse_goals(overrides.goals, profile),
    )


def _goal_benefit_tags(profile: EventMatchProfile) -> set[str]:
    text = " ".join(profile.goals).lower()
    tags: set[str] = set()
    for benefit, keywords in _GOAL_TO_BENEFIT.items():
        if any(keyword in text for keyword in keywords):
            tags.add(benefit)
    return tags


def _score_outcome(profile: EventMatchProfile, event: Event) -> tuple[float, bool]:
    event_benefits = set(event.benefit_tags or [])
    goal_benefits = _goal_benefit_tags(profile)
    if not goal_benefits:
        return 0.5, False
    if not event_benefits:
        return 0.2, False
    score = jaccard(goal_benefits, event_benefits)
    return score, score > 0


def _score_industry(profile: EventMatchProfile, event: Event) -> tuple[float, bool]:
    if not profile.industry:
        return 0.5, False
    event_industry = set(event.industry_tags or [])
    if not event_industry:
        return 0.3, False
    score = jaccard(set(profile.industry), event_industry)
    return score, score > 0


def _score_stage(profile: EventMatchProfile, event: Event) -> tuple[float, bool]:
    if not profile.company_stage:
        return 0.5, False
    tags = set(event.stage_tags or [])
    if not tags:
        return 0.4, False
    if "any" in tags or profile.company_stage in tags:
        return 1.0, True
    return 0.0, False


def _score_distance(profile: EventMatchProfile, event: Event, include_virtual: bool) -> tuple[float, bool]:
    if event.is_virtual:
        return (1.0 if include_virtual else 0.0), include_virtual
    if not profile.location:
        return 0.4, False
    location_blob = " ".join(
        v.lower() for v in [event.location_text, event.city, event.region, event.country] if v
    )
    # Profiles commonly use "City, ST" while sources separately store city and
    # region. Match a meaningful location part rather than the full display text.
    location_terms = [
        term.strip().lower()
        for term in profile.location.split(",")
        if len(term.strip()) > 1
    ]
    if any(term in location_blob for term in location_terms):
        return 1.0, True
    if event_is_in_state(
        event,
        profile.incorporation_state,
        profile.incorporation_country,
    ) or event_is_in_country(event, profile.incorporation_country):
        return 1.0, True
    return 0.15, False


@dataclass
class EventScore:
    score: float
    matched_on: list[str]
    missing_or_mismatched: list[str]


def _score_event(profile: EventMatchProfile, event: Event, include_virtual: bool) -> EventScore:
    outcome_score, outcome_match = _score_outcome(profile, event)
    industry_score, industry_match = _score_industry(profile, event)
    stage_score, stage_match = _score_stage(profile, event)
    distance_score, distance_match = _score_distance(profile, event, include_virtual)
    host_quality = min(max(event.host_quality_score or 0.5, 0.0), 1.0)

    score = (
        _WEIGHTS["outcome"] * outcome_score
        + _WEIGHTS["industry"] * industry_score
        + _WEIGHTS["stage"] * stage_score
        + _WEIGHTS["distance"] * distance_score
        + _WEIGHTS["host_quality"] * host_quality
    )
    score = round(score, 4)

    matched_on: list[str] = []
    missing_or_mismatched: list[str] = []
    for key, matched in (
        ("outcome", outcome_match),
        ("industry", industry_match),
        ("stage", stage_match),
        ("distance", distance_match),
    ):
        if matched:
            matched_on.append(key)
        else:
            missing_or_mismatched.append(key)

    return EventScore(score=score, matched_on=matched_on, missing_or_mismatched=missing_or_mismatched)


def evaluate_event(
    profile: EventMatchProfile,
    event: Event,
    *,
    include_virtual: bool,
) -> EventMatchResult:
    score_details = _score_event(profile, event, include_virtual)
    matched = ", ".join(score_details.matched_on) if score_details.matched_on else "limited dimensions"
    explanation = f"Event fit based on {matched}."
    return EventMatchResult(
        event=EventSummary.model_validate(event),
        score=score_details.score,
        matched_on=score_details.matched_on,
        missing_or_mismatched=score_details.missing_or_mismatched,
        explanation=explanation,
    )


def is_event_active(event: Event, include_expired: bool) -> bool:
    if include_expired:
        return True
    now = datetime.now(UTC)
    end = event.ends_at or event.starts_at
    return event.status == "active" and end >= now

