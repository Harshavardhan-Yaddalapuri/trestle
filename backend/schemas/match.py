from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.schemas.grant import GrantSummary


class MatchRequest(BaseModel):
    stage: str | None = None
    industry: list[str] | None = None
    location: str | None = None
    limit: int = Field(default=20, ge=1, le=50)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    include_ineligible: bool = False
    include_dismissed: bool = False


class MatchProfile(BaseModel):
    founder_name: str | None = None
    company_name: str | None = None
    company_stage: str | None = None
    industry: list[str] | None = None
    location: str | None = None
    one_liner: str | None = None
    # Match-evaluation fields (from profile, no request overrides)
    team_size: int | None = None
    has_technical_cofounder: bool | None = None
    funding_raised_usd_cents: int | None = None
    funding_target_usd_cents: int | None = None
    incorporated: bool | None = None
    incorporation_country: str | None = None
    incorporation_state: str | None = None
    regulatory_status: dict[str, Any] = Field(default_factory=dict)


class RuleFailure(BaseModel):
    rule: str
    code: str
    detail: str


class MatchResult(BaseModel):
    grant: GrantSummary
    score: float
    tier: Literal["strong", "moderate", "weak", "ineligible"]
    matched_on: list[str]
    missing_or_mismatched: list[str]
    hard_fails: list[RuleFailure]
    explanation: str
    tracked: bool = False
    dismissed: bool = False


class MatchResponse(BaseModel):
    match_profile: MatchProfile
    results: list[MatchResult]
    total_evaluated: int
    total_returned: int


def score_to_tier(
    score: float, has_hard_fail: bool
) -> Literal["strong", "moderate", "weak", "ineligible"]:
    if has_hard_fail or score < 0.2:
        return "ineligible"
    if score >= 0.7:
        return "strong"
    if score >= 0.4:
        return "moderate"
    return "weak"
