"""Tests for the question engine — pure service, no HTTP, no DB."""
from __future__ import annotations

import uuid

import pytest

from backend.schemas.grant import GrantSummary
from backend.schemas.intent import ExtractedEntities, IntentResult
from backend.schemas.match import MatchProfile, MatchResponse, MatchResult, RuleFailure
from backend.schemas.question import QuestionEngineConfig
from backend.services.question_engine import GAP_DEFINITIONS, analyze_gaps, suggest_question


# ── Helpers ───────────────────────────────────────────────────────────────────


def _intent(label: str, grant_refs: list[str] | None = None, action: str | None = None) -> IntentResult:
    return IntentResult(
        intent=label,
        confidence=0.9,
        entities=ExtractedEntities(
            grant_refs=grant_refs or [],
            action=action,
        ),
        classified_by="regex",
    )


def _dummy_grant(location: list[str] | None = None) -> GrantSummary:
    return GrantSummary(
        id=uuid.uuid4(),
        source_id="test-grant",
        name="Test Grant",
        type="grant",
        provider_name="Test Provider",
        deadline=None,
        rolling=True,
        amount_min=None,
        amount_max=None,
        stage=None,
        industry=None,
        location=location,
        status="active",
    )


def _match_context_with_fail(rule: str, detail: str) -> MatchResponse:
    """Build a minimal MatchResponse with a single insufficient_profile_data hard fail."""
    result = MatchResult(
        grant=_dummy_grant(),
        score=0.0,
        tier="ineligible",
        matched_on=[],
        missing_or_mismatched=[],
        hard_fails=[
            RuleFailure(
                rule=rule,
                code="insufficient_profile_data",
                detail=detail,
            )
        ],
        explanation="Not eligible — insufficient profile data.",
    )
    return MatchResponse(
        match_profile=MatchProfile(),
        results=[result],
        total_evaluated=1,
        total_returned=1,
    )


def _complete_profile(**overrides) -> MatchProfile:
    """Return a fully-populated profile, useful for completeness tests."""
    base = dict(
        company_stage="seed",
        incorporation_country="GB",
        industry=["fintech"],
        company_name="Acme",
        founder_name="Alice",
        team_size=3,
        has_technical_cofounder=True,
        funding_raised_usd_cents=0,
        funding_target_usd_cents=100_000_00,
        one_liner="We make fintech software.",
    )
    base.update(overrides)
    return MatchProfile(**base)


# ── analyze_gaps ──────────────────────────────────────────────────────────────


def test_analyze_gaps_empty_profile_excludes_depends_on_gated():
    """Fully-empty profile: all gaps returned except depends_on-gated incorporation_state."""
    gaps = analyze_gaps(MatchProfile())
    fields = [g.field for g in gaps]
    # 11 entries in GAP_DEFINITIONS; incorporation_state excluded (country not "US")
    assert len(gaps) == 10
    assert "incorporation_state" not in fields


def test_analyze_gaps_full_profile_returns_empty():
    """Fully-populated profile: no gaps."""
    profile = MatchProfile(
        company_stage="seed",
        incorporation_country="US",
        incorporation_state="CA",
        industry=["saas"],
        company_name="Acme",
        founder_name="Alice",
        team_size=3,
        has_technical_cofounder=True,
        funding_raised_usd_cents=0,
        funding_target_usd_cents=500_000_00,
        one_liner="We make things.",
    )
    assert analyze_gaps(profile) == []


def test_analyze_gaps_null_country_excludes_state():
    """incorporation_state is not a gap when incorporation_country is null."""
    # even if state somehow has a value, depends_on is false
    profile = MatchProfile(incorporation_state="CA")
    fields = [g.field for g in analyze_gaps(profile)]
    assert "incorporation_state" not in fields


def test_analyze_gaps_us_country_includes_state_gap():
    """When incorporation_country='US' and state is null, state appears as a gap."""
    profile = MatchProfile(incorporation_country="US")
    fields = [g.field for g in analyze_gaps(profile)]
    assert "incorporation_state" in fields


def test_analyze_gaps_false_bool_not_a_gap():
    """False (has_technical_cofounder) is a valid filled value, not a gap."""
    profile = MatchProfile(has_technical_cofounder=False)
    fields = [g.field for g in analyze_gaps(profile)]
    assert "has_technical_cofounder" not in fields


def test_analyze_gaps_zero_funding_not_a_gap():
    """0 (funding_raised_usd_cents=0) is a valid filled value, not a gap."""
    profile = MatchProfile(funding_raised_usd_cents=0)
    fields = [g.field for g in analyze_gaps(profile)]
    assert "funding_raised_usd_cents" not in fields


# ── suggest_question: intent suppression ─────────────────────────────────────


def test_suggest_greet_returns_none():
    """greet intent: never ask a question."""
    result = suggest_question(MatchProfile(), _intent("greet"))
    assert result is None


def test_suggest_smalltalk_returns_none():
    """smalltalk intent: never ask a question."""
    result = suggest_question(MatchProfile(), _intent("smalltalk"))
    assert result is None


def test_suggest_profile_query_returns_none_even_with_empty_profile():
    """profile_query: user wants to see what's on file, not be asked."""
    result = suggest_question(MatchProfile(), _intent("profile_query"))
    assert result is None


# ── suggest_question: match_request path ─────────────────────────────────────


def test_suggest_match_request_empty_profile_asks_company_stage():
    """match_request + empty profile: highest-weight gap is company_stage."""
    result = suggest_question(MatchProfile(), _intent("match_request"))
    assert result is not None
    assert result.field == "company_stage"
    assert result.intent_context == "match_request"
    assert result.priority_score == pytest.approx(0.95)
    # Should have stage response options
    assert len(result.response_options) > 0


def test_suggest_match_request_stage_filled_asks_incorporation_country():
    """After filling stage, incorporation_country is the next highest-weight gap."""
    profile = MatchProfile(company_stage="seed")
    result = suggest_question(profile, _intent("match_request"))
    assert result is not None
    assert result.field == "incorporation_country"
    assert result.priority_score == pytest.approx(0.85)


def test_suggest_match_request_complete_enough_returns_none():
    """All high-priority fields filled: no question crosses the 0.3 threshold."""
    profile = _complete_profile()
    result = suggest_question(profile, _intent("match_request"))
    assert result is None


# ── suggest_question: deep_dive with grant_ref ────────────────────────────────


def test_suggest_deep_dive_with_grant_ref_asks_incorporation_country():
    """deep_dive + grant_ref → incorporation_country gets relevance boost from match context."""
    profile = MatchProfile(company_stage="seed")  # stage is filled

    intent = _intent("deep_dive", grant_refs=["us-only-grant"])
    context = _match_context_with_fail(
        rule="required_location",
        detail="Grant has location requirements; profile has no location data.",
    )

    result = suggest_question(profile, intent, match_context=context)
    assert result is not None
    assert result.field == "incorporation_country"
    # relevance = min(1.0, 0.7 + 0.3) = 1.0 → priority = 0.85 × 1.0 = 0.85
    assert result.priority_score == pytest.approx(0.85)
    assert "location" in result.reason.lower()


# ── suggest_question: profile_update ─────────────────────────────────────────


def test_suggest_profile_update_empty_profile_asks_first_gap():
    """profile_update + empty profile: asks company_stage (highest base_weight)."""
    result = suggest_question(MatchProfile(), _intent("profile_update"))
    assert result is not None
    assert result.field == "company_stage"


# ── suggest_question: completeness threshold ─────────────────────────────────


def test_suggest_one_liner_alone_below_threshold_for_match_request():
    """Profile missing only one_liner: returns None for match_request (0.3 × 0.2 = 0.06)."""
    profile = _complete_profile(one_liner=None)
    result = suggest_question(profile, _intent("match_request"))
    assert result is None


def test_suggest_one_liner_crosses_threshold_for_profile_update():
    """Profile missing only one_liner: profile_update gives relevance 1.0 → crosses 0.3."""
    profile = _complete_profile(one_liner=None)
    result = suggest_question(profile, _intent("profile_update"))
    assert result is not None
    assert result.field == "one_liner"
    assert result.priority_score == pytest.approx(0.3)


# ── suggest_question: match_context boost ────────────────────────────────────


def test_suggest_match_context_team_size_fail_boosts_priority():
    """match_context with team_size fail: team_size is asked with boosted priority and specific reason."""
    # Fill all higher-weight fields so team_size surfaces
    profile = MatchProfile(
        company_stage="seed",
        incorporation_country="DE",
        industry=["deeptech"],
        company_name="Zeta",
    )
    intent = _intent("discover")
    context = _match_context_with_fail(
        rule="min_team_size",
        detail="Grant requires team of 5+; profile has no team_size set.",
    )

    result = suggest_question(profile, intent, match_context=context)
    assert result is not None
    assert result.field == "team_size"
    # relevance = min(1.0, 0.6 + 0.3) = 0.9 → priority = 0.6 × 0.9 = 0.54
    assert result.priority_score == pytest.approx(0.54)
    assert "team" in result.reason.lower() or "5" in result.reason


# ── suggest_question: response options ───────────────────────────────────────


def test_funding_raised_has_range_options():
    """funding_raised gap should include bucketed range options."""
    profile = MatchProfile(company_stage="seed", incorporation_country="US", industry=["saas"])
    # With high-weight gaps filled, funding_raised_usd_cents surfaces as a gap
    profile_partial = MatchProfile(
        company_stage="seed",
        incorporation_country="GB",
        industry=["saas"],
        company_name="Beta",
        team_size=2,
    )
    result = suggest_question(profile_partial, _intent("match_request"))
    # Whichever field comes up, check that funding_raised has options when it's the answer
    # Force it by eliminating other gaps
    profile_funding_only = MatchProfile(
        company_stage="seed",
        incorporation_country="GB",
        industry=["saas"],
        company_name="Beta",
        founder_name="Bob",
        team_size=2,
        has_technical_cofounder=True,
        funding_target_usd_cents=50_000_00,
        one_liner="We build tools.",
    )
    result = suggest_question(profile_funding_only, _intent("match_request"))
    assert result is not None
    assert result.field == "funding_raised_usd_cents"
    labels = [o.label for o in result.response_options]
    assert "$50k–$250k" in labels  # "$50k–$250k"


# ── suggest_question: custom config threshold ────────────────────────────────


def test_custom_min_priority_raises_threshold():
    """Raising min_priority_to_ask filters out lower-weight questions."""
    profile = MatchProfile(company_stage="seed", incorporation_country="GB", industry=["saas"])
    # With these gaps remaining: team_size (0.6×1.0=0.6), company_name (0.7×1.0=0.7), ...
    # Set threshold to 0.9 — only company_stage would pass, but that's filled
    high_threshold = QuestionEngineConfig(min_priority_to_ask=0.9)
    result = suggest_question(profile, _intent("match_request"), config=high_threshold)
    # industry is filled, incorporation_country filled, company_stage filled
    # Remaining highest: company_name (0.7 × 1.0 = 0.70) < 0.9 → None
    assert result is None
