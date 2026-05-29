from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from backend.schemas.match import MatchProfile
from backend.services.matching import evaluate_grant, jaccard, resolve_match_profile


# ── helpers ───────────────────────────────────────────────────────────────────


def _grant(**kwargs) -> SimpleNamespace:
    defaults = dict(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        source_id="test-grant",
        name="Test Grant",
        type="grant",
        provider_name="Test Provider",
        deadline=None,
        rolling=False,
        amount_min=None,
        amount_max=None,
        stage=None,
        industry=None,
        location=None,
        eligibility={},
        status="active",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _full_profile(**kwargs) -> MatchProfile:
    base = dict(
        founder_name="Alice",
        company_name="TestCo",
        company_stage="seed",
        industry=["fintech", "b2b"],
        location="US",
        one_liner="Making fintech better",
        incorporation_country="US",
        incorporated=True,
        team_size=3,
        has_technical_cofounder=True,
        funding_raised_usd_cents=50000000,  # $500k
    )
    base.update(kwargs)
    return MatchProfile(**base)


# ── 1. full match ─────────────────────────────────────────────────────────────


def test_full_match_strong():
    # Grant industry matches profile exactly (jaccard=1.0) for maximum score.
    grant = _grant(
        stage=["seed"],
        industry=["fintech", "b2b"],
        location=["US"],
        eligibility={},
    )
    result = evaluate_grant(_full_profile(), grant)
    assert result.score >= 0.85
    assert result.tier == "strong"
    assert "stage" in result.matched_on
    assert "industry" in result.matched_on
    assert "location" in result.matched_on
    assert result.hard_fails == []


# ── 2. required_stage hard fail ───────────────────────────────────────────────


def test_required_stage_hard_fail():
    grant = _grant(
        stage=["pre_seed"],
        eligibility={"required_stage": ["pre_seed"]},
    )
    result = evaluate_grant(_full_profile(company_stage="seed"), grant)
    assert result.score == 0.0
    assert result.tier == "ineligible"
    assert len(result.hard_fails) == 1
    f = result.hard_fails[0]
    assert f.rule == "required_stage"
    assert f.code == "stage_not_in_required"
    assert "pre_seed" in f.detail


# ── 3. partial match → moderate or weak ──────────────────────────────────────


def test_partial_match_moderate():
    # Industry matches, stage mismatch, global location
    grant = _grant(
        stage=["pre_seed"],
        industry=["fintech"],
        location=["global"],
        eligibility={},
    )
    result = evaluate_grant(_full_profile(), grant)
    assert result.tier in ("moderate", "weak")
    assert "industry" in result.matched_on
    assert "stage" in result.missing_or_mismatched
    assert result.hard_fails == []


# ── 4. jaccard helper ─────────────────────────────────────────────────────────


def test_jaccard_empty_empty():
    assert jaccard(set(), set()) == 0.0


def test_jaccard_identical():
    assert jaccard({"a", "b"}, {"a", "b"}) == 1.0


def test_jaccard_partial():
    result = jaccard({"a", "b"}, {"a", "c"})
    # intersection=1, union=3 → 1/3
    assert abs(result - 1 / 3) < 1e-9


def test_jaccard_no_overlap():
    assert jaccard({"a"}, {"b"}) == 0.0


# ── 5. empty eligibility {} ───────────────────────────────────────────────────


def test_empty_eligibility_no_hard_fails():
    grant = _grant(eligibility={})
    result = evaluate_grant(_full_profile(), grant)
    assert result.hard_fails == []
    assert result.score > 0.0


# ── 6. unknown eligibility key ignored ───────────────────────────────────────


def test_unknown_eligibility_key_ignored():
    # structlog uses PrintLoggerFactory so caplog doesn't capture it;
    # we verify functional behavior: unknown keys are ignored, no crash.
    grant = _grant(eligibility={"required_phd": True, "max_team_size": 5})
    result = evaluate_grant(_full_profile(), grant)
    assert result.tier != "ineligible"
    assert result.hard_fails == []
    assert result.score > 0.0


# ── 7. stage='any' matches any profile stage ─────────────────────────────────


def test_stage_any_matches_any_stage():
    grant = _grant(stage=["any"], eligibility={})
    for stage in ("idea", "pre_seed", "seed", "series_a", "series_b_plus", "other"):
        result = evaluate_grant(_full_profile(company_stage=stage), grant)
        assert "stage" in result.matched_on, f"stage={stage} should match 'any'"


# ── 12. multi-rule grant → all failures in hard_fails ────────────────────────


def test_multi_rule_hard_fail_all_returned():
    grant = _grant(
        eligibility={
            "required_location": ["US"],
            "requires_incorporation": True,
        }
    )
    # Profile is in GB and not incorporated — both rules fail.
    profile = _full_profile(incorporation_country="GB", incorporated=False)
    result = evaluate_grant(profile, grant)
    assert result.tier == "ineligible"
    assert result.score == 0.0
    rules = {f.rule for f in result.hard_fails}
    assert "required_location" in rules
    assert "requires_incorporation" in rules
    assert len(result.hard_fails) == 2
    # Explanation uses first failure's detail verbatim.
    assert "Not eligible" in result.explanation
