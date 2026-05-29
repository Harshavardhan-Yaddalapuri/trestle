"""grants table

Revision ID: 0004_grants
Revises: 0003_profiles
Create Date: 2026-05-28

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0004_grants"
down_revision: Union[str, None] = "0003_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("application_url", sa.Text(), nullable=True),
        sa.Column("amount_min", sa.Integer(), nullable=True),
        sa.Column("amount_max", sa.Integer(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column(
            "rolling",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "stage",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "industry",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "location",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "eligibility",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("provider_name", sa.Text(), nullable=False),
        sa.Column("provider_type", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "source_status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'unknown'"),
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
        sa.CheckConstraint(
            "type IN ('grant','contest','accelerator','fellowship','other')",
            name="ck_grants_type_valid",
        ),
        sa.CheckConstraint(
            "provider_type IS NULL OR provider_type IN ('government','foundation','corporate','vc','accelerator','other')",
            name="ck_grants_provider_type_valid",
        ),
        sa.CheckConstraint(
            "status IN ('active','expired','archived')",
            name="ck_grants_status_valid",
        ),
        sa.CheckConstraint(
            "source_status IN ('unknown','ok','redirect','gone','error')",
            name="ck_grants_source_status_valid",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_grants"),
        sa.UniqueConstraint("source_id", name="uq_grants_source_id"),
    )
    op.create_index("ix_grants_source_id", "grants", ["source_id"], unique=True)
    op.create_index("ix_grants_status", "grants", ["status"])
    op.create_index("ix_grants_deadline", "grants", ["deadline"])
    op.create_index(
        "ix_grants_eligibility_gin",
        "grants",
        ["eligibility"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_grants_eligibility_gin", table_name="grants")
    op.drop_index("ix_grants_deadline", table_name="grants")
    op.drop_index("ix_grants_status", table_name="grants")
    op.drop_index("ix_grants_source_id", table_name="grants")
    op.drop_table("grants")
