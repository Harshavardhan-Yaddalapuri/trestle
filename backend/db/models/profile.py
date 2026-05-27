from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base
from backend.db.types import StringList
from backend.schemas.profile import COMPANY_STAGES


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
