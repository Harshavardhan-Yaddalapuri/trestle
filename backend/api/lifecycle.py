"""Grant lifecycle endpoints — list, transition, and view event history.

Routes:
- GET    /lifecycle                     — list all tracks in a lifecycle state
- POST   /{grant_ref}/lifecycle         — transition a tracked grant
- GET    /{grant_ref}/lifecycle/events  — get event history for a tracked grant
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.grants import _resolve_grant, _track_out
from backend.core.errors import NotFoundError, ValidationError
from backend.core.logging import get_logger
from backend.db.models.grant import Grant
from backend.db.models.grant_association import GrantLifecycleEvent, GrantTrack
from backend.db.session import get_db
from backend.middleware.auth import get_identity, owner_clause
from backend.schemas.grant_association import (
    GrantLifecycleEventListResponse,
    GrantLifecycleEventOut,
    GrantLifecycleListResponse,
    GrantLifecycleTransitionIn,
    GrantTrackOut,
    decode_assoc_cursor,
    encode_assoc_cursor,
)
from backend.services.lifecycle import (
    LIFECYCLE_STATUSES,
    TERMINAL_STATUSES,
    validate_transition,
)

router = APIRouter(prefix="/grants", tags=["grants:lifecycle"])
logger = get_logger(__name__)

_ASSOC_DEFAULT_LIMIT = 20
_ASSOC_MAX_LIMIT = 50


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/lifecycle", response_model=GrantLifecycleListResponse)
async def list_lifecycle(
    request: Request,
    status: str | None = Query(default=None),
    limit: int = Query(_ASSOC_DEFAULT_LIMIT, ge=1, le=_ASSOC_MAX_LIMIT),
    cursor: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> GrantLifecycleListResponse:

    if status is not None:
        status_list = [s.strip() for s in status.split(",") if s.strip()]
        for s in status_list:
            if s not in LIFECYCLE_STATUSES:
                raise ValidationError(
                    f"Invalid lifecycle status: '{s}'",
                    code="invalid_status",
                    status_code=400,
                )
    else:
        # Default: all active (non-terminal) statuses.
        status_list = [s for s in LIFECYCLE_STATUSES if s not in TERMINAL_STATUSES]

    stmt = (
        sa.select(GrantTrack, Grant)
        .join(Grant, GrantTrack.grant_id == Grant.id)
        .where(
            owner_clause(GrantTrack.user_id, GrantTrack.session_id, request),
            GrantTrack.deleted_at.is_(None),
            GrantTrack.lifecycle_status.in_(status_list),
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
                GrantTrack.lifecycle_updated_at < cursor_ts,
                sa.and_(
                    GrantTrack.lifecycle_updated_at == cursor_ts,
                    GrantTrack.id < cursor_id,
                ),
            )
        )

    stmt = stmt.order_by(
        GrantTrack.lifecycle_updated_at.desc(), GrantTrack.id.desc()
    ).limit(limit + 1)

    result = await db.execute(stmt)
    rows = result.all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    items = [_track_out(track, grant) for track, grant in rows]

    next_cursor = (
        encode_assoc_cursor(rows[-1][0].lifecycle_updated_at, rows[-1][0].id)
        if has_more
        else None
    )

    return GrantLifecycleListResponse(items=items, next_cursor=next_cursor)


@router.post("/{grant_ref}/lifecycle", response_model=GrantTrackOut)
async def transition_lifecycle(
    grant_ref: str,
    body: GrantLifecycleTransitionIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GrantTrackOut:
    _, session_id = get_identity(request)
    grant = await _resolve_grant(grant_ref, db)

    track_result = await db.execute(
        sa.select(GrantTrack).where(
            owner_clause(GrantTrack.user_id, GrantTrack.session_id, request),
            GrantTrack.grant_id == grant.id,
            GrantTrack.deleted_at.is_(None),
        )
    )
    track = track_result.scalar_one_or_none()
    if track is None:
        raise NotFoundError("Grant not tracked")

    from_status = track.lifecycle_status
    validate_transition(from_status, body.to_status, "user")

    now = _utcnow()

    # Merge metadata: existing ∪ incoming, with None values removed.
    existing_meta: dict = track.lifecycle_metadata or {}
    merged_meta = {**existing_meta, **body.metadata}
    merged_meta = {k: v for k, v in merged_meta.items() if v is not None}

    await db.execute(
        sa.update(GrantTrack)
        .where(GrantTrack.id == track.id)
        .values(
            lifecycle_status=body.to_status,
            lifecycle_updated_at=now,
            lifecycle_metadata=merged_meta,
            updated_at=now,
        )
    )

    event = GrantLifecycleEvent(
        grant_track_id=track.id,
        from_status=from_status,
        to_status=body.to_status,
        transition_kind="user",
        note=body.note,
        event_metadata=body.metadata,
        session_id=session_id,
        created_at=now,
    )
    db.add(event)

    await db.commit()
    await db.refresh(track)

    return _track_out(track, grant)


@router.get(
    "/{grant_ref}/lifecycle/events",
    response_model=GrantLifecycleEventListResponse,
)
async def get_lifecycle_events(
    grant_ref: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GrantLifecycleEventListResponse:
    grant = await _resolve_grant(grant_ref, db)

    track_result = await db.execute(
        sa.select(GrantTrack).where(
            owner_clause(GrantTrack.user_id, GrantTrack.session_id, request),
            GrantTrack.grant_id == grant.id,
            GrantTrack.deleted_at.is_(None),
        )
    )
    track = track_result.scalar_one_or_none()
    if track is None:
        raise NotFoundError("Grant not tracked")

    events_result = await db.execute(
        sa.select(GrantLifecycleEvent)
        .where(GrantLifecycleEvent.grant_track_id == track.id)
        .order_by(GrantLifecycleEvent.created_at.asc())
    )
    events = events_result.scalars().all()

    return GrantLifecycleEventListResponse(
        events=[
            GrantLifecycleEventOut(
                id=e.id,
                from_status=e.from_status,  # type: ignore[arg-type]
                to_status=e.to_status,  # type: ignore[arg-type]
                transition_kind=e.transition_kind,  # type: ignore[arg-type]
                note=e.note,
                metadata=e.event_metadata or {},
                created_at=e.created_at,
            )
            for e in events
        ]
    )
