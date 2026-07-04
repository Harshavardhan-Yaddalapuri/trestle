from __future__ import annotations

from backend.schemas.match import MatchProfile
from backend.services.eligibility.interpreter import RuleResult, register


@register("requires")
def _requires(value: list[str], profile: MatchProfile) -> RuleResult:
    """Each entry in `value` must be a truthy key in profile.regulatory_status."""
    regulatory = profile.regulatory_status or {}
    missing = [k for k in value if not regulatory.get(k)]
    if missing:
        keys_str = ", ".join(repr(k) for k in missing)
        return RuleResult(
            False,
            "required_regulatory_signal_missing",
            f"Grant requires {keys_str} in regulatory_status; not present or falsy.",
        )
    return RuleResult(True)
