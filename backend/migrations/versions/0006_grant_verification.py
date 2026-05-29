"""grant verification tracking

Revision ID: 0006_grant_verification
Revises: 0005_profile_match_fields
Create Date: 2026-05-28

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_grant_verification"
down_revision: Union[str, None] = "0005_profile_match_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "grants",
        sa.Column(
            "consecutive_failures",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column("grants", sa.Column("last_verification_error", sa.Text(), nullable=True))

    op.create_table(
        "verification_runs",
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
            "grants_checked",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "grants_ok",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "grants_failed",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "grants_archived",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "triggered_by IN ('schedule','manual')",
            name="ck_verification_runs_triggered_by",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_verification_runs"),
    )
    op.create_index(
        "ix_verification_runs_started_at", "verification_runs", ["started_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_verification_runs_started_at", table_name="verification_runs")
    op.drop_table("verification_runs")
    op.drop_column("grants", "last_verification_error")
    op.drop_column("grants", "consecutive_failures")
