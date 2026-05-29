from __future__ import annotations

from backend.schemas.match import MatchProfile
from backend.services.eligibility.interpreter import RuleResult, register


@register("min_team_size")
def _min_team_size(value: int, profile: MatchProfile) -> RuleResult:
    if profile.team_size is None:
        return RuleResult(
            False,
            "insufficient_profile_data",
            f"Grant requires team of {value}+; profile has no team_size set.",
        )
    if profile.team_size < value:
        return RuleResult(
            False,
            "below_threshold",
            f"Grant requires team of {value}+; profile shows {profile.team_size}.",
        )
    return RuleResult(True)


@register("max_team_size")
def _max_team_size(value: int, profile: MatchProfile) -> RuleResult:
    """Passes on null team_size — max-bound rule; absence is assumed safe."""
    if profile.team_size is None:
        return RuleResult(True)
    if profile.team_size > value:
        return RuleResult(
            False,
            "above_threshold",
            f"Grant requires team of <={value}; profile shows {profile.team_size}.",
        )
    return RuleResult(True)


@register("requires_technical_cofounder")
def _requires_technical_cofounder(value: bool, profile: MatchProfile) -> RuleResult:
    if not value:
        return RuleResult(True)
    if profile.has_technical_cofounder is None:
        return RuleResult(
            False,
            "insufficient_profile_data",
            "Grant requires a technical co-founder; profile has no has_technical_cofounder set.",
        )
    if not profile.has_technical_cofounder:
        return RuleResult(
            False,
            "technical_cofounder_required",
            "Grant requires a technical co-founder; profile indicates none.",
        )
    return RuleResult(True)


@register("requires_incorporation")
def _requires_incorporation(value: bool, profile: MatchProfile) -> RuleResult:
    # Negative check (value=False): always passes, even when incorporated is null.
    if not value:
        return RuleResult(True)
    if profile.incorporated is None:
        return RuleResult(
            False,
            "insufficient_profile_data",
            "Grant requires incorporation; profile has no incorporated status set.",
        )
    if not profile.incorporated:
        return RuleResult(
            False,
            "incorporation_required",
            "Grant requires incorporation; profile indicates not incorporated.",
        )
    return RuleResult(True)
