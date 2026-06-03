"""Callable matching logic shared by the HTTP endpoint and the orchestrator."""
from __future__ import annotations

import uuid
from datetime import date

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.grant import Grant
from backend.db.models.grant_association import GrantDismissal, GrantTrack
from backend.db.models.profile import Profile
from backend.schemas.match import MatchRequest, MatchResponse
from backend.services.matching import evaluate_grant, resolve_match_profile


async def run_matching(
    session_id: str,
    db: AsyncSession,
    overrides: MatchRequest | None = None,
    limit: int = 5,
    min_score: float = 0.0,
) -> MatchResponse:
    """Run grant matching for a chat turn. Returns top eligible results."""
    if overrides is None:
        overrides = MatchRequest()

    profile_result = await db.execute(
        sa.select(Profile).where(Profile.session_id == session_id)
    )
    profile = profile_result.scalar_one_or_none()
    match_profile = resolve_match_profile(profile, overrides)

    dismissed_result = await db.execute(
        sa.select(GrantDismissal.grant_id).where(
            GrantDismissal.session_id == session_id
        )
    )
    dismissed_ids: set[uuid.UUID] = {row[0] for row in dismissed_result.all()}

    tracked_result = await db.execute(
        sa.select(GrantTrack.grant_id).where(
            GrantTrack.session_id == session_id,
            GrantTrack.deleted_at.is_(None),
        )
    )
    tracked_ids: set[uuid.UUID] = {row[0] for row in tracked_result.all()}

    today = date.today()
    stmt = (
        sa.select(Grant)
        .where(Grant.status == "active")
        .where(sa.or_(Grant.deadline.is_(None), Grant.deadline >= today))
        .limit(500)
    )
    if dismissed_ids:
        stmt = stmt.where(Grant.id.notin_(list(dismissed_ids)))

    grant_result = await db.execute(stmt)
    grants = list(grant_result.scalars().all())

    total_evaluated = len(grants)
    results = [evaluate_grant(match_profile, g) for g in grants]
    eligible = [r for r in results if r.tier != "ineligible" and r.score >= min_score]
    eligible.sort(key=lambda r: -r.score)
    truncated = eligible[:limit]

    for r in truncated:
        r.tracked = r.grant.id in tracked_ids
        r.dismissed = r.grant.id in dismissed_ids

    return MatchResponse(
        match_profile=match_profile,
        results=truncated,
        total_evaluated=total_evaluated,
        total_returned=len(truncated),
    )
