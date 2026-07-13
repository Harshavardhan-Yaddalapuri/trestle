from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import Settings, get_settings
from backend.db.models.event import Event
from backend.db.models.profile import Profile
from backend.db.session import get_db, get_db_factory
from backend.middleware.auth import owner_clause
from backend.redis_client import get_redis
from backend.schemas.event import (
    EventDiscoveryResponse,
    EventListResponse,
    EventMatchRequest,
    EventMatchResponse,
    EventSummary,
)
from backend.services.events.matching import evaluate_event, is_event_active, resolve_event_profile
from backend.services.events.orchestration import run_events_discovery_sweep

router = APIRouter(prefix="/events", tags=["events"])

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100


def _list_filter_string(col, value: str, is_postgres: bool) -> sa.ColumnElement:
    if is_postgres:
        return col.overlap([value, "any"])
    return sa.or_(
        sa.cast(col, sa.Text).like(f'%"{value}"%'),
        sa.cast(col, sa.Text).like('%"any"%'),
    )


@router.post("/discover", response_model=EventDiscoveryResponse)
async def discover_events(
    request: Request,
    redis = Depends(get_redis),
    session_factory = Depends(get_db_factory),
    settings: Settings = Depends(get_settings),
) -> EventDiscoveryResponse:
    result = await run_events_discovery_sweep(
        session_factory=session_factory,
        redis=redis,
        settings=settings,
        triggered_by="manual",
        triggered_session_id=getattr(request.state, "session_id", None),
    )
    assert result is not None
    return EventDiscoveryResponse(
        discovered=result.discovered,
        inserted=result.inserted,
        updated=result.updated,
        sources_scanned=result.sources_scanned,
    )


@router.get("", response_model=EventListResponse)
async def list_events(
    limit: int = Query(_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    industry: str | None = Query(default=None),
    stage: str | None = Query(default=None),
    location: str | None = Query(default=None),
    include_expired: bool = Query(default=False),
    q: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> EventListResponse:
    conn = await db.connection()
    is_postgres = conn.dialect.name == "postgresql"

    stmt = sa.select(Event).where(Event.status != "archived")
    if not include_expired:
        now = datetime.now(UTC)
        stmt = stmt.where(
            sa.or_(
                Event.ends_at.is_(None),
                Event.ends_at >= now,
            )
        )
    if industry is not None:
        stmt = stmt.where(
            Event.industry_tags.isnot(None),
            _list_filter_string(Event.industry_tags, industry, is_postgres),
        )
    if stage is not None:
        stmt = stmt.where(
            Event.stage_tags.isnot(None),
            _list_filter_string(Event.stage_tags, stage, is_postgres),
        )
    if location is not None:
        pattern = f"%{location}%"
        if is_postgres:
            stmt = stmt.where(
                sa.or_(
                    Event.location_text.ilike(pattern),
                    Event.city.ilike(pattern),
                    Event.region.ilike(pattern),
                    Event.country.ilike(pattern),
                )
            )
        else:
            stmt = stmt.where(
                sa.or_(
                    Event.location_text.like(pattern),
                    Event.city.like(pattern),
                    Event.region.like(pattern),
                    Event.country.like(pattern),
                )
            )
    if q is not None:
        q_pattern = f"%{q}%"
        if is_postgres:
            stmt = stmt.where(sa.or_(Event.name.ilike(q_pattern), Event.description.ilike(q_pattern)))
        else:
            stmt = stmt.where(sa.or_(Event.name.like(q_pattern), Event.description.like(q_pattern)))

    result = await db.execute(stmt.order_by(Event.starts_at.asc()).limit(limit))
    items = [EventSummary.model_validate(row) for row in result.scalars().all()]
    return EventListResponse(items=items)


@router.post("/match", response_model=EventMatchResponse)
async def match_events(
    body: EventMatchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> EventMatchResponse:
    profile_result = await db.execute(
        sa.select(Profile).where(owner_clause(Profile.user_id, Profile.session_id, request))
    )
    profile = profile_result.scalar_one_or_none()
    match_profile = resolve_event_profile(profile, body)

    stmt = sa.select(Event).where(Event.status != "archived")
    if not body.include_virtual:
        stmt = stmt.where(Event.is_virtual.is_(False))
    result = await db.execute(stmt.limit(1000))
    events = list(result.scalars().all())

    filtered = [e for e in events if is_event_active(e, include_expired=body.include_expired)]
    total_evaluated = len(filtered)
    scored = [
        evaluate_event(match_profile, event, include_virtual=body.include_virtual)
        for event in filtered
    ]
    scored = [row for row in scored if row.score >= body.min_score]
    scored.sort(
        key=lambda row: (
            -row.score,
            row.event.starts_at,
        )
    )
    truncated = scored[: body.limit]
    return EventMatchResponse(
        match_profile=match_profile,
        results=truncated,
        total_evaluated=total_evaluated,
        total_returned=len(truncated),
    )
