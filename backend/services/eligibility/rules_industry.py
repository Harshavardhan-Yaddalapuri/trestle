from __future__ import annotations

from backend.schemas.match import MatchProfile
from backend.services.eligibility.interpreter import RuleResult, register


@register("required_industry")
def _required_industry(value: list[str], profile: MatchProfile) -> RuleResult:
    if not profile.industry:
        return RuleResult(
            False,
            "insufficient_profile_data",
            "Grant requires specific industries; profile has no industry set.",
        )
    overlap = set(profile.industry) & set(value)
    if not overlap:
        return RuleResult(
            False,
            "industry_not_in_required",
            (
                f"Grant requires industry in {sorted(value)}; "
                f"profile industries {sorted(profile.industry)} don't overlap."
            ),
        )
    return RuleResult(True)


@register("excluded_industry")
def _excluded_industry(value: list[str], profile: MatchProfile) -> RuleResult:
    # Negative check: unknown industry cannot be excluded — pass.
    if not profile.industry:
        return RuleResult(True)
    overlap = set(profile.industry) & set(value)
    if overlap:
        return RuleResult(
            False,
            "industry_excluded",
            f"Industries {sorted(overlap)} are excluded by this grant.",
        )
    return RuleResult(True)
