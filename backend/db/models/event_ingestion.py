"""Persistence for generic event discovery, review, and source provenance."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base

_JsonType = sa.JSON().with_variant(JSONB(), "postgresql")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EventDiscoveryRun(Base):
    __tablename__ = "event_discovery_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_by: Mapped[str] = mapped_column(Text, nullable=False)
    strategy: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    records_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=sa.text("0"))
    records_accepted: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=sa.text("0"))
    records_pending_review: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=sa.text("0"))
    records_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=sa.text("0"))
    records_duplicates: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=sa.text("0"))
    error: Mapped[str | None] = mapped_column(Text)
    diagnostics: Mapped[dict[str, Any]] = mapped_column(_JsonType, nullable=False, default=dict)

    __table_args__ = (
        sa.CheckConstraint("triggered_by IN ('manual','schedule')", name="ck_event_discovery_runs_triggered_by"),
        Index("ix_event_discovery_runs_source_started", "source_url", "started_at"),
    )


class EventCandidate(Base):
    __tablename__ = "event_candidates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("event_discovery_runs.id"), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_identifier: Mapped[str | None] = mapped_column(Text)
    extraction_method: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_data: Mapped[dict[str, Any]] = mapped_column(_JsonType, nullable=False)
    field_confidences: Mapped[dict[str, Any]] = mapped_column(_JsonType, nullable=False, default=dict)
    evidence: Mapped[dict[str, Any]] = mapped_column(_JsonType, nullable=False, default=dict)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(_JsonType, nullable=False, default=dict)
    content_hash: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(Text, nullable=False, default="pending_review")
    validation_errors: Mapped[list[str]] = mapped_column(_JsonType, nullable=False, default=list)
    duplicate_event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("events.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        sa.CheckConstraint(
            "review_status IN ('accepted','pending_review','rejected','duplicate')",
            name="ck_event_candidates_review_status",
        ),
        Index("ix_event_candidates_status_created", "review_status", "created_at"),
    )


class EventProvenance(Base):
    __tablename__ = "event_provenance"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("event_candidates.id"))
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_identifier: Mapped[str | None] = mapped_column(Text)
    extraction_method: Mapped[str] = mapped_column(Text, nullable=False)
    field_confidences: Mapped[dict[str, Any]] = mapped_column(_JsonType, nullable=False, default=dict)
    evidence: Mapped[dict[str, Any]] = mapped_column(_JsonType, nullable=False, default=dict)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(_JsonType, nullable=False, default=dict)
    content_hash: Mapped[str | None] = mapped_column(Text)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    last_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        sa.UniqueConstraint("event_id", "source_url", "source_identifier", name="uq_event_provenance_event_source"),
        Index("ix_event_provenance_source_identifier", "source_url", "source_identifier"),
    )
