from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base

_JsonType = JSON().with_variant(JSONB(), "postgresql")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AlertDelivery(Base):
    __tablename__ = "alert_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_kind: Mapped[str] = mapped_column(Text, nullable=False)
    grant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("grants.id", ondelete="SET NULL"),
        nullable=True,
    )
    key: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="queued",
        server_default=sa.text("'queued'"),
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        _JsonType,
        nullable=False,
        default=dict,
        server_default=sa.text("'{}'"),
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
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "alert_kind IN ('deadline_reminder','new_grant_match','check_in')",
            name="ck_alert_deliveries_alert_kind_valid",
        ),
        CheckConstraint(
            "status IN ('queued','sent','failed','suppressed')",
            name="ck_alert_deliveries_status_valid",
        ),
        sa.UniqueConstraint(
            "user_id", "alert_kind", "key",
            name="uq_alert_deliveries_user_kind_key",
        ),
        Index("ix_alert_deliveries_user_kind_status", "user_id", "alert_kind", "status"),
        Index("ix_alert_deliveries_status_created", "status", "created_at"),
    )
