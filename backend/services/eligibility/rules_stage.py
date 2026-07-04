from __future__ import annotations

from backend.schemas.match import MatchProfile
from backend.services.eligibility.interpreter import RuleResult, register


@register("required_stage")
def _required_stage(value: list[str], profile: MatchProfile) -> RuleResult:
    if profile.company_stage is None:
        return RuleResult(
            False,
            "insufficient_profile_data",
            "Grant requires a specific stage; profile has no company_stage set.",
        )
    if profile.company_stage not in value:
        return RuleResult(
            False,
            "stage_not_in_required",
            f"Grant requires stage {value}; profile is {profile.company_stage!r}.",
        )
    return RuleResult(True)


@register("excluded_stage")
def _excluded_stage(value: list[str], profile: MatchProfile) -> RuleResult:
    # Negative check: unknown stage cannot be excluded — pass.
    if profile.company_stage is None:
        return RuleResult(True)
    if profile.company_stage in value:
        return RuleResult(
            False,
            "stage_excluded",
            f"Stage {profile.company_stage!r} is excluded by this grant.",
        )
    return RuleResult(True)
