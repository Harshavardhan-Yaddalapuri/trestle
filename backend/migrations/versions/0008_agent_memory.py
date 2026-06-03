"""agent memory table

Revision ID: 0008_agent_memory
Revises: 0007_grant_associations
Create Date: 2026-05-30

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_agent_memory"
down_revision: Union[str, None] = "0007_grant_associations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_memories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "structured",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("source_message_id", sa.Uuid(), nullable=True),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "kind IN ('preference','constraint','observation','correction')",
            name="ck_agent_memories_kind_valid",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="SET NULL",
            name="fk_agent_memories_conversation_id_conversations",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id"],
            ["messages.id"],
            ondelete="SET NULL",
            name="fk_agent_memories_source_message_id_messages",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agent_memories"),
    )
    op.create_index(
        "ix_agent_memories_session_deleted",
        "agent_memories",
        ["session_id", "deleted_at"],
    )
    op.create_index(
        "ix_agent_memories_session_kind_deleted",
        "agent_memories",
        ["session_id", "kind", "deleted_at"],
    )
    op.create_index(
        "ix_agent_memories_conversation_id",
        "agent_memories",
        ["conversation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_memories_conversation_id", table_name="agent_memories")
    op.drop_index("ix_agent_memories_session_kind_deleted", table_name="agent_memories")
    op.drop_index("ix_agent_memories_session_deleted", table_name="agent_memories")
    op.drop_table("agent_memories")
