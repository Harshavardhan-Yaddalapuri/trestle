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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


# JSON on SQLite (tests), JSONB on Postgres (prod migration).
JsonType = JSON().with_variant(JSONB(), "postgresql")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Python-side default gives microsecond precision on SQLite (which only
    # supports second-precision via CURRENT_TIMESTAMP); server_default still
    # applies for raw SQL inserts (e.g. migrations).
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

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # `metadata` is reserved on DeclarativeBase, so map to a different Python attr.
    meta: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JsonType,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    __table_args__ = (
        CheckConstraint(
            "role IN ('user','assistant','system','tool')",
            name="role_valid",
        ),
        Index(
            "ix_messages_conversation_id_created_at",
            "conversation_id",
            "created_at",
        ),
    )
