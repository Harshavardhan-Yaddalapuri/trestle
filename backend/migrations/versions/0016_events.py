"""events table for founder event discovery and matching.

Revision ID: 0016_events
Revises: 0015_users_alert_prefs
Create Date: 2026-07-08
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_events"
down_revision: Union[str, None] = "0015_users_alert_prefs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "source_payload",
            json_type,
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("source_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("host_name", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.Text(), nullable=True),
        sa.Column(
            "is_virtual",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("location_text", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("region", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("industry_tags", json_type, nullable=True),
        sa.Column("stage_tags", json_type, nullable=True),
        sa.Column("benefit_tags", json_type, nullable=True),
        sa.Column("attendee_types", json_type, nullable=True),
        sa.Column("cost_usd_cents", sa.Integer(), nullable=True),
        sa.Column(
            "application_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "host_quality_score",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.5"),
        ),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('active','expired','archived')",
            name="ck_events_status_valid",
        ),
        sa.CheckConstraint(
            "host_quality_score >= 0.0 AND host_quality_score <= 1.0",
            name="ck_events_host_quality_score_range",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_events"),
        sa.UniqueConstraint("source_id", name="uq_events_source_id"),
    )
    op.create_index("ix_events_source_id", "events", ["source_id"], unique=True)
    op.create_index("ix_events_status_starts_at", "events", ["status", "starts_at"])
    op.create_index("ix_events_source_starts_at", "events", ["source", "starts_at"])


def downgrade() -> None:
    op.drop_index("ix_events_source_starts_at", table_name="events")
    op.drop_index("ix_events_status_starts_at", table_name="events")
    op.drop_index("ix_events_source_id", table_name="events")
    op.drop_table("events")
