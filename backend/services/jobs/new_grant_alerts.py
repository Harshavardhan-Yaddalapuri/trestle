"""New grant match alert jobs."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from backend.core.errors import UpstreamError
from backend.core.logging import get_logger
from backend.db.models.alert_delivery import AlertDelivery
from backend.db.models.grant import Grant
from backend.db.models.profile import Profile
from backend.db.models.user import User
from backend.schemas.match import MatchProfile
from backend.services.auth.identity import canonical_session_id_for_user
from backend.services.email import build_unsubscribe_url
from backend.services.email.templates import render_email
from backend.services.jobs.dispatch import _utcnow, prefs_enabled
from backend.services.matching import evaluate_grant

logger = get_logger(__name__)


def _build_match_profile(profile: Profile) -> MatchProfile:
    return MatchProfile(
        founder_name=profile.founder_name,
        company_name=profile.company_name,
        company_stage=profile.company_stage,
        industry=profile.industry,
        location=profile.location,
        one_liner=profile.one_liner,
        team_size=profile.team_size,
        has_technical_cofounder=profile.has_technical_cofounder,
        funding_raised_usd_cents=profile.funding_raised_usd_cents,
        funding_target_usd_cents=profile.funding_target_usd_cents,
        incorporated=profile.incorporated,
        incorporation_country=profile.incorporation_country,
        incorporation_state=profile.incorporation_state,
        regulatory_status=profile.regulatory_status or {},
    )


def _profile_complete_enough(profile: Profile) -> bool:
    """Minimum completeness gate: stage set and at least one location field set."""
    if profile.company_stage is None:
        return False
    if profile.incorporation_country is None and profile.location is None:
        return False
    return True


async def enqueue_new_grant_alerts(ctx: dict) -> None:
    session_factory = ctx["session_factory"]
    settings = ctx["settings"]

    if not settings.ALERTS_ENABLED:
        logger.info("new_grant_scan_skipped", reason="alerts_disabled")
        return

    lookback_cutoff = datetime.now(timezone.utc) - timedelta(
        hours=settings.ALERTS_NEW_GRANT_LOOKBACK_HOURS
    )
    total_enqueued = 0
    total_skipped = 0

    async with session_factory() as db:
        grants_result = await db.execute(
            sa.select(Grant).where(
                Grant.status == "active",
                Grant.created_at >= lookback_cutoff,
                Grant.last_alerted_to_users_at.is_(None),
            )
        )
        grants = grants_result.scalars().all()

    for grant in grants:
        async with session_factory() as db:
            users_result = await db.execute(
                sa.select(User).where(
                    User.email_verified_at.is_not(None),
                    User.disabled_at.is_(None),
                )
            )
            users = users_result.scalars().all()

        for user in users:
            if not prefs_enabled(user.alert_preferences, "new_grant_matches"):
                continue

            async with session_factory() as db:
                profile_result = await db.execute(
                    sa.select(Profile).where(
                        Profile.session_id == canonical_session_id_for_user(user.id)
                    )
                )
                profile = profile_result.scalar_one_or_none()

            if profile is None or not _profile_complete_enough(profile):
                continue

            match_profile = _build_match_profile(profile)
            result = evaluate_grant(match_profile, grant)

            if result.tier == "ineligible" or result.score < settings.ALERTS_NEW_GRANT_MIN_SCORE:
                continue

            key = f"new_grant:{grant.id}"
            delivery_id: str | None = None
            try:
                async with session_factory() as db:
                    async with db.begin():
                        delivery = AlertDelivery(
                            user_id=user.id,
                            alert_kind="new_grant_match",
                            grant_id=grant.id,
                            key=key,
                            status="queued",
                            payload={
                                "score": result.score,
                                "tier": result.tier,
                                "matched_on": result.matched_on,
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
                await ctx["redis"].enqueue_job("send_new_grant_alert", delivery_id)
            total_enqueued += 1

        # Mark grant as alerted regardless of how many users matched
        async with session_factory() as db:
            async with db.begin():
                await db.execute(
                    sa.update(Grant)
                    .where(Grant.id == grant.id)
                    .values(last_alerted_to_users_at=_utcnow())
                )

    logger.info(
        "new_grant_scan_complete",
        enqueued=total_enqueued,
        skipped_duplicates=total_skipped,
        grants_processed=len(grants),
    )


async def send_new_grant_alert(ctx: dict, delivery_id: str) -> None:
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

        score = delivery.payload.get("score", 0.0)
        tier = delivery.payload.get("tier", "unknown")
        unsubscribe_url = build_unsubscribe_url(settings, user, "new_grant_matches")

        rendered = render_email("new_grant_match", {
            "grant_name": grant.name,
            "score": score,
            "tier": tier,
            "app_url": settings.AUTH_BASE_URL,
            "unsubscribe_url": unsubscribe_url,
        })

        try:
            await email_client.send(
                to=user.email_normalized,
                subject=rendered.subject,
                html=rendered.html,
                text=rendered.text,
                tags=["new_grant_match"],
            )
            delivery.status = "sent"
            delivery.sent_at = _utcnow()
            delivery.updated_at = _utcnow()
            await db.commit()
            logger.info(
                "alert_sent",
                delivery_id=delivery_id,
                kind="new_grant_match",
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
