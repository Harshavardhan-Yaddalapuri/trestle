"""grant_dedup: cross-source deduplication columns + ingest_runs.duplicates_found

Revision ID: 0014_grant_dedup
Revises: 0013_ingest_sources
Create Date: 2026-06-03

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_grant_dedup"
down_revision: Union[str, None] = "0013_ingest_sources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── grants: dedup columns ────────────────────────────────────────────────
    op.add_column(
        "grants",
        sa.Column("is_duplicate_of", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "grants",
        sa.Column("dedup_match_kind", sa.Text(), nullable=True),
    )
    op.add_column(
        "grants",
        sa.Column("dedup_checked_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_check_constraint(
        "ck_grants_dedup_match_kind_valid",
        "grants",
        "dedup_match_kind IS NULL OR dedup_match_kind IN ('topic_number','url','manual')",
    )

    # FK: is_duplicate_of → grants.id ON DELETE SET NULL
    # Use batch_alter_table for SQLite compatibility in local dev
    with op.batch_alter_table("grants") as batch_op:
        batch_op.create_foreign_key(
            "fk_grants_is_duplicate_of",
            "grants",
            ["is_duplicate_of"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_index(
        "ix_grants_is_duplicate_of",
        "grants",
        ["is_duplicate_of"],
    )

    # ── ingest_runs: duplicates_found counter ─────────────────────────────────
    op.add_column(
        "ingest_runs",
        sa.Column(
            "duplicates_found",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("ingest_runs", "duplicates_found")

    op.drop_index("ix_grants_is_duplicate_of", table_name="grants")
    with op.batch_alter_table("grants") as batch_op:
        batch_op.drop_constraint("fk_grants_is_duplicate_of", type_="foreignkey")

    op.drop_constraint("ck_grants_dedup_match_kind_valid", "grants", type_="check")
    op.drop_column("grants", "dedup_checked_at")
    op.drop_column("grants", "dedup_match_kind")
    op.drop_column("grants", "is_duplicate_of")
