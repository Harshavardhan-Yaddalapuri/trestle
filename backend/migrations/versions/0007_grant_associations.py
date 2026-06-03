"""grant tracking and dismissal associations

Revision ID: 0007_grant_associations
Revises: 0006_grant_verification
Create Date: 2026-05-28

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_grant_associations"
down_revision: Union[str, None] = "0006_grant_verification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "grant_tracks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("grant_id", sa.Uuid(), nullable=False),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["grant_id"],
            ["grants.id"],
            ondelete="CASCADE",
            name="fk_grant_tracks_grant_id_grants",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_grant_tracks"),
    )
    op.create_index("ix_grant_tracks_session_id", "grant_tracks", ["session_id"])
    op.create_index(
        "ix_grant_tracks_session_deleted", "grant_tracks", ["session_id", "deleted_at"]
    )
    # Partial unique index: only one active track per (session, grant).
    # On Postgres the WHERE clause is enforced by the DB; on SQLite the WHERE is
    # ignored (full unique index), but application code's upsert logic (always
    # update-or-undelete an existing row, never insert a second one) means the
    # constraint is never violated regardless.
    op.create_index(
        "uq_grant_tracks_active",
        "grant_tracks",
        ["session_id", "grant_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "grant_dismissals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("grant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "reason IS NULL OR reason IN ("
            "'not_eligible','not_interested','already_applied','too_competitive','other')",
            name="ck_grant_dismissals_reason_valid",
        ),
        sa.ForeignKeyConstraint(
            ["grant_id"],
            ["grants.id"],
            ondelete="CASCADE",
            name="fk_grant_dismissals_grant_id_grants",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_grant_dismissals"),
        sa.UniqueConstraint(
            "session_id", "grant_id", name="uq_grant_dismissals_session_grant"
        ),
    )
    op.create_index(
        "ix_grant_dismissals_session_id", "grant_dismissals", ["session_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_grant_dismissals_session_id", table_name="grant_dismissals")
    op.drop_table("grant_dismissals")
    op.drop_index("uq_grant_tracks_active", table_name="grant_tracks")
    op.drop_index("ix_grant_tracks_session_deleted", table_name="grant_tracks")
    op.drop_index("ix_grant_tracks_session_id", table_name="grant_tracks")
    op.drop_table("grant_tracks")
