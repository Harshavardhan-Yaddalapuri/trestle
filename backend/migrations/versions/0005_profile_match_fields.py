"""profile match fields

Revision ID: 0005_profile_match_fields
Revises: 0004_grants
Create Date: 2026-05-28

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_profile_match_fields"
down_revision: Union[str, None] = "0004_grants"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("team_size", sa.Integer(), nullable=True))
    op.add_column("profiles", sa.Column("has_technical_cofounder", sa.Boolean(), nullable=True))
    op.add_column("profiles", sa.Column("funding_raised_usd_cents", sa.BigInteger(), nullable=True))
    op.add_column("profiles", sa.Column("funding_target_usd_cents", sa.BigInteger(), nullable=True))
    op.add_column("profiles", sa.Column("incorporated", sa.Boolean(), nullable=True))
    op.add_column("profiles", sa.Column("incorporation_country", sa.Text(), nullable=True))
    op.add_column("profiles", sa.Column("incorporation_state", sa.Text(), nullable=True))
    op.add_column(
        "profiles",
        sa.Column(
            "regulatory_status",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("profiles", "regulatory_status")
    op.drop_column("profiles", "incorporation_state")
    op.drop_column("profiles", "incorporation_country")
    op.drop_column("profiles", "incorporated")
    op.drop_column("profiles", "funding_target_usd_cents")
    op.drop_column("profiles", "funding_raised_usd_cents")
    op.drop_column("profiles", "has_technical_cofounder")
    op.drop_column("profiles", "team_size")
