from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Integer, JSON, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base
from backend.db.types import StringList
from backend.schemas.profile import COMPANY_STAGES

_JsonType = JSON().with_variant(JSONB(), "postgresql")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


_STAGE_CHECK = "company_stage IN (" + ", ".join(f"'{s}'" for s in COMPANY_STAGES) + ")"


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    founder_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_stage: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[list | None] = mapped_column(StringList, nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(Text, nullable=True)
    one_liner: Mapped[str | None] = mapped_column(Text, nullable=True)
    goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    team_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_technical_cofounder: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    funding_raised_usd_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    funding_target_usd_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    incorporated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    incorporation_country: Mapped[str | None] = mapped_column(Text, nullable=True)
    incorporation_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    regulatory_status: Mapped[dict[str, Any]] = mapped_column(
        _JsonType, nullable=False, default=dict, server_default=sa.text("'{}'")
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
        CheckConstraint(_STAGE_CHECK, name="company_stage_valid"),
    )
