from __future__ import annotations

from backend.schemas.match import MatchProfile
from backend.services.eligibility.interpreter import RuleResult, register

# EU member states, ISO-3166 alpha-2. Snapshot as of 2024.
EU_COUNTRIES: frozenset[str] = frozenset(
    {
        "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI",
        "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT",
        "NL", "PL", "PT", "RO", "SE", "SI", "SK",
    }
)


def _matches_entry(entry: str, profile: MatchProfile) -> bool:
    """Return True if the profile satisfies a single location entry.

    Hierarchy:
      - "global"  → always matches
      - "EU"      → profile.incorporation_country in EU_COUNTRIES
      - "US-CA"   → incorporation_country="US" AND incorporation_state="CA"
      - "US"      → incorporation_country="US"
    Fallback when incorporation_country is null: case-insensitive substring of profile.location.
    """
    if entry == "global":
        return True

    if profile.incorporation_country is not None:
        if entry == "EU":
            return profile.incorporation_country in EU_COUNTRIES
        if "-" in entry:
            country, state = entry.split("-", 1)
            return (
                profile.incorporation_country == country
                and profile.incorporation_state == state
            )
        return profile.incorporation_country == entry

    # Fallback: free-text location substring match.
    if profile.location:
        return entry.lower() in profile.location.lower()
    return False


@register("required_location")
def _required_location(value: list[str], profile: MatchProfile) -> RuleResult:
    if profile.incorporation_country is None and not profile.location:
        return RuleResult(
            False,
            "insufficient_profile_data",
            "Grant has location requirements; profile has no location data.",
        )
    if any(_matches_entry(e, profile) for e in value):
        return RuleResult(True)
    return RuleResult(
        False,
        "location_not_in_required",
        f"Grant requires location in {value}; profile location does not match.",
    )


@register("excluded_location")
def _excluded_location(value: list[str], profile: MatchProfile) -> RuleResult:
    # Negative check: unknown location cannot be excluded — pass.
    if profile.incorporation_country is None and not profile.location:
        return RuleResult(True)
    if any(_matches_entry(e, profile) for e in value):
        return RuleResult(
            False,
            "location_excluded",
            f"Profile location is excluded by this grant (excluded: {value}).",
        )
    return RuleResult(True)
