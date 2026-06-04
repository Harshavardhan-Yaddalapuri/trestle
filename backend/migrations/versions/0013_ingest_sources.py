"""ingest_sources: source column on grants, source_payload, ingest_runs audit log

Revision ID: 0013_ingest_sources
Revises: 0012_alerts
Create Date: 2026-06-03

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_ingest_sources"
down_revision: Union[str, None] = "0012_alerts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── grants: source, source_payload, source_fetched_at ────────────────────
    op.add_column(
        "grants",
        sa.Column(
            "source",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'manual'"),
        ),
    )
    op.add_column(
        "grants",
        sa.Column(
            "source_payload",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.add_column(
        "grants",
        sa.Column("source_fetched_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_grants_source_valid",
        "grants",
        "source IN ('manual','grantsgov','sbirgov')",
    )
    op.create_index(
        "ix_grants_source_status_deadline",
        "grants",
        ["source", "status", "deadline"],
    )

    # ── ingest_runs audit table ───────────────────────────────────────────────
    op.create_table(
        "ingest_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("triggered_by", sa.Text(), nullable=False),
        sa.Column("triggered_session_id", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "records_fetched",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "records_inserted",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "records_updated",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "records_skipped",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "records_archived",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "triggered_by IN ('schedule','manual')",
            name="ck_ingest_runs_triggered_by",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ingest_runs"),
    )
    op.create_index(
        "ix_ingest_runs_source_started_at",
        "ingest_runs",
        ["source", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ingest_runs_source_started_at", table_name="ingest_runs")
    op.drop_table("ingest_runs")

    op.drop_index("ix_grants_source_status_deadline", table_name="grants")
    op.drop_constraint("ck_grants_source_valid", "grants", type_="check")
    op.drop_column("grants", "source_fetched_at")
    op.drop_column("grants", "source_payload")
    op.drop_column("grants", "source")
