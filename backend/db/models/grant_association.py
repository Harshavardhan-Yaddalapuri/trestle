from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base

_JsonType = JSON().with_variant(JSONB(), "postgresql")

DISMISSAL_REASONS = (
    "not_eligible",
    "not_interested",
    "already_applied",
    "too_competitive",
    "other",
)

_LIFECYCLE_STATUSES_CHECK = (
    "'interested','researching','drafting','submitted','under_review',"
    "'awarded','rejected','withdrawn','abandoned'"
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GrantTrack(Base):
    __tablename__ = "grant_tracks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    session_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    grant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("grants.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    lifecycle_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="interested",
        server_default=sa.text("'interested'"),
    )
    lifecycle_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
    )
    lifecycle_metadata: Mapped[dict[str, Any]] = mapped_column(
        _JsonType,
        nullable=False,
        default=dict,
        server_default=sa.text("'{}'"),
    )

    __table_args__ = (
        Index("ix_grant_tracks_session_deleted", "session_id", "deleted_at"),
        Index(
            "ix_grant_tracks_session_lifecycle",
            "session_id",
            "lifecycle_status",
            "deleted_at",
        ),
        CheckConstraint(
            f"lifecycle_status IN ({_LIFECYCLE_STATUSES_CHECK})",
            name="ck_grant_tracks_lifecycle_status_valid",
        ),
    )


class GrantDismissal(Base):
    __tablename__ = "grant_dismissals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    session_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    grant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("grants.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_grant_dismissals_session_grant", "session_id", "grant_id"),
        CheckConstraint(
            "reason IS NULL OR reason IN ("
            "'not_eligible','not_interested','already_applied','too_competitive','other')",
            name="ck_grant_dismissals_reason_valid",
        ),
        sa.UniqueConstraint(
            "session_id", "grant_id", name="uq_grant_dismissals_session_grant"
        ),
    )


class GrantLifecycleEvent(Base):
    __tablename__ = "grant_lifecycle_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    grant_track_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("grant_tracks.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    to_status: Mapped[str] = mapped_column(Text, nullable=False)
    transition_kind: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "metadata" shadows Base.metadata, so use event_metadata as Python name.
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        _JsonType,
        nullable=False,
        default=dict,
        server_default=sa.text("'{}'"),
    )
    session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_grant_lifecycle_events_track_created",
            "grant_track_id",
            "created_at",
        ),
        CheckConstraint(
            f"to_status IN ({_LIFECYCLE_STATUSES_CHECK})",
            name="ck_grant_lifecycle_events_to_status_valid",
        ),
        CheckConstraint(
            f"from_status IS NULL OR from_status IN ({_LIFECYCLE_STATUSES_CHECK})",
            name="ck_grant_lifecycle_events_from_status_valid",
        ),
        CheckConstraint(
            "transition_kind IN ('user','automated','system')",
            name="ck_grant_lifecycle_events_transition_kind_valid",
        ),
    )
