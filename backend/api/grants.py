from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors import NotFoundError, ValidationError
from backend.core.logging import get_logger
from backend.db.models.grant import Grant
from backend.db.models.grant_association import GrantDismissal, GrantTrack
from backend.db.models.profile import Profile
from backend.db.session import get_db
from backend.middleware.auth import get_identity, owner_clause
from backend.schemas.grant import (
    GrantDetail,
    GrantListResponse,
    GrantSummary,
    decode_grant_cursor,
    encode_grant_cursor,
)
from backend.schemas.grant_association import (
    GrantDismissalIn,
    GrantDismissalItem,
    GrantDismissalListResponse,
    GrantDismissalOut,
    GrantTrackIn,
    GrantTrackListResponse,
    GrantTrackOut,
    decode_assoc_cursor,
    encode_assoc_cursor,
)
from backend.schemas.match import MatchRequest, MatchResponse
from backend.schemas.verification import GrantVerificationStatus
from backend.services.matching import evaluate_grant, resolve_match_profile

router = APIRouter(prefix="/grants", tags=["grants"])
logger = get_logger(__name__)

_DEFAULT_STATUS = "active"
_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100
_ASSOC_DEFAULT_LIMIT = 20
_ASSOC_MAX_LIMIT = 50


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _track_out(track: GrantTrack, grant: Grant) -> GrantTrackOut:
    return GrantTrackOut(
        id=track.id,
        grant=GrantSummary.model_validate(grant),
        note=track.note,
        created_at=track.created_at,
        updated_at=track.updated_at,
        lifecycle_status=track.lifecycle_status,  # type: ignore[arg-type]
        lifecycle_updated_at=track.lifecycle_updated_at,
        lifecycle_metadata=track.lifecycle_metadata or {},
    )


def _list_filter_string(col, value: str, is_postgres: bool) -> sa.ColumnElement:
    """Return WHERE predicate for "value is in the StringList column"."""
    if is_postgres:
        return col.overlap([value, "any"])
    # SQLite: JSON stored as text – crude but correct for simple alphanumeric values.
    return sa.or_(
        sa.cast(col, sa.Text).like(f'%"{value}"%'),
        sa.cast(col, sa.Text).like('%"any"%'),
    )


async def _resolve_grant(grant_ref: str, db: AsyncSession) -> Grant:
    """Resolve a grant by UUID or source_id."""
    result = await db.execute(
        sa.select(Grant).where(Grant.source_id == grant_ref)
    )
    grant = result.scalar_one_or_none()

    if grant is None:
        try:
            grant_id = uuid.UUID(grant_ref)
        except ValueError:
            raise NotFoundError("Grant not found")
        grant = await db.get(Grant, grant_id)

    if grant is None:
        raise NotFoundError("Grant not found")

    return grant


@router.get("", response_model=GrantListResponse)
async def list_grants(
    limit: int = Query(_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    cursor: str | None = Query(default=None),
    type: str | None = Query(default=None),
    stage: str | None = Query(default=None),
    industry: str | None = Query(default=None),
    location: str | None = Query(default=None),
    status: str = Query(default=_DEFAULT_STATUS),
    q: str | None = Query(default=None),
    include_duplicates: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
) -> GrantListResponse:
    conn = await db.connection()
    is_postgres = conn.dialect.name == "postgresql"

    stmt = sa.select(Grant).where(Grant.status == status)

    if not include_duplicates:
        stmt = stmt.where(Grant.is_duplicate_of.is_(None))

    if type is not None:
        stmt = stmt.where(Grant.type == type)
    if stage is not None:
        stmt = stmt.where(
            Grant.stage.isnot(None),
            _list_filter_string(Grant.stage, stage, is_postgres),
        )
    if industry is not None:
        stmt = stmt.where(
            Grant.industry.isnot(None),
            _list_filter_string(Grant.industry, industry, is_postgres),
        )
    if location is not None:
        stmt = stmt.where(
            Grant.location.isnot(None),
            _list_filter_string(Grant.location, location, is_postgres),
        )
    if q is not None:
        q_pattern = f"%{q}%"
        if is_postgres:
            stmt = stmt.where(
                sa.or_(
                    Grant.name.ilike(q_pattern),
                    Grant.description.ilike(q_pattern),
                )
            )
        else:
            stmt = stmt.where(
                sa.or_(
                    Grant.name.like(q_pattern),
                    Grant.description.like(q_pattern),
                )
            )

    if cursor is not None:
        try:
            cursor_deadline, cursor_id = decode_grant_cursor(cursor)
        except ValueError as exc:
            raise ValidationError(
                "Invalid cursor", code="invalid_cursor", status_code=400
            ) from exc
        if cursor_deadline is not None:
            stmt = stmt.where(
                sa.or_(
                    Grant.deadline > cursor_deadline,
                    sa.and_(Grant.deadline == cursor_deadline, Grant.id > cursor_id),
                    Grant.deadline.is_(None),
                )
            )
        else:
            stmt = stmt.where(
                sa.and_(Grant.deadline.is_(None), Grant.id > cursor_id)
            )

    # Sort: deadline ASC NULLS LAST, then id ASC for stable tiebreak.
    if is_postgres:
        order = [sa.nullslast(Grant.deadline.asc()), Grant.id.asc()]
    else:
        order = [
            sa.case((Grant.deadline.is_(None), 1), else_=0).asc(),
            Grant.deadline.asc(),
            Grant.id.asc(),
        ]

    stmt = stmt.order_by(*order).limit(limit + 1)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    items = [GrantSummary.model_validate(r) for r in rows]

    next_cursor = (
        encode_grant_cursor(rows[-1].deadline, rows[-1].id) if has_more else None
    )

    return GrantListResponse(items=items, next_cursor=next_cursor, total_estimate=None)


@router.post("/match", response_model=MatchResponse)
async def match_grants(
    body: MatchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> MatchResponse:
    user_id, session_id = get_identity(request)

    profile_result = await db.execute(
        sa.select(Profile).where(
            owner_clause(Profile.user_id, Profile.session_id, request)
        )
    )
    profile = profile_result.scalar_one_or_none()

    match_profile = resolve_match_profile(profile, body)

    dismissed_result = await db.execute(
        sa.select(GrantDismissal.grant_id).where(
            owner_clause(GrantDismissal.user_id, GrantDismissal.session_id, request)
        )
    )
    dismissed_ids: set[uuid.UUID] = {row[0] for row in dismissed_result.all()}

    tracked_result = await db.execute(
        sa.select(GrantTrack.grant_id).where(
            owner_clause(GrantTrack.user_id, GrantTrack.session_id, request),
            GrantTrack.deleted_at.is_(None),
        )
    )
    tracked_ids: set[uuid.UUID] = {row[0] for row in tracked_result.all()}

    today = date.today()
    stmt = (
        sa.select(Grant)
        .where(Grant.status == "active")
        .where(sa.or_(Grant.deadline.is_(None), Grant.deadline >= today))
        .where(Grant.is_duplicate_of.is_(None))
        .limit(1000)
    )

    if not body.include_dismissed and dismissed_ids:
        stmt = stmt.where(Grant.id.notin_(list(dismissed_ids)))

    grant_result = await db.execute(stmt)
    grants = grant_result.scalars().all()

    total_evaluated = len(grants)

    results = [evaluate_grant(match_profile, g) for g in grants]

    if body.include_ineligible:
        filtered = [
            r for r in results if r.score >= body.min_score or r.tier == "ineligible"
        ]
    else:
        filtered = [
            r for r in results if r.score >= body.min_score and r.tier != "ineligible"
        ]

    filtered.sort(
        key=lambda r: (
            -r.score,
            (1, date.max, str(r.grant.id))
            if r.grant.deadline is None
            else (0, r.grant.deadline, str(r.grant.id)),
        )
    )

    truncated = filtered[: body.limit]

    for r in truncated:
        r.tracked = r.grant.id in tracked_ids
        r.dismissed = r.grant.id in dismissed_ids

    return MatchResponse(
        match_profile=match_profile,
        results=truncated,
        total_evaluated=total_evaluated,
        total_returned=len(truncated),
    )


# ── Tracking endpoints ────────────────────────────────────────────────────────


@router.post("/track", response_model=GrantTrackOut)
async def track_grant(
    body: GrantTrackIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GrantTrackOut:
    user_id, session_id = get_identity(request)
    grant = await _resolve_grant(body.grant_id, db)
    now = _utcnow()

    # Look for any existing row (active or soft-deleted) for this (session, grant).
    existing_result = await db.execute(
        sa.select(GrantTrack).where(
            owner_clause(GrantTrack.user_id, GrantTrack.session_id, request),
            GrantTrack.grant_id == grant.id,
        )
    )
    track = existing_result.scalar_one_or_none()

    if track is not None:
        # Update active row or undelete soft-deleted row.
        # Preserve lifecycle state on re-track (funnel survives un-tracking).
        await db.execute(
            sa.update(GrantTrack)
            .where(GrantTrack.id == track.id)
            .values(note=body.note, updated_at=now, deleted_at=None, user_id=user_id)
        )
        await db.commit()
        await db.refresh(track)
    else:
        track = GrantTrack(
            user_id=user_id,
            session_id=session_id,
            grant_id=grant.id,
            note=body.note,
            created_at=now,
            updated_at=now,
            lifecycle_updated_at=now,
        )
        db.add(track)
        await db.commit()
        await db.refresh(track)

    return _track_out(track, grant)


@router.delete("/track/{grant_ref}", status_code=204)
async def untrack_grant(
    grant_ref: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    user_id, session_id = get_identity(request)
    grant = await _resolve_grant(grant_ref, db)
    now = _utcnow()

    result = await db.execute(
        sa.update(GrantTrack)
        .where(
            owner_clause(GrantTrack.user_id, GrantTrack.session_id, request),
            GrantTrack.grant_id == grant.id,
            GrantTrack.deleted_at.is_(None),
        )
        .values(deleted_at=now, updated_at=now)
    )
    if result.rowcount == 0:
        raise NotFoundError("Track not found")
    await db.commit()
    return Response(status_code=204)


@router.get("/tracked", response_model=GrantTrackListResponse)
async def list_tracked(
    request: Request,
    limit: int = Query(_ASSOC_DEFAULT_LIMIT, ge=1, le=_ASSOC_MAX_LIMIT),
    cursor: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> GrantTrackListResponse:
    user_id, session_id = get_identity(request)

    stmt = (
        sa.select(GrantTrack, Grant)
        .join(Grant, GrantTrack.grant_id == Grant.id)
        .where(
            owner_clause(GrantTrack.user_id, GrantTrack.session_id, request),
            GrantTrack.deleted_at.is_(None),
        )
    )

    if cursor is not None:
        try:
            cursor_ts, cursor_id = decode_assoc_cursor(cursor)
        except ValueError as exc:
            raise ValidationError(
                "Invalid cursor", code="invalid_cursor", status_code=400
            ) from exc
        stmt = stmt.where(
            sa.or_(
                GrantTrack.updated_at < cursor_ts,
                sa.and_(
                    GrantTrack.updated_at == cursor_ts,
                    GrantTrack.id < cursor_id,
                ),
            )
        )

    stmt = stmt.order_by(
        GrantTrack.updated_at.desc(), GrantTrack.id.desc()
    ).limit(limit + 1)

    result = await db.execute(stmt)
    rows = result.all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    items = [_track_out(track, grant) for track, grant in rows]

    next_cursor = (
        encode_assoc_cursor(rows[-1][0].updated_at, rows[-1][0].id) if has_more else None
    )

    return GrantTrackListResponse(items=items, next_cursor=next_cursor)


# ── Dismissal endpoints ───────────────────────────────────────────────────────


@router.post("/dismiss", response_model=GrantDismissalOut)
async def dismiss_grant(
    body: GrantDismissalIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GrantDismissalOut:
    user_id, session_id = get_identity(request)
    grant = await _resolve_grant(body.grant_id, db)
    now = _utcnow()

    existing_result = await db.execute(
        sa.select(GrantDismissal).where(
            owner_clause(GrantDismissal.user_id, GrantDismissal.session_id, request),
            GrantDismissal.grant_id == grant.id,
        )
    )
    dismissal = existing_result.scalar_one_or_none()

    if dismissal is not None:
        await db.execute(
            sa.update(GrantDismissal)
            .where(GrantDismissal.id == dismissal.id)
            .values(reason=body.reason, user_id=user_id)
        )
        await db.commit()
        await db.refresh(dismissal)
    else:
        dismissal = GrantDismissal(
            user_id=user_id,
            session_id=session_id,
            grant_id=grant.id,
            reason=body.reason,
            created_at=now,
        )
        db.add(dismissal)
        await db.commit()
        await db.refresh(dismissal)

    return GrantDismissalOut(
        id=dismissal.id,
        grant_id=dismissal.grant_id,
        reason=dismissal.reason,
        created_at=dismissal.created_at,
    )


@router.delete("/dismiss/{grant_ref}", status_code=204)
async def undismiss_grant(
    grant_ref: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    user_id, session_id = get_identity(request)
    grant = await _resolve_grant(grant_ref, db)

    result = await db.execute(
        sa.delete(GrantDismissal).where(
            owner_clause(GrantDismissal.user_id, GrantDismissal.session_id, request),
            GrantDismissal.grant_id == grant.id,
        )
    )
    if result.rowcount == 0:
        raise NotFoundError("Dismissal not found")
    await db.commit()
    return Response(status_code=204)


@router.get("/dismissed", response_model=GrantDismissalListResponse)
async def list_dismissed(
    request: Request,
    limit: int = Query(_ASSOC_DEFAULT_LIMIT, ge=1, le=_ASSOC_MAX_LIMIT),
    cursor: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> GrantDismissalListResponse:
    user_id, session_id = get_identity(request)

    stmt = (
        sa.select(GrantDismissal, Grant)
        .join(Grant, GrantDismissal.grant_id == Grant.id)
        .where(
            owner_clause(GrantDismissal.user_id, GrantDismissal.session_id, request),
        )
    )

    if cursor is not None:
        try:
            cursor_ts, cursor_id = decode_assoc_cursor(cursor)
        except ValueError as exc:
            raise ValidationError(
                "Invalid cursor", code="invalid_cursor", status_code=400
            ) from exc
        stmt = stmt.where(
            sa.or_(
                GrantDismissal.created_at < cursor_ts,
                sa.and_(
                    GrantDismissal.created_at == cursor_ts,
                    GrantDismissal.id < cursor_id,
                ),
            )
        )

    stmt = stmt.order_by(
        GrantDismissal.created_at.desc(), GrantDismissal.id.desc()
    ).limit(limit + 1)

    result = await db.execute(stmt)
    rows = result.all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    items = [
        GrantDismissalItem(
            id=dismissal.id,
            grant=GrantSummary.model_validate(grant),
            reason=dismissal.reason,
            created_at=dismissal.created_at,
        )
        for dismissal, grant in rows
    ]

    next_cursor = (
        encode_assoc_cursor(rows[-1][0].created_at, rows[-1][0].id) if has_more else None
    )

    return GrantDismissalListResponse(items=items, next_cursor=next_cursor)


# ── Detail / verification ─────────────────────────────────────────────────────


@router.get("/{grant_ref}", response_model=GrantDetail)
async def get_grant(
    grant_ref: str,
    db: AsyncSession = Depends(get_db),
) -> GrantDetail:
    grant = await _resolve_grant(grant_ref, db)
    return GrantDetail.model_validate(grant)


@router.get("/{grant_ref}/verification", response_model=GrantVerificationStatus)
async def get_verification_status(
    grant_ref: str,
    db: AsyncSession = Depends(get_db),
) -> GrantVerificationStatus:
    grant = await _resolve_grant(grant_ref, db)
    return GrantVerificationStatus(
        source_status=grant.source_status,
        last_verified_at=grant.last_verified_at.isoformat() if grant.last_verified_at else None,
        consecutive_failures=grant.consecutive_failures,
        last_verification_error=grant.last_verification_error,
    )
