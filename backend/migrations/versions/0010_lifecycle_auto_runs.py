"""lifecycle auto-transition audit log

Revision ID: 0010_lifecycle_auto_runs
Revises: 0009_grant_lifecycle
Create Date: 2026-06-02

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_lifecycle_auto_runs"
down_revision: Union[str, None] = "0009_grant_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lifecycle_auto_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triggered_by", sa.Text(), nullable=False),
        sa.Column("triggered_session_id", sa.Text(), nullable=True),
        sa.Column(
            "tracks_scanned",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "transitions_submitted_to_review",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "transitions_to_abandoned",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "triggered_by IN ('schedule','manual')",
            name="ck_lifecycle_auto_runs_triggered_by",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_lifecycle_auto_runs"),
    )
    op.create_index(
        "ix_lifecycle_auto_runs_started_at",
        "lifecycle_auto_runs",
        ["started_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_lifecycle_auto_runs_started_at", table_name="lifecycle_auto_runs"
    )
    op.drop_table("lifecycle_auto_runs")
