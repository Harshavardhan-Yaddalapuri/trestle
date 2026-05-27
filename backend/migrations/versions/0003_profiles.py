"""profiles table

Revision ID: 0003_profiles
Revises: 0002_chat
Create Date: 2026-05-26

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.schemas.profile import COMPANY_STAGES

revision: str = "0003_profiles"
down_revision: Union[str, None] = "0002_chat"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STAGE_LIST = ", ".join(f"'{s}'" for s in COMPANY_STAGES)


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("founder_name", sa.Text(), nullable=True),
        sa.Column("company_name", sa.Text(), nullable=True),
        sa.Column("company_stage", sa.Text(), nullable=True),
        sa.Column("industry", sa.JSON(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("one_liner", sa.Text(), nullable=True),
        sa.Column("goals", sa.Text(), nullable=True),
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
            f"company_stage IN ({_STAGE_LIST})",
            name="company_stage_valid",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_profiles"),
        sa.UniqueConstraint("session_id", name="uq_profiles_session_id"),
    )
    op.create_index(
        "ix_profiles_session_id",
        "profiles",
        ["session_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_profiles_session_id", table_name="profiles")
    op.drop_table("profiles")
