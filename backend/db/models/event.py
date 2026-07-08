from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base
from backend.db.types import StringList

_JsonType = JSON().with_variant(JSONB(), "postgresql")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_payload: Mapped[dict[str, Any]] = mapped_column(
        _JsonType, nullable=False, default=dict, server_default=sa.text("'{}'")
    )
    source_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    url: Mapped[str] = mapped_column(Text, nullable=False)
    host_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_virtual: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa.text("0")
    )
    location_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    region: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)

    industry_tags: Mapped[list | None] = mapped_column(StringList, nullable=True)
    stage_tags: Mapped[list | None] = mapped_column(StringList, nullable=True)
    benefit_tags: Mapped[list | None] = mapped_column(StringList, nullable=True)
    attendee_types: Mapped[list | None] = mapped_column(StringList, nullable=True)

    cost_usd_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    application_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa.text("0")
    )
    host_quality_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5, server_default=sa.text("0.5")
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="active", server_default=sa.text("'active'")
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

    __table_args__ = (
        CheckConstraint(
            "status IN ('active','expired','archived')",
            name="ck_events_status_valid",
        ),
        CheckConstraint(
            "host_quality_score >= 0.0 AND host_quality_score <= 1.0",
            name="ck_events_host_quality_score_range",
        ),
        Index("ix_events_status_starts_at", "status", "starts_at"),
        Index("ix_events_source_starts_at", "source", "starts_at"),
    )
