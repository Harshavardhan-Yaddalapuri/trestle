"""grant lifecycle state machine and event log

Revision ID: 0009_grant_lifecycle
Revises: 0008_agent_memory
Create Date: 2026-06-02

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_grant_lifecycle"
down_revision: Union[str, None] = "0008_agent_memory"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LIFECYCLE_STATUSES = (
    "'interested','researching','drafting','submitted','under_review',"
    "'awarded','rejected','withdrawn','abandoned'"
)


def upgrade() -> None:
    # ── Extend grant_tracks with lifecycle columns ────────────────────────────
    op.add_column(
        "grant_tracks",
        sa.Column(
            "lifecycle_status",
            sa.Text(),
            nullable=False,
            server_default="interested",
        ),
    )
    op.add_column(
        "grant_tracks",
        sa.Column(
            "lifecycle_updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column(
        "grant_tracks",
        sa.Column(
            "lifecycle_metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )

    # Composite index for lifecycle list query.
    op.create_index(
        "ix_grant_tracks_session_lifecycle",
        "grant_tracks",
        ["session_id", "lifecycle_status", "deleted_at"],
    )

    # ── New audit-log table ───────────────────────────────────────────────────
    op.create_table(
        "grant_lifecycle_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("grant_track_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.Text(), nullable=True),
        sa.Column("to_status", sa.Text(), nullable=False),
        sa.Column("transition_kind", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            f"to_status IN ({_LIFECYCLE_STATUSES})",
            name="ck_grant_lifecycle_events_to_status_valid",
        ),
        sa.CheckConstraint(
            f"from_status IS NULL OR from_status IN ({_LIFECYCLE_STATUSES})",
            name="ck_grant_lifecycle_events_from_status_valid",
        ),
        sa.CheckConstraint(
            "transition_kind IN ('user','automated','system')",
            name="ck_grant_lifecycle_events_transition_kind_valid",
        ),
        sa.ForeignKeyConstraint(
            ["grant_track_id"],
            ["grant_tracks.id"],
            ondelete="CASCADE",
            name="fk_grant_lifecycle_events_grant_track_id_grant_tracks",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_grant_lifecycle_events"),
    )
    op.create_index(
        "ix_grant_lifecycle_events_track_created",
        "grant_lifecycle_events",
        ["grant_track_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_grant_lifecycle_events_track_created",
        table_name="grant_lifecycle_events",
    )
    op.drop_table("grant_lifecycle_events")
    op.drop_index(
        "ix_grant_tracks_session_lifecycle", table_name="grant_tracks"
    )
    op.drop_column("grant_tracks", "lifecycle_metadata")
    op.drop_column("grant_tracks", "lifecycle_updated_at")
    op.drop_column("grant_tracks", "lifecycle_status")
