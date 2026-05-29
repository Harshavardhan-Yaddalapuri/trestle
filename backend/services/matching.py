from __future__ import annotations

from backend.core.logging import get_logger
from backend.db.models.grant import Grant
from backend.db.models.profile import Profile
from backend.schemas.grant import GrantSummary
from backend.schemas.match import MatchProfile, MatchRequest, MatchResult, RuleFailure, score_to_tier
from backend.services.eligibility import evaluate_eligibility

logger = get_logger(__name__)

_WEIGHTS = {
    "stage": 0.30,
    "industry": 0.30,
    "location": 0.20,
    "funding": 0.10,
    "completeness": 0.10,
}

_COMPLETENESS_FIELDS = (
    "founder_name",
    "company_name",
    "company_stage",
    "industry",
    "location",
    "one_liner",
)


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def resolve_match_profile(
    profile: Profile | None, overrides: MatchRequest
) -> MatchProfile:
    return MatchProfile(
        founder_name=profile.founder_name if profile else None,
        company_name=profile.company_name if profile else None,
        company_stage=(
            overrides.stage
            if overrides.stage is not None
            else (profile.company_stage if profile else None)
        ),
        industry=(
            overrides.industry
            if overrides.industry is not None
            else (profile.industry if profile else None)
        ),
        location=(
            overrides.location
            if overrides.location is not None
            else (profile.location if profile else None)
        ),
        one_liner=profile.one_liner if profile else None,
        team_size=profile.team_size if profile else None,
        has_technical_cofounder=profile.has_technical_cofounder if profile else None,
        funding_raised_usd_cents=profile.funding_raised_usd_cents if profile else None,
        funding_target_usd_cents=profile.funding_target_usd_cents if profile else None,
        incorporated=profile.incorporated if profile else None,
        incorporation_country=profile.incorporation_country if profile else None,
        incorporation_state=profile.incorporation_state if profile else None,
        regulatory_status=profile.regulatory_status if profile else {},
    )


def _score_stage(profile: MatchProfile, grant: Grant) -> tuple[float, bool, bool]:
    """Returns (score, matched, mismatched)."""
    if not grant.stage:
        return 0.5, False, False
    if "any" in grant.stage or (
        profile.company_stage and profile.company_stage in grant.stage
    ):
        return 1.0, True, False
    return 0.0, False, True


def _score_industry(profile: MatchProfile, grant: Grant) -> tuple[float, bool, bool]:
    if not grant.industry:
        return 0.5, False, False
    if not profile.industry:
        return 0.5, False, False
    j = jaccard(set(profile.industry), set(grant.industry))
    if j > 0:
        return j, True, False
    return 0.0, False, True


def _score_location(profile: MatchProfile, grant: Grant) -> tuple[float, bool, bool]:
    if not grant.location:
        return 0.5, False, False
    if "global" in grant.location:
        return 0.8, True, False
    if profile.location and profile.location in grant.location:
        return 1.0, True, False
    return 0.0, False, True


def _score_completeness(profile: MatchProfile) -> float:
    filled = sum(
        1
        for f in _COMPLETENESS_FIELDS
        if getattr(profile, f, None) not in (None, [], "")
    )
    return filled / len(_COMPLETENESS_FIELDS)


def _build_explanation(
    tier: str,
    matched_on: list[str],
    missing_or_mismatched: list[str],
    hard_fails: list[RuleFailure],
) -> str:
    if tier == "ineligible":
        if hard_fails:
            return f"Not eligible — {hard_fails[0].detail}"[:200]
        return "Not eligible — does not meet grant requirements."

    matched_str = ", ".join(matched_on) if matched_on else "no dimensions"

    if tier == "strong":
        msg = f"Strong fit — matches {matched_str}."
    elif tier == "moderate":
        if missing_or_mismatched:
            mismatch_str = ", ".join(missing_or_mismatched)
            msg = f"Moderate fit — {matched_str} align, but {mismatch_str} may not match."
        else:
            msg = f"Moderate fit — {matched_str} align."
    else:
        if missing_or_mismatched:
            mismatch_str = ", ".join(missing_or_mismatched)
            msg = f"Weak fit — {matched_str} overlap. {mismatch_str} don't match."
        else:
            msg = "Weak fit — limited alignment with grant requirements."

    return msg[:200]


def evaluate_grant(profile: MatchProfile, grant: Grant) -> MatchResult:
    eligibility = grant.eligibility or {}

    elig_result = evaluate_eligibility(eligibility, profile)
    if not elig_result.passed:
        return MatchResult(
            grant=GrantSummary.model_validate(grant),
            score=0.0,
            tier="ineligible",
            matched_on=[],
            missing_or_mismatched=[],
            hard_fails=elig_result.hard_fails,
            explanation=_build_explanation("ineligible", [], [], elig_result.hard_fails),
        )

    stage_score, stage_matched, stage_mismatch = _score_stage(profile, grant)
    industry_score, industry_matched, industry_mismatch = _score_industry(profile, grant)
    location_score, location_matched, location_mismatch = _score_location(profile, grant)
    completeness_score = _score_completeness(profile)

    total = (
        stage_score * _WEIGHTS["stage"]
        + industry_score * _WEIGHTS["industry"]
        + location_score * _WEIGHTS["location"]
        + 0.5 * _WEIGHTS["funding"]
        + completeness_score * _WEIGHTS["completeness"]
    )
    score = round(max(0.0, min(1.0, total)), 4)

    matched_on: list[str] = []
    missing_or_mismatched: list[str] = []

    if stage_matched:
        matched_on.append("stage")
    elif stage_mismatch:
        missing_or_mismatched.append("stage")

    if industry_matched:
        matched_on.append("industry")
    elif industry_mismatch:
        missing_or_mismatched.append("industry")

    if location_matched:
        matched_on.append("location")
    elif location_mismatch:
        missing_or_mismatched.append("location")

    tier = score_to_tier(score, False)
    explanation = _build_explanation(tier, matched_on, missing_or_mismatched, [])

    return MatchResult(
        grant=GrantSummary.model_validate(grant),
        score=score,
        tier=tier,
        matched_on=matched_on,
        missing_or_mismatched=missing_or_mismatched,
        hard_fails=[],
        explanation=explanation,
    )
