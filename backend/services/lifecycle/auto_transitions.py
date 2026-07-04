"""Automated lifecycle transition sweeps.

Pure service module — callers inject session_factory, redis, settings, and now.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.config import Settings
from backend.core.errors import ConflictError
from backend.core.logging import get_logger
from backend.db.models.grant_association import GrantLifecycleEvent, GrantTrack
from backend.db.models.lifecycle_auto_run import LifecycleAutoRun
from backend.services.lifecycle.transitions import validate_transition

logger = get_logger(__name__)

_LOCK_KEY = "lifecycle_auto:lock"
_QUERY_LIMIT = 1000


async def find_submitted_to_review_candidates(
    session: AsyncSession,
    settings: Settings,
    now: datetime,
) -> list[GrantTrack]:
    cutoff = now - timedelta(days=settings.LIFECYCLE_SUBMITTED_TO_REVIEW_DAYS)
    result = await session.execute(
        sa.select(GrantTrack)
        .where(
            GrantTrack.lifecycle_status == "submitted",
            GrantTrack.lifecycle_updated_at <= cutoff,
            GrantTrack.deleted_at.is_(None),
        )
        .limit(_QUERY_LIMIT)
    )
    tracks = list(result.scalars().all())
    if len(tracks) == _QUERY_LIMIT:
        logger.warning(
            "lifecycle_auto_candidate_limit_hit",
            rule="submitted_to_under_review",
            limit=_QUERY_LIMIT,
        )
    return tracks


async def find_abandoned_candidates(
    session: AsyncSession,
    settings: Settings,
    now: datetime,
) -> list[GrantTrack]:
    cutoff = now - timedelta(days=settings.LIFECYCLE_INACTIVITY_TO_ABANDONED_DAYS)
    result = await session.execute(
        sa.select(GrantTrack)
        .where(
            GrantTrack.lifecycle_status.in_(["interested", "researching", "drafting"]),
            GrantTrack.lifecycle_updated_at <= cutoff,
            GrantTrack.deleted_at.is_(None),
        )
        .limit(_QUERY_LIMIT)
    )
    tracks = list(result.scalars().all())
    if len(tracks) == _QUERY_LIMIT:
        logger.warning(
            "lifecycle_auto_candidate_limit_hit",
            rule="inactivity_to_abandoned",
            limit=_QUERY_LIMIT,
        )
    return tracks


async def apply_auto_transition(
    session: AsyncSession,
    track: GrantTrack,
    to_status: str,
    rule_name: str,
    now: datetime,
) -> bool:
    """Apply a single automated transition.

    Raises ValidationError for illegal pairs (defense-in-depth — callers shouldn't
    reach this, but guard against logic bugs in the query layer).
    Returns True on success, False if the DB operation fails.
    """
    from_status = track.lifecycle_status
    validate_transition(from_status, to_status, "automated")

    try:
        updated_at = track.lifecycle_updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        days_elapsed = int((now - updated_at).total_seconds() / 86400)

        existing_meta: dict[str, Any] = dict(track.lifecycle_metadata or {})
        merged_meta = {
            **existing_meta,
            "auto_transition_rule": rule_name,
            "auto_transition_at": now.isoformat(),
        }

        await session.execute(
            sa.update(GrantTrack)
            .where(GrantTrack.id == track.id)
            .values(
                lifecycle_status=to_status,
                lifecycle_updated_at=now,
                lifecycle_metadata=merged_meta,
                updated_at=now,
            )
        )

        event = GrantLifecycleEvent(
            grant_track_id=track.id,
            from_status=from_status,
            to_status=to_status,
            transition_kind="automated",
            note=None,
            event_metadata={
                "auto_transition_rule": rule_name,
                "days_in_prior_status": days_elapsed,
            },
            session_id=None,
            created_at=now,
        )
        session.add(event)
        await session.commit()

        logger.info(
            "lifecycle_auto_transition_applied",
            track_id=str(track.id),
            from_status=from_status,
            to_status=to_status,
            rule=rule_name,
            days_elapsed=days_elapsed,
        )
        return True

    except Exception:
        logger.exception(
            "lifecycle_auto_transition_failed",
            track_id=str(track.id),
            from_status=from_status,
            to_status=to_status,
            rule=rule_name,
        )
        await session.rollback()
        return False


async def run_lifecycle_auto_sweep(
    session_factory: async_sessionmaker[AsyncSession],
    redis,
    settings: Settings,
    triggered_by: str,
    triggered_session_id: str | None = None,
    now: datetime | None = None,
    pre_run_id: uuid.UUID | None = None,
) -> LifecycleAutoRun | None:
    if now is None:
        now = datetime.now(timezone.utc)

    run_id = pre_run_id or uuid.uuid4()
    log = logger.bind(job_id=str(run_id), triggered_by=triggered_by)

    acquired = await redis.set(
        _LOCK_KEY,
        str(run_id),
        nx=True,
        ex=settings.LIFECYCLE_AUTO_REDIS_LOCK_TTL_SECONDS,
    )
    if not acquired:
        in_progress = await redis.get(_LOCK_KEY)
        log.info("lifecycle_auto_skipped_locked", in_progress_run_id=in_progress)
        if triggered_by == "manual":
            raise ConflictError(
                "Lifecycle auto-transition already in progress",
                code="lifecycle_auto_in_progress",
                extra={"run_id": in_progress},
            )
        return None

    started_at = datetime.now(timezone.utc)
    log.info("lifecycle_auto_sweep_started")

    async with session_factory() as s:
        run = LifecycleAutoRun(
            id=run_id,
            started_at=started_at,
            triggered_by=triggered_by,
            triggered_session_id=triggered_session_id,
        )
        s.add(run)
        await s.commit()

    counters = {
        "tracks_scanned": 0,
        "transitions_submitted_to_review": 0,
        "transitions_to_abandoned": 0,
    }
    run_error: str | None = None

    try:
        # Rule 1: submitted → under_review
        async with session_factory() as s:
            candidates = await find_submitted_to_review_candidates(s, settings, now)

        log.info(
            "lifecycle_auto_candidates_found",
            rule="submitted_to_under_review",
            count=len(candidates),
        )

        for track in candidates:
            counters["tracks_scanned"] += 1
            try:
                async with session_factory() as s:
                    db_track = await s.get(GrantTrack, track.id)
                    if db_track is None:
                        continue
                    success = await apply_auto_transition(
                        s, db_track, "under_review", "submitted_to_under_review", now
                    )
                    if success:
                        counters["transitions_submitted_to_review"] += 1
            except Exception:
                log.exception("lifecycle_auto_track_error", track_id=str(track.id))

        # Rule 2: interested/researching/drafting → abandoned
        async with session_factory() as s:
            abandoned_candidates = await find_abandoned_candidates(s, settings, now)

        log.info(
            "lifecycle_auto_candidates_found",
            rule="inactivity_to_abandoned",
            count=len(abandoned_candidates),
        )

        for track in abandoned_candidates:
            counters["tracks_scanned"] += 1
            try:
                async with session_factory() as s:
                    db_track = await s.get(GrantTrack, track.id)
                    if db_track is None:
                        continue
                    success = await apply_auto_transition(
                        s, db_track, "abandoned", "inactivity_to_abandoned", now
                    )
                    if success:
                        counters["transitions_to_abandoned"] += 1
            except Exception:
                log.exception("lifecycle_auto_track_error", track_id=str(track.id))

    except Exception as exc:
        run_error = str(exc)[:500]
        log.exception("lifecycle_auto_sweep_error")

    finally:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        try:
            async with session_factory() as s:
                db_run = await s.get(LifecycleAutoRun, run_id)
                if db_run is not None:
                    db_run.finished_at = finished_at
                    db_run.tracks_scanned = counters["tracks_scanned"]
                    db_run.transitions_submitted_to_review = counters[
                        "transitions_submitted_to_review"
                    ]
                    db_run.transitions_to_abandoned = counters["transitions_to_abandoned"]
                    db_run.duration_ms = duration_ms
                    db_run.error = run_error
                    await s.commit()
        except Exception:
            log.exception("lifecycle_auto_run_finalize_error")

        await redis.delete(_LOCK_KEY)
        log.info(
            "lifecycle_auto_sweep_finished",
            duration_ms=duration_ms,
            **counters,
        )

    async with session_factory() as s:
        return await s.get(LifecycleAutoRun, run_id)
