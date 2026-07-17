"""users: minimal user table for Supabase-shaped auth (sub claim + alert_prefs JSONB).

Revision ID: 0015_users_alert_prefs
Revises: 0014_grant_dedup
Create Date: 2026-06-07

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_users_alert_prefs"
down_revision: Union[str, None] = "0014_grant_dedup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "users" in tables:
        existing_cols = {col["name"] for col in inspector.get_columns("users")}
        if "sub" not in existing_cols:
            op.add_column("users", sa.Column("sub", sa.String(length=255), nullable=True))
        if "alert_prefs" not in existing_cols:
            op.add_column(
                "users",
                sa.Column(
                    "alert_prefs",
                    sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
                    nullable=False,
                    server_default=sa.text("'{}'"),
                ),
            )
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("users")}
        if "ix_users_sub" not in existing_indexes:
            op.create_index("ix_users_sub", "users", ["sub"], unique=True)
        existing_uniques = {c["name"] for c in inspector.get_unique_constraints("users")}
        if "uq_users_sub" not in existing_uniques:
            op.create_unique_constraint("uq_users_sub", "users", ["sub"])
        return

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("sub", sa.String(length=255), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column(
            "alert_prefs",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
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
        sa.UniqueConstraint("sub", name="uq_users_sub"),
    )
    op.create_index("ix_users_sub", "users", ["sub"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_sub", table_name="users")
    op.drop_table("users")
