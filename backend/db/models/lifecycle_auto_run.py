from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, DateTime, Index, Integer, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LifecycleAutoRun(Base):
    __tablename__ = "lifecycle_auto_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    triggered_by: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    tracks_scanned: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    transitions_submitted_to_review: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    transitions_to_abandoned: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "triggered_by IN ('schedule','manual')",
            name="ck_lifecycle_auto_runs_triggered_by",
        ),
        Index("ix_lifecycle_auto_runs_started_at", "started_at"),
    )
