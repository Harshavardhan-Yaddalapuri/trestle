"""Check-in alert jobs for stale tracked grants."""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from backend.core.errors import UpstreamError
from backend.core.logging import get_logger
from backend.db.models.alert_delivery import AlertDelivery
from backend.db.models.grant import Grant
from backend.db.models.grant_association import GrantTrack
from backend.db.models.user import User
from backend.services.email import build_unsubscribe_url
from backend.services.email.templates import render_email
from backend.services.jobs.dispatch import TERMINAL_STATUSES, _utcnow, prefs_enabled

logger = get_logger(__name__)

_USER_PREFIX = "user:"
_USER_PREFIX_LEN = len(_USER_PREFIX)


def _user_id_from_session(session_id: str) -> uuid.UUID | None:
    if not session_id.startswith(_USER_PREFIX):
        return None
    try:
        return uuid.UUID(session_id[_USER_PREFIX_LEN:])
    except ValueError:
        return None


async def enqueue_checkin_alerts(ctx: dict) -> None:
    session_factory = ctx["session_factory"]
    settings = ctx["settings"]

    if not settings.ALERTS_ENABLED:
        logger.info("checkin_scan_skipped", reason="alerts_disabled")
        return

    today = date.today()
    iso_year, iso_week, _ = today.isocalendar()
    checkin_key = f"checkin:{iso_year}-W{iso_week:02d}"

    inactivity_cutoff = datetime.now(timezone.utc) - timedelta(
        days=settings.ALERTS_CHECKIN_INACTIVITY_DAYS
    )

    total_enqueued = 0
    total_skipped = 0

    # Find stale tracks for authenticated users
    async with session_factory() as db:
        tracks_result = await db.execute(
            sa.select(GrantTrack).where(
                GrantTrack.deleted_at.is_(None),
                GrantTrack.lifecycle_status.notin_(TERMINAL_STATUSES),
                GrantTrack.lifecycle_updated_at <= inactivity_cutoff,
                GrantTrack.session_id.like(f"{_USER_PREFIX}%"),
            )
        )
        tracks = tracks_result.scalars().all()

    # Group tracks by user_id
    tracks_by_user: dict[uuid.UUID, list[GrantTrack]] = defaultdict(list)
    for track in tracks:
        uid = _user_id_from_session(track.session_id)
        if uid is not None:
            tracks_by_user[uid].append(track)

    if not tracks_by_user:
        logger.info(
            "checkin_scan_complete",
            enqueued=0,
            skipped_duplicates=0,
            iso_week=checkin_key,
        )
        return

    # Load qualified users
    async with session_factory() as db:
        users_result = await db.execute(
            sa.select(User).where(
                User.id.in_(list(tracks_by_user.keys())),
                User.email_verified_at.is_not(None),
                User.disabled_at.is_(None),
            )
        )
        users = users_result.scalars().all()

    for user in users:
        if not prefs_enabled(user.alert_preferences, "check_ins"):
            continue

        stale_tracks = tracks_by_user.get(user.id, [])
        if not stale_tracks:
            continue

        track_count = len(stale_tracks)
        oldest_updated_at = min(t.lifecycle_updated_at for t in stale_tracks)
        if oldest_updated_at.tzinfo is None:
            oldest_updated_at = oldest_updated_at.replace(tzinfo=timezone.utc)
        oldest_age_days = (datetime.now(timezone.utc) - oldest_updated_at).days

        # Load top 3 grant names for the template
        top_grant_ids = [t.grant_id for t in stale_tracks[:3]]
        top_grant_names: list[str] = []
        if top_grant_ids:
            async with session_factory() as db:
                grants_result = await db.execute(
                    sa.select(Grant).where(Grant.id.in_(top_grant_ids))
                )
                grants_by_id = {g.id: g.name for g in grants_result.scalars().all()}
            top_grant_names = [
                grants_by_id.get(t.grant_id, "Unknown grant") for t in stale_tracks[:3]
            ]

        delivery_id: str | None = None
        try:
            async with session_factory() as db:
                async with db.begin():
                    delivery = AlertDelivery(
                        user_id=user.id,
                        alert_kind="check_in",
                        grant_id=None,
                        key=checkin_key,
                        status="queued",
                        payload={
                            "track_count": track_count,
                            "oldest_track_age_days": oldest_age_days,
                            "top_grant_names": top_grant_names,
                            "iso_week": checkin_key,
                        },
                    )
                    db.add(delivery)
                    await db.flush()
                    delivery_id = str(delivery.id)
        except IntegrityError:
            total_skipped += 1
            continue

        if delivery_id and ctx.get("redis") is not None:
            await ctx["redis"].enqueue_job("send_checkin_alert", delivery_id)
        total_enqueued += 1

    logger.info(
        "checkin_scan_complete",
        enqueued=total_enqueued,
        skipped_duplicates=total_skipped,
        iso_week=checkin_key,
    )


async def send_checkin_alert(ctx: dict, delivery_id: str) -> None:
    session_factory = ctx["session_factory"]
    email_client = ctx["email_client"]
    settings = ctx["settings"]

    async with session_factory() as db:
        delivery = await db.get(AlertDelivery, uuid.UUID(delivery_id))
        if delivery is None or delivery.status != "queued":
            return

        user = await db.get(User, delivery.user_id)

        if user is None:
            delivery.status = "failed"
            delivery.failure_reason = "user not found"
            delivery.updated_at = _utcnow()
            await db.commit()
            return

        track_count = delivery.payload.get("track_count", 0)
        oldest_age_days = delivery.payload.get("oldest_track_age_days", 0)
        top_grant_names = delivery.payload.get("top_grant_names", [])
        unsubscribe_url = build_unsubscribe_url(settings, user, "check_ins")

        rendered = render_email("check_in", {
            "track_count": track_count,
            "oldest_age_days": oldest_age_days,
            "top_grant_names": top_grant_names,
            "app_url": settings.AUTH_BASE_URL,
            "unsubscribe_url": unsubscribe_url,
        })

        try:
            await email_client.send(
                to=user.email_normalized,
                subject=rendered.subject,
                html=rendered.html,
                text=rendered.text,
                tags=["check_in"],
            )
            delivery.status = "sent"
            delivery.sent_at = _utcnow()
            delivery.updated_at = _utcnow()
            await db.commit()
            logger.info(
                "alert_sent",
                delivery_id=delivery_id,
                kind="check_in",
                user_id_prefix=str(user.id)[:8],
            )
        except UpstreamError as exc:
            if exc.code == "invalid_recipient":
                delivery.status = "suppressed"
                delivery.failure_reason = str(exc)[:500]
                delivery.updated_at = _utcnow()
                await db.commit()
                return
            delivery.status = "failed"
            delivery.failure_reason = str(exc)[:500]
            delivery.updated_at = _utcnow()
            await db.commit()
            raise
        except Exception as exc:
            delivery.status = "failed"
            delivery.failure_reason = str(exc)[:500]
            delivery.updated_at = _utcnow()
            await db.commit()
            raise
