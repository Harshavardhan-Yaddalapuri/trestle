"""Add user_id to grant_tracks, grant_dismissals, and agent_memories

Revision ID: 0010_add_user_id_to_tracks_dismissals_memories
Revises: 0009_add_user_id
Create Date: 2026-06-03

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column already exists in the given table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns

revision: str = "0010_add_user_id_to_tracks_dismissals_memories"
down_revision: Union[str, None] = "0009_add_user_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # grant_tracks
    if not column_exists("grant_tracks", "user_id"):
        op.add_column("grant_tracks", sa.Column("user_id", sa.Text(), nullable=True))
        op.create_index("ix_grant_tracks_user_id", "grant_tracks", ["user_id"])

    # grant_dismissals
    if not column_exists("grant_dismissals", "user_id"):
        op.add_column("grant_dismissals", sa.Column("user_id", sa.Text(), nullable=True))
        op.create_index("ix_grant_dismissals_user_id", "grant_dismissals", ["user_id"])

    # agent_memories
    if not column_exists("agent_memories", "user_id"):
        op.add_column("agent_memories", sa.Column("user_id", sa.Text(), nullable=True))
        op.create_index("ix_agent_memories_user_id", "agent_memories", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_memories_user_id", table_name="agent_memories")
    op.drop_column("agent_memories", "user_id")

    op.drop_index("ix_grant_dismissals_user_id", table_name="grant_dismissals")
    op.drop_column("grant_dismissals", "user_id")

    op.drop_index("ix_grant_tracks_user_id", table_name="grant_tracks")
    op.drop_column("grant_tracks", "user_id")
