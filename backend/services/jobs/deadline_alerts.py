"""Deadline reminder alert jobs."""
from __future__ import annotations

import uuid
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


async def enqueue_deadline_alerts(ctx: dict) -> None:
    session_factory = ctx["session_factory"]
    settings = ctx["settings"]

    if not settings.ALERTS_ENABLED:
        logger.info("deadline_scan_skipped", reason="alerts_disabled")
        return

    today = date.today()
    total_enqueued = 0
    total_skipped = 0

    for window_days in settings.ALERTS_DEADLINE_WINDOWS_DAYS:
        target_date = today + timedelta(days=window_days)

        async with session_factory() as db:
            grants_result = await db.execute(
                sa.select(Grant).where(
                    Grant.status == "active",
                    Grant.deadline == target_date,
                )
            )
            grants = grants_result.scalars().all()

        for grant in grants:
            async with session_factory() as db:
                # Find active user tracks (session_id format: "user:<uuid>")
                tracks_result = await db.execute(
                    sa.select(GrantTrack).where(
                        GrantTrack.grant_id == grant.id,
                        GrantTrack.deleted_at.is_(None),
                        GrantTrack.lifecycle_status.notin_(TERMINAL_STATUSES),
                        GrantTrack.session_id.like(f"{_USER_PREFIX}%"),
                    )
                )
                tracks = tracks_result.scalars().all()

                if not tracks:
                    continue

                user_ids = [
                    uid
                    for t in tracks
                    if (uid := _user_id_from_session(t.session_id)) is not None
                ]
                users_result = await db.execute(
                    sa.select(User).where(
                        User.id.in_(user_ids),
                        User.email_verified_at.is_not(None),
                        User.disabled_at.is_(None),
                    )
                )
                users = users_result.scalars().all()

            for user in users:
                if not prefs_enabled(user.alert_preferences, "deadline_reminders"):
                    continue

                key = f"deadline:{grant.id}:{window_days}"
                delivery_id: str | None = None
                try:
                    async with session_factory() as db:
                        async with db.begin():
                            delivery = AlertDelivery(
                                user_id=user.id,
                                alert_kind="deadline_reminder",
                                grant_id=grant.id,
                                key=key,
                                status="queued",
                                payload={
                                    "deadline": target_date.isoformat(),
                                    "window_days": window_days,
                                    "grant_name": grant.name,
                                },
                            )
                            db.add(delivery)
                            await db.flush()
                            delivery_id = str(delivery.id)
                except IntegrityError:
                    total_skipped += 1
                    continue

                if delivery_id and ctx.get("redis") is not None:
                    await ctx["redis"].enqueue_job("send_deadline_alert", delivery_id)
                total_enqueued += 1

    logger.info(
        "deadline_scan_complete",
        enqueued=total_enqueued,
        skipped_duplicates=total_skipped,
    )


async def send_deadline_alert(ctx: dict, delivery_id: str) -> None:
    session_factory = ctx["session_factory"]
    email_client = ctx["email_client"]
    settings = ctx["settings"]

    async with session_factory() as db:
        delivery = await db.get(AlertDelivery, uuid.UUID(delivery_id))
        if delivery is None or delivery.status != "queued":
            return

        user = await db.get(User, delivery.user_id)
        grant = await db.get(Grant, delivery.grant_id) if delivery.grant_id else None

        if user is None or grant is None:
            delivery.status = "failed"
            delivery.failure_reason = "user or grant not found"
            delivery.updated_at = _utcnow()
            await db.commit()
            return

        window_days = delivery.payload.get("window_days", 0)
        deadline_str = delivery.payload.get("deadline", "")
        unsubscribe_url = build_unsubscribe_url(settings, user, "deadline_reminders")

        rendered = render_email("deadline_reminder", {
            "grant_name": grant.name,
            "window_days": window_days,
            "deadline_str": deadline_str,
            "app_url": settings.AUTH_BASE_URL,
            "unsubscribe_url": unsubscribe_url,
        })

        try:
            await email_client.send(
                to=user.email_normalized,
                subject=rendered.subject,
                html=rendered.html,
                text=rendered.text,
                tags=["deadline_reminder"],
            )
            delivery.status = "sent"
            delivery.sent_at = _utcnow()
            delivery.updated_at = _utcnow()
            await db.commit()
            logger.info(
                "alert_sent",
                delivery_id=delivery_id,
                kind="deadline_reminder",
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
