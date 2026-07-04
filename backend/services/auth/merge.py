"""Anonymous-session → authenticated-user merge.

Re-keys all session-scoped rows from the anonymous session's UUID to the
stable "user:{uuid}" identifier.  Everything runs in a single transaction so
the merge is all-or-nothing.

User-set values always win over anon values on field conflicts.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from backend.db.models.chat import Conversation
from backend.db.models.grant_association import (
    GrantDismissal,
    GrantLifecycleEvent,
    GrantTrack,
)
from backend.db.models.memory import AgentMemory
from backend.db.models.profile import Profile
from backend.schemas.auth import MergeSummary
from backend.services.auth.identity import (
    USER_SESSION_PREFIX,
    canonical_session_id_for_user,
    is_user_session_id,
)

logger = structlog.get_logger(__name__)

# Scalar profile fields eligible for fill-from-anon (user wins on non-null).
_PROFILE_SCALAR_FIELDS = [
    "founder_name",
    "company_name",
    "company_stage",
    "location",
    "website",
    "one_liner",
    "goals",
    "team_size",
    "has_technical_cofounder",
    "funding_raised_usd_cents",
    "funding_target_usd_cents",
    "incorporated",
    "incorporation_country",
    "incorporation_state",
]


async def merge_anonymous_session(
    db: AsyncSession,
    from_session_id: str,
    to_user_id: uuid.UUID,
) -> MergeSummary:
    """Re-key all rows from *from_session_id* to the canonical user session id.

    Runs in a single transaction — any failure rolls back everything.
    Safe to retry: a second call after a successful first call finds empty
    tables and returns with all-zero counts (no_op=False).
    """
    prefix = from_session_id[:8]

    # Guard: same-session (shouldn't happen with the prefix scheme, but be safe).
    to_session_id = canonical_session_id_for_user(to_user_id)
    if from_session_id == to_session_id:
        return MergeSummary(no_op=True, from_session_id_prefix=prefix)

    # Guard: never merge from another authenticated user's namespace.
    if is_user_session_id(from_session_id):
        logger.warning(
            "merge_from_user_session_rejected",
            from_prefix=prefix,
            to_user_id=str(to_user_id),
        )
        return MergeSummary(no_op=True, from_session_id_prefix=prefix)

    summary = MergeSummary(from_session_id_prefix=prefix)
    now = datetime.now(timezone.utc)

    async with db.begin():
        # ── 1. Profile merge ──────────────────────────────────────────────────
        anon_profile = (
            await db.execute(
                sa.select(Profile).where(Profile.session_id == from_session_id)
            )
        ).scalar_one_or_none()

        user_profile = (
            await db.execute(
                sa.select(Profile).where(Profile.session_id == to_session_id)
            )
        ).scalar_one_or_none()

        if anon_profile is not None and user_profile is None:
            anon_profile.session_id = to_session_id
            summary.profile_moved = 1

        elif anon_profile is not None and user_profile is not None:
            # Fill user's null fields from anon; user-set values are authoritative.
            fields_filled = 0
            for field in _PROFILE_SCALAR_FIELDS:
                if getattr(user_profile, field) is None and getattr(anon_profile, field) is not None:
                    setattr(user_profile, field, getattr(anon_profile, field))
                    fields_filled += 1

            # industry list: union with dedup (user's items first)
            user_ind = user_profile.industry or []
            anon_ind = anon_profile.industry or []
            merged_ind = list(user_ind) + [x for x in anon_ind if x not in user_ind]
            if user_profile.industry is None and merged_ind:
                user_profile.industry = merged_ind

            # regulatory_status dict: merge with user winning on key conflicts
            merged_reg = {
                **(anon_profile.regulatory_status or {}),
                **(user_profile.regulatory_status or {}),
            }
            user_profile.regulatory_status = merged_reg
            user_profile.updated_at = now

            await db.delete(anon_profile)
            summary.profile_merged = 1
            summary.profile_fields_filled_from_anon = fields_filled

        # ── 2. Conversations bulk rekey ───────────────────────────────────────
        conv_result = await db.execute(
            sa.update(Conversation)
            .where(Conversation.session_id == from_session_id)
            .values(session_id=to_session_id)
        )
        summary.conversations_moved = conv_result.rowcount

        # ── 3. GrantTrack conflicts ───────────────────────────────────────────
        # Find active tracks that exist in BOTH sessions for the same grant.
        anon_t = aliased(GrantTrack, name="anon_t")
        user_t = aliased(GrantTrack, name="user_t")

        conflict_rows = (
            await db.execute(
                sa.select(anon_t, user_t)
                .join(
                    user_t,
                    sa.and_(
                        anon_t.grant_id == user_t.grant_id,
                        user_t.session_id == to_session_id,
                        user_t.deleted_at.is_(None),
                    ),
                )
                .where(
                    anon_t.session_id == from_session_id,
                    anon_t.deleted_at.is_(None),
                )
            )
        ).all()

        conflict_anon_track_ids: list[uuid.UUID] = []

        for anon_row, user_row in conflict_rows:
            conflict_anon_track_ids.append(anon_row.id)

            # Merge note: user's value preserved; anon appended if user is empty.
            if user_row.note:
                if anon_row.note:
                    user_row.note = f"{user_row.note} | {anon_row.note}"
            else:
                user_row.note = anon_row.note

            # Merge lifecycle_metadata: anon as base, user wins on conflict.
            user_row.lifecycle_metadata = {
                **(anon_row.lifecycle_metadata or {}),
                **(user_row.lifecycle_metadata or {}),
            }
            user_row.updated_at = now

            # Re-link anon track's lifecycle events to the user track.
            await db.execute(
                sa.update(GrantLifecycleEvent)
                .where(GrantLifecycleEvent.grant_track_id == anon_row.id)
                .values(grant_track_id=user_row.id)
            )

            # Soft-delete the anon track — stays as a tombstone in anon namespace.
            anon_row.deleted_at = now
            summary.grant_tracks_merged += 1

        # Bulk rekey non-conflicting tracks (including soft-deleted ones).
        if conflict_anon_track_ids:
            gt_stmt = (
                sa.update(GrantTrack)
                .where(
                    GrantTrack.session_id == from_session_id,
                    GrantTrack.id.not_in(conflict_anon_track_ids),
                )
                .values(session_id=to_session_id)
            )
        else:
            gt_stmt = (
                sa.update(GrantTrack)
                .where(GrantTrack.session_id == from_session_id)
                .values(session_id=to_session_id)
            )
        gt_result = await db.execute(gt_stmt)
        summary.grant_tracks_moved = gt_result.rowcount

        # ── 4. GrantDismissal conflicts ───────────────────────────────────────
        anon_d = aliased(GrantDismissal, name="anon_d")
        user_d = aliased(GrantDismissal, name="user_d")

        dismissal_conflicts = (
            await db.execute(
                sa.select(anon_d, user_d)
                .join(
                    user_d,
                    sa.and_(
                        anon_d.grant_id == user_d.grant_id,
                        user_d.session_id == to_session_id,
                    ),
                )
                .where(anon_d.session_id == from_session_id)
            )
        ).all()

        conflict_dismissal_grant_ids: list[uuid.UUID] = []

        for anon_dis, user_dis in dismissal_conflicts:
            conflict_dismissal_grant_ids.append(anon_dis.grant_id)
            # User's reason is authoritative; fill from anon only if user has none.
            if user_dis.reason is None and anon_dis.reason is not None:
                user_dis.reason = anon_dis.reason
            await db.delete(anon_dis)
            summary.grant_dismissals_merged += 1

        if conflict_dismissal_grant_ids:
            gd_stmt = (
                sa.update(GrantDismissal)
                .where(
                    GrantDismissal.session_id == from_session_id,
                    GrantDismissal.grant_id.not_in(conflict_dismissal_grant_ids),
                )
                .values(session_id=to_session_id)
            )
        else:
            gd_stmt = (
                sa.update(GrantDismissal)
                .where(GrantDismissal.session_id == from_session_id)
                .values(session_id=to_session_id)
            )
        gd_result = await db.execute(gd_stmt)
        summary.grant_dismissals_moved = gd_result.rowcount

        # ── 5. AgentMemory bulk rekey (no dedup — duplicates are acceptable) ──
        mem_result = await db.execute(
            sa.update(AgentMemory)
            .where(AgentMemory.session_id == from_session_id)
            .values(session_id=to_session_id)
        )
        summary.agent_memories_moved = mem_result.rowcount

        # ── 6. GrantLifecycleEvent session_id rekey (NULL = automated, skip) ─
        gle_result = await db.execute(
            sa.update(GrantLifecycleEvent)
            .where(
                GrantLifecycleEvent.session_id == from_session_id,
                GrantLifecycleEvent.session_id.is_not(None),
            )
            .values(session_id=to_session_id)
        )
        summary.lifecycle_events_moved = gle_result.rowcount

    logger.info(
        "session_merged",
        from_prefix=prefix,
        to_user_id=str(to_user_id),
        profile_moved=summary.profile_moved,
        profile_merged=summary.profile_merged,
        conversations_moved=summary.conversations_moved,
        grant_tracks_moved=summary.grant_tracks_moved,
        grant_tracks_merged=summary.grant_tracks_merged,
        grant_dismissals_moved=summary.grant_dismissals_moved,
        grant_dismissals_merged=summary.grant_dismissals_merged,
        agent_memories_moved=summary.agent_memories_moved,
        lifecycle_events_moved=summary.lifecycle_events_moved,
    )

    return summary
