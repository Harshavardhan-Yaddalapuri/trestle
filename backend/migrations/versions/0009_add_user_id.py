"""Add user_id to profiles and conversations

Revision ID: 0009_add_user_id
Revises: 0008_agent_memory
Create Date: 2026-06-03

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_add_user_id"
down_revision: Union[str, None] = "0008_agent_memory"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user_id to profiles
    op.add_column(
        "profiles",
        sa.Column("user_id", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_profiles_user_id",
        "profiles",
        ["user_id"],
    )

    # Add user_id to conversations
    op.add_column(
        "conversations",
        sa.Column("user_id", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_conversations_user_id",
        "conversations",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_column("conversations", "user_id")
    op.drop_index("ix_profiles_user_id", table_name="profiles")
    op.drop_column("profiles", "user_id")
