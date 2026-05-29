from __future__ import annotations

import pytest

from backend.schemas.match import MatchProfile
from backend.services.eligibility import evaluate_eligibility


# ── helpers ───────────────────────────────────────────────────────────────────


def _profile(**kwargs) -> MatchProfile:
    return MatchProfile(**kwargs)


def _eval(eligibility: dict, **profile_kwargs):
    return evaluate_eligibility(eligibility, _profile(**profile_kwargs))


# ── 1. required_stage ─────────────────────────────────────────────────────────


def test_required_stage_pass():
    result = _eval({"required_stage": ["seed", "pre_seed"]}, company_stage="seed")
    assert result.passed


def test_required_stage_fail():
    result = _eval({"required_stage": ["pre_seed"]}, company_stage="seed")
    assert not result.passed
    assert len(result.hard_fails) == 1
    f = result.hard_fails[0]
    assert f.rule == "required_stage"
    assert f.code == "stage_not_in_required"
    assert "pre_seed" in f.detail


def test_required_stage_missing_profile_field():
    result = _eval({"required_stage": ["seed"]}, company_stage=None)
    assert not result.passed
    assert result.hard_fails[0].code == "insufficient_profile_data"


# ── 2. required_location — country / state / EU ───────────────────────────────


def test_required_location_country_pass():
    result = _eval({"required_location": ["US"]}, incorporation_country="US")
    assert result.passed


def test_required_location_country_fail():
    result = _eval({"required_location": ["US"]}, incorporation_country="GB")
    assert not result.passed
    assert result.hard_fails[0].rule == "required_location"
    assert result.hard_fails[0].code == "location_not_in_required"


def test_required_location_state_match():
    result = _eval(
        {"required_location": ["US-CA"]},
        incorporation_country="US",
        incorporation_state="CA",
    )
    assert result.passed


def test_required_location_state_mismatch():
    result = _eval(
        {"required_location": ["US-CA"]},
        incorporation_country="US",
        incorporation_state="TX",
    )
    assert not result.passed


def test_required_location_eu_pass():
    result = _eval({"required_location": ["EU"]}, incorporation_country="DE")
    assert result.passed


def test_required_location_eu_fail():
    result = _eval({"required_location": ["EU"]}, incorporation_country="GB")
    assert not result.passed


def test_required_location_global_always_passes():
    result = _eval({"required_location": ["global"]}, incorporation_country="JP")
    assert result.passed


# ── 3. required_location — fallback to profile.location string ────────────────


def test_required_location_fallback_pass():
    # No incorporation_country — fall back to profile.location substring match.
    result = _eval({"required_location": ["US"]}, incorporation_country=None, location="US")
    assert result.passed


def test_required_location_fallback_substring():
    # Entry "US" (lowercase "us") is a substring of "New York, US".
    result = _eval(
        {"required_location": ["US"]},
        incorporation_country=None,
        location="New York, US",
    )
    assert result.passed


def test_required_location_fallback_fail():
    result = _eval(
        {"required_location": ["US"]},
        incorporation_country=None,
        location="Canada",
    )
    assert not result.passed


def test_required_location_no_data_insufficient():
    result = _eval(
        {"required_location": ["US"]},
        incorporation_country=None,
        location=None,
    )
    assert not result.passed
    assert result.hard_fails[0].code == "insufficient_profile_data"


# ── 4. max_funding_raised_usd ─────────────────────────────────────────────────


def test_max_funding_raised_pass():
    result = _eval({"max_funding_raised_usd": 2000000}, funding_raised_usd_cents=50000000)
    assert result.passed  # $500k < $2M


def test_max_funding_raised_fail():
    result = _eval({"max_funding_raised_usd": 2000000}, funding_raised_usd_cents=300000000)
    assert not result.passed  # $3M > $2M
    assert result.hard_fails[0].rule == "max_funding_raised_usd"
    assert result.hard_fails[0].code == "above_threshold"
    assert "$3,000,000" in result.hard_fails[0].detail


def test_max_funding_raised_null_passes():
    # Missing funding_raised → pass (assumed ~zero).
    result = _eval({"max_funding_raised_usd": 2000000}, funding_raised_usd_cents=None)
    assert result.passed


# ── 5. min_team_size null profile field ───────────────────────────────────────


def test_min_team_size_null_fails():
    result = _eval({"min_team_size": 5}, team_size=None)
    assert not result.passed
    assert result.hard_fails[0].code == "insufficient_profile_data"


def test_min_team_size_pass():
    result = _eval({"min_team_size": 5}, team_size=6)
    assert result.passed


def test_min_team_size_fail():
    result = _eval({"min_team_size": 5}, team_size=2)
    assert not result.passed
    assert "5+" in result.hard_fails[0].detail


# ── 6. requires_technical_cofounder ──────────────────────────────────────────


def test_requires_technical_cofounder_null_fails():
    result = _eval({"requires_technical_cofounder": True}, has_technical_cofounder=None)
    assert not result.passed
    assert result.hard_fails[0].code == "insufficient_profile_data"


def test_requires_technical_cofounder_false_fails():
    result = _eval({"requires_technical_cofounder": True}, has_technical_cofounder=False)
    assert not result.passed
    assert result.hard_fails[0].code == "technical_cofounder_required"


def test_requires_technical_cofounder_true_passes():
    result = _eval({"requires_technical_cofounder": True}, has_technical_cofounder=True)
    assert result.passed


def test_requires_technical_cofounder_rule_false_always_passes():
    result = _eval({"requires_technical_cofounder": False}, has_technical_cofounder=None)
    assert result.passed


# ── 7. requires (regulatory) ──────────────────────────────────────────────────


def test_requires_regulatory_pass():
    result = _eval(
        {"requires": ["hipaa_ready"]},
        regulatory_status={"hipaa_ready": True},
    )
    assert result.passed


def test_requires_regulatory_missing_key_fails():
    result = _eval({"requires": ["hipaa_ready"]}, regulatory_status={})
    assert not result.passed
    assert result.hard_fails[0].code == "required_regulatory_signal_missing"
    assert "hipaa_ready" in result.hard_fails[0].detail


def test_requires_regulatory_falsy_value_fails():
    result = _eval(
        {"requires": ["hipaa_ready"]},
        regulatory_status={"hipaa_ready": False},
    )
    assert not result.passed
    assert result.hard_fails[0].code == "required_regulatory_signal_missing"


# ── 8. required_industry ──────────────────────────────────────────────────────


def test_required_industry_overlap_passes():
    result = _eval(
        {"required_industry": ["ai", "open_source", "ml"]},
        industry=["ai", "fintech"],
    )
    assert result.passed


def test_required_industry_no_overlap_fails():
    result = _eval(
        {"required_industry": ["ai", "open_source", "ml"]},
        industry=["hardware", "climate"],
    )
    assert not result.passed
    assert result.hard_fails[0].rule == "required_industry"
    assert result.hard_fails[0].code == "industry_not_in_required"


def test_required_industry_null_fails():
    result = _eval({"required_industry": ["ai"]}, industry=None)
    assert not result.passed
    assert result.hard_fails[0].code == "insufficient_profile_data"


# ── 9. unknown rule key — no crash ────────────────────────────────────────────


def test_unknown_rule_key_ignored(capfd):
    result = _eval(
        {"some_future_rule": "some_value", "another_unknown": 42},
        company_stage="seed",
    )
    assert result.passed
    assert result.hard_fails == []


# ── 10. empty eligibility {} → passes ────────────────────────────────────────


def test_empty_eligibility_passes():
    result = _eval({})
    assert result.passed
    assert result.hard_fails == []


# ── 11. multiple failing rules — all returned (no short-circuit) ──────────────


def test_multiple_failures_all_returned():
    result = _eval(
        {
            "required_stage": ["pre_seed"],
            "required_location": ["US"],
            "min_team_size": 5,
        },
        company_stage="seed",
        incorporation_country="GB",
        team_size=2,
    )
    assert not result.passed
    rules = {f.rule for f in result.hard_fails}
    assert "required_stage" in rules
    assert "required_location" in rules
    assert "min_team_size" in rules
    assert len(result.hard_fails) == 3
