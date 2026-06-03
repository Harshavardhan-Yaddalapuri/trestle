"""Demo: question engine across 5 (profile, intent) combos.

Run from the repo root:
    python -m backend.scripts.question_demo
"""
from __future__ import annotations

from backend.schemas.intent import ExtractedEntities, IntentResult
from backend.schemas.match import MatchProfile, MatchResponse, MatchResult, RuleFailure
from backend.schemas.grant import GrantSummary
from backend.services.question_engine import suggest_question
import uuid


def _intent(label: str, grant_refs: list[str] | None = None) -> IntentResult:
    return IntentResult(
        intent=label,
        confidence=0.9,
        entities=ExtractedEntities(grant_refs=grant_refs or []),
        classified_by="regex",
    )


def _match_context_with_fail(rule: str, detail: str) -> MatchResponse:
    result = MatchResult(
        grant=GrantSummary(
            id=uuid.uuid4(),
            source_id="demo-grant",
            name="Demo Grant",
            type="grant",
            provider_name="Demo Provider",
            deadline=None,
            rolling=True,
            amount_min=None,
            amount_max=None,
            stage=None,
            industry=None,
            location=None,
            status="active",
        ),
        score=0.0,
        tier="ineligible",
        matched_on=[],
        missing_or_mismatched=[],
        hard_fails=[RuleFailure(rule=rule, code="insufficient_profile_data", detail=detail)],
        explanation="Not eligible — insufficient profile data.",
    )
    return MatchResponse(
        match_profile=MatchProfile(),
        results=[result],
        total_evaluated=1,
        total_returned=1,
    )


SCENARIOS = [
    (
        "1. Empty profile, match_request",
        MatchProfile(),
        _intent("match_request"),
        None,
    ),
    (
        "2. Stage filled, match_request",
        MatchProfile(company_stage="seed"),
        _intent("match_request"),
        None,
    ),
    (
        "3. Greet intent (should suppress all questions)",
        MatchProfile(),
        _intent("greet"),
        None,
    ),
    (
        "4. Deep dive with grant_ref + location fail in match_context",
        MatchProfile(company_stage="pre_seed"),
        _intent("deep_dive", grant_refs=["nsf-sbir"]),
        _match_context_with_fail(
            "required_location",
            "Grant has location requirements; profile has no location data.",
        ),
    ),
    (
        "5. discover intent with team-size fail in match_context",
        MatchProfile(
            company_stage="seed",
            incorporation_country="DE",
            industry=["climate-tech"],
            company_name="GreenCo",
        ),
        _intent("discover"),
        _match_context_with_fail(
            "min_team_size",
            "Grant requires team of 5+; profile has no team_size set.",
        ),
    ),
]


def main() -> None:
    sep = "-" * 60
    for label, profile, intent, ctx in SCENARIOS:
        print(sep)
        print(f"  {label}")
        result = suggest_question(profile, intent, match_context=ctx)
        if result is None:
            print("  -> None (no question to ask)")
        else:
            print(f"  -> field:          {result.field}")
            print(f"     question:       {result.question}")
            print(f"     reason:         {result.reason}")
            print(f"     priority_score: {result.priority_score:.4f}")
            if result.response_options:
                opts = ", ".join(o.label for o in result.response_options[:4])
                suffix = "..." if len(result.response_options) > 4 else ""
                print(f"     options:        {opts}{suffix}")
    print(sep)


if __name__ == "__main__":
    main()
