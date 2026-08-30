"""align profiles.industry to varchar[] for postgres StringList type

Revision ID: 0019_profiles_industry_array
Revises: 0018_event_generic_ingestion
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0019_profiles_industry_array"
down_revision = "0018_event_generic_ingestion"
branch_labels = None
depends_on = None


def _is_array_column(bind, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    for col in inspector.get_columns(table_name):
        if col["name"] == column_name:
            return isinstance(col["type"], postgresql.ARRAY)
    return False


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    if _is_array_column(bind, "profiles", "industry"):
        return

    op.add_column(
        "profiles",
        sa.Column("industry__tmp", postgresql.ARRAY(sa.String()), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE profiles
            SET industry__tmp = ARRAY(SELECT jsonb_array_elements_text(industry::jsonb))
            WHERE industry IS NOT NULL
            """
        )
    )
    op.drop_column("profiles", "industry")
    op.alter_column("profiles", "industry__tmp", new_column_name="industry")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    if not _is_array_column(bind, "profiles", "industry"):
        return

    op.add_column(
        "profiles",
        sa.Column("industry__tmp", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE profiles
            SET industry__tmp = to_jsonb(industry)
            WHERE industry IS NOT NULL
            """
        )
    )
    op.drop_column("profiles", "industry")
    op.alter_column("profiles", "industry__tmp", new_column_name="industry")
