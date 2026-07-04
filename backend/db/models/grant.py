from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
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

VALID_SOURCES = ("manual", "grantsgov", "sbirgov")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Grant(Base):
    __tablename__ = "grants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source: Mapped[str] = mapped_column(
        Text, nullable=False, default="manual", server_default=sa.text("'manual'")
    )
    source_payload: Mapped[dict[str, Any]] = mapped_column(
        _JsonType, nullable=False, default=dict, server_default=sa.text("'{}'")
    )
    source_fetched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    application_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    rolling: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa.text("0")
    )
    stage: Mapped[list | None] = mapped_column(StringList, nullable=True)
    industry: Mapped[list | None] = mapped_column(StringList, nullable=True)
    location: Mapped[list | None] = mapped_column(StringList, nullable=True)
    eligibility: Mapped[dict[str, Any]] = mapped_column(
        _JsonType, nullable=False, default=dict, server_default=sa.text("'{}'")
    )
    provider_name: Mapped[str] = mapped_column(Text, nullable=False)
    provider_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="active", server_default=sa.text("'active'")
    )
    last_alerted_to_users_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_status: Mapped[str] = mapped_column(
        Text, nullable=False, default="unknown", server_default=sa.text("'unknown'")
    )
    consecutive_failures: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    last_verification_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_duplicate_of: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("grants.id", ondelete="SET NULL"),
        nullable=True,
    )
    dedup_match_kind: Mapped[str | None] = mapped_column(Text, nullable=True)
    dedup_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
            "type IN ('grant','contest','accelerator','fellowship','other')",
            name="ck_grants_type_valid",
        ),
        CheckConstraint(
            "provider_type IS NULL OR provider_type IN ('government','foundation','corporate','vc','accelerator','other')",
            name="ck_grants_provider_type_valid",
        ),
        CheckConstraint(
            "status IN ('active','expired','archived')",
            name="ck_grants_status_valid",
        ),
        CheckConstraint(
            "source_status IN ('unknown','ok','redirect','gone','error')",
            name="ck_grants_source_status_valid",
        ),
        CheckConstraint(
            "source IN ('manual','grantsgov','sbirgov')",
            name="ck_grants_source_valid",
        ),
        Index("ix_grants_status", "status"),
        Index("ix_grants_deadline", "deadline"),
        Index(
            "ix_grants_alert_scan",
            "status",
            "created_at",
            "last_alerted_to_users_at",
        ),
        Index("ix_grants_source_status_deadline", "source", "status", "deadline"),
        Index("ix_grants_is_duplicate_of", "is_duplicate_of"),
        CheckConstraint(
            "dedup_match_kind IS NULL OR dedup_match_kind IN ('topic_number','url','manual')",
            name="ck_grants_dedup_match_kind_valid",
        ),
    )
