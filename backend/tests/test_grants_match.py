from __future__ import annotations

from datetime import datetime, timezone

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.profile import Profile


# ── fixtures ──────────────────────────────────────────────────────────────────

SESSION_A = "match-sess-a"
SESSION_B = "match-sess-b"
SESSION_C = "match-sess-c"
SESSION_D = "match-sess-d"

# Session A: seed-stage AI company in the US — full profile, scores vary across grants.
_PROFILE_A = dict(
    founder_name="Alice",
    company_name="SeedCo",
    company_stage="seed",
    industry=["ai"],
    location="US",
    one_liner="AI for everyone",
    incorporation_country="US",
    incorporated=True,
    team_size=3,
    has_technical_cofounder=True,
    funding_raised_usd_cents=50000000,  # $500k
)

# Session B: pre_seed hardware startup — for cross-session isolation test.
_PROFILE_B = dict(
    founder_name="Bob",
    company_name="HardwareCo",
    company_stage="pre_seed",
    industry=["hardware"],
    location="US",
    one_liner="Hardware done right",
    incorporation_country="US",
    incorporated=True,
    team_size=2,
    has_technical_cofounder=True,
    funding_raised_usd_cents=0,
)

# Session C: pre_seed AI startup, US incorporated, $500k raised — exercises new rules.
_PROFILE_C = dict(
    founder_name="Carol",
    company_name="AICo",
    company_stage="pre_seed",
    industry=["ai"],
    location="US",
    one_liner="AI for the people",
    incorporation_country="US",
    incorporated=True,
    team_size=3,
    has_technical_cofounder=True,
    funding_raised_usd_cents=50000000,  # $500k
)

# Session D: same as C but with $3M raised — YC should become ineligible.
_PROFILE_D = dict(
    founder_name="Dana",
    company_name="AICo2",
    company_stage="pre_seed",
    industry=["ai"],
    location="US",
    one_liner="AI for business",
    incorporation_country="US",
    incorporated=True,
    team_size=3,
    has_technical_cofounder=True,
    funding_raised_usd_cents=300000000,  # $3M
)


async def _insert_profile(
    session: AsyncSession, session_id: str, fields: dict
) -> None:
    now = datetime.now(timezone.utc)
    profile = Profile(session_id=session_id, created_at=now, updated_at=now, **fields)
    session.add(profile)
    await session.commit()


@pytest_asyncio.fixture
async def seeded_with_profiles(session_factory, seeded_grants):
    async with session_factory() as session:
        await _insert_profile(session, SESSION_A, _PROFILE_A)
        await _insert_profile(session, SESSION_B, _PROFILE_B)
        await _insert_profile(session, SESSION_C, _PROFILE_C)
        await _insert_profile(session, SESSION_D, _PROFILE_D)
    return seeded_grants


# ── helpers ───────────────────────────────────────────────────────────────────


async def _match(client, session_id: str, body: dict | None = None) -> tuple[int, dict]:
    res = await client.post(
        "/api/grants/match",
        json=body or {},
        headers={"X-Session-Id": session_id},
    )
    return res.status_code, res.json()


# ── 8. no body, no profile → 200, results, match_profile returned ─────────────


@pytest.mark.asyncio
async def test_match_no_body_no_profile(client, seeded_grants):
    status, body = await _match(client, "brand-new-session")
    assert status == 200
    assert "results" in body
    assert "match_profile" in body
    assert isinstance(body["results"], list)
    assert body["total_evaluated"] == 5


# ── 9. body overrides win over stored profile ─────────────────────────────────


@pytest.mark.asyncio
async def test_match_overrides_win_over_profile(client, seeded_with_profiles):
    status, body = await _match(
        client,
        SESSION_A,
        {"stage": "series_a", "industry": ["biotech"], "location": "EU"},
    )
    assert status == 200
    mp = body["match_profile"]
    assert mp["company_stage"] == "series_a"
    assert mp["industry"] == ["biotech"]
    assert mp["location"] == "EU"


# ── 10. min_score filters out low scores ──────────────────────────────────────


@pytest.mark.asyncio
async def test_match_min_score_filters(client, seeded_with_profiles):
    _, all_body = await _match(client, SESSION_A, {})
    _, filtered_body = await _match(client, SESSION_A, {"min_score": 0.7})

    all_results = all_body["results"]
    filtered_results = filtered_body["results"]

    assert all(r["score"] >= 0.7 for r in filtered_results)
    assert len(filtered_results) <= len(all_results)


# ── 11. include_ineligible=true includes hard-fail grants ─────────────────────


@pytest.mark.asyncio
async def test_match_include_ineligible(client, seeded_with_profiles):
    # Session A is seed-stage; activate-fellowship requires pre_seed → hard fail.
    _, body = await _match(client, SESSION_A, {"include_ineligible": True})
    results = body["results"]
    ineligible = [r for r in results if r["tier"] == "ineligible"]
    assert len(ineligible) >= 1
    activate = next(
        (r for r in ineligible if r["grant"]["source_id"] == "activate-fellowship"),
        None,
    )
    assert activate is not None
    assert activate["score"] == 0.0
    assert len(activate["hard_fails"]) > 0

    # Without the flag, activate should be absent.
    _, body_no_inelig = await _match(client, SESSION_A, {})
    source_ids = {r["grant"]["source_id"] for r in body_no_inelig["results"]}
    assert "activate-fellowship" not in source_ids


# ── 12. results ordered by score DESC, deadline ASC NULLS LAST ────────────────


@pytest.mark.asyncio
async def test_match_ordering(client, seeded_with_profiles):
    # Session A (seed, ai, US) produces deterministic scores:
    #   nsf-sbir-phase-1      0.80 (deadline 2026-09-15)
    #   yc-w26                0.76 (deadline null)
    #   anthropic-academic    0.71 (deadline 2026-07-15)
    #   mozilla-builders      0.71 (deadline 2026-10-31)
    _, body = await _match(client, SESSION_A, {})
    results = body["results"]

    # Scores should be descending.
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True), "scores must be descending"

    # Top result should be NSF (highest score).
    assert results[0]["grant"]["source_id"] == "nsf-sbir-phase-1"

    # Among equal-score grants, earlier deadline comes first.
    tied = [r for r in results if r["score"] == results[2]["score"]]
    if len(tied) >= 2:
        deadlines = [r["grant"]["deadline"] for r in tied]
        non_null = [d for d in deadlines if d is not None]
        assert non_null == sorted(non_null)


# ── 13. limit truncates results ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_match_limit(client, seeded_with_profiles):
    _, body = await _match(client, SESSION_A, {"limit": 2})
    assert len(body["results"]) == 2
    assert body["total_returned"] == 2
    # Verify those are the top 2 by score.
    assert body["results"][0]["grant"]["source_id"] == "nsf-sbir-phase-1"
    assert body["results"][1]["grant"]["source_id"] == "yc-w26"


# ── 14. cross-session isolation ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_match_cross_session_isolation(client, seeded_with_profiles):
    # Session B (pre_seed, hardware) should have different match_profile from A.
    _, body_a = await _match(client, SESSION_A, {})
    _, body_b = await _match(client, SESSION_B, {})

    mp_a = body_a["match_profile"]
    mp_b = body_b["match_profile"]

    assert mp_a["company_stage"] == "seed"
    assert mp_b["company_stage"] == "pre_seed"
    assert mp_a["industry"] != mp_b["industry"]

    # Session B is pre_seed so activate-fellowship should NOT hard-fail for them.
    _, body_b_incl = await _match(client, SESSION_B, {"include_ineligible": True})
    activate = next(
        (
            r
            for r in body_b_incl["results"]
            if r["grant"]["source_id"] == "activate-fellowship"
        ),
        None,
    )
    assert activate is not None
    assert activate["tier"] != "ineligible", "pre_seed profile should pass activate's required_stage"


# ── 15. US incorporated profile — NSF, Activate, YC all eligible ──────────────


@pytest.mark.asyncio
async def test_us_incorporated_profile_passes_new_rules(client, seeded_with_profiles):
    # SESSION_C: pre_seed, ai, US, incorporated, team=3, $500k raised.
    _, body = await _match(client, SESSION_C, {"include_ineligible": True})
    results = body["results"]
    by_id = {r["grant"]["source_id"]: r for r in results}

    # NSF: required_location=US, requires_incorporation=true → both pass.
    nsf = by_id.get("nsf-sbir-phase-1")
    assert nsf is not None
    assert nsf["hard_fails"] == [], f"NSF should be eligible; got {nsf['hard_fails']}"

    # Activate: required_stage=pre_seed, required_location=US, min_team_size=2 → all pass.
    activate = by_id.get("activate-fellowship")
    assert activate is not None
    assert activate["hard_fails"] == [], f"Activate should be eligible; got {activate['hard_fails']}"

    # YC: max_funding_raised_usd=2M ($500k passes), requires_incorporation=true → pass.
    yc = by_id.get("yc-w26")
    assert yc is not None
    assert yc["hard_fails"] == [], f"YC should be eligible; got {yc['hard_fails']}"


# ── 16. over-funded profile — YC ineligible with correct rule failure ─────────


@pytest.mark.asyncio
async def test_over_funded_profile_yc_ineligible(client, seeded_with_profiles):
    # SESSION_D: same as C but $3M raised → YC max_funding_raised_usd=2M fails.
    _, body = await _match(client, SESSION_D, {"include_ineligible": True})
    results = body["results"]
    yc = next(
        (r for r in results if r["grant"]["source_id"] == "yc-w26"),
        None,
    )
    assert yc is not None
    assert yc["tier"] == "ineligible"
    assert yc["score"] == 0.0
    fails = yc["hard_fails"]
    assert len(fails) >= 1
    yc_fail = next((f for f in fails if f["rule"] == "max_funding_raised_usd"), None)
    assert yc_fail is not None, f"Expected max_funding_raised_usd failure; got {fails}"
    assert yc_fail["code"] == "above_threshold"
    assert "$3,000,000" in yc_fail["detail"]
