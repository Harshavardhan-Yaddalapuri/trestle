from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base

DISMISSAL_REASONS = (
    "not_eligible",
    "not_interested",
    "already_applied",
    "too_competitive",
    "other",
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

    __table_args__ = (
        Index("ix_grant_tracks_session_deleted", "session_id", "deleted_at"),
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
