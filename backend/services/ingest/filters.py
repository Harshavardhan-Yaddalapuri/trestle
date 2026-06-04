"""Startup-relevance filter for ingested grants.

Conservative exclusions only: filter when we're sure the grant is irrelevant.
Soft signals are left for the eligibility engine.
"""
from __future__ import annotations

from backend.services.ingest.base import IngestedGrant


def startup_relevance_filter(record: IngestedGrant) -> tuple[bool, str | None]:
    """Return (kept, skip_reason). skip_reason is None when kept=True."""
    applicant_types: list = record.eligibility.get("_applicant_types") or []

    # Normalize to lower-case for comparison
    types_lower = [t.lower() for t in applicant_types]

    # Rule 1: individuals-only
    if types_lower and all(t in {"individuals", "individual"} for t in types_lower):
        return False, "individuals-only"

    # Rule 2: nonprofits-only
    _NONPROFIT_ONLY = {"nonprofits", "nonprofit", "501c3", "501(c)(3)"}
    if types_lower and all(t in _NONPROFIT_ONLY for t in types_lower):
        return False, "nonprofits-only"

    # Rule 3: explicitly excluded for startups
    if record.eligibility.get("_excluded_for_startups") is True:
        return False, "explicitly-not-for-startups"

    # Rule 4: below-threshold ($10K = 1_000_000 cents)
    if (
        record.amount_max_usd_cents is not None
        and record.amount_max_usd_cents < 1_000_000
    ):
        return False, "below-threshold"

    # TODO: heuristic keyword check (soft signal — deferred to v2)

    return True, None
