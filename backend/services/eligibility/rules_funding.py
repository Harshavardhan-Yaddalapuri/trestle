from __future__ import annotations

from backend.schemas.match import MatchProfile
from backend.services.eligibility.interpreter import RuleResult, register


@register("max_funding_raised_usd")
def _max_funding_raised_usd(value: int, profile: MatchProfile) -> RuleResult:
    """Passes on null funding_raised — absence is interpreted as approximately zero.

    YAML stores USD for human readability; profile stores cents. We convert here.
    """
    if profile.funding_raised_usd_cents is None:
        return RuleResult(True)
    raised_usd = profile.funding_raised_usd_cents // 100
    if raised_usd > value:
        return RuleResult(
            False,
            "above_threshold",
            f"Grant requires <=${value:,} raised; profile shows ${raised_usd:,}.",
        )
    return RuleResult(True)


@register("min_funding_target_usd")
def _min_funding_target_usd(value: int, profile: MatchProfile) -> RuleResult:
    """YAML stores USD; profile stores cents. We convert here."""
    if profile.funding_target_usd_cents is None:
        return RuleResult(
            False,
            "insufficient_profile_data",
            f"Grant requires funding target ≥${value:,}; profile has no target set.",
        )
    target_usd = profile.funding_target_usd_cents // 100
    if target_usd < value:
        return RuleResult(
            False,
            "below_threshold",
            f"Grant requires funding target ≥${value:,}; profile target is ${target_usd:,}.",
        )
    return RuleResult(True)
