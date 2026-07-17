"""align events tag columns to varchar[] for postgres filtering

Revision ID: 0017_events_tag_arrays
Revises: 0016_events
Create Date: 2026-07-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017_events_tag_arrays"
down_revision: Union[str, None] = "0016_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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

    for column_name in ("industry_tags", "stage_tags", "benefit_tags", "attendee_types"):
        if _is_array_column(bind, "events", column_name):
            continue
        tmp_name = f"{column_name}__tmp"
        op.add_column("events", sa.Column(tmp_name, postgresql.ARRAY(sa.String()), nullable=True))
        op.execute(
            sa.text(
                f"""
                UPDATE events
                SET {tmp_name} = ARRAY(SELECT jsonb_array_elements_text({column_name}))
                WHERE {column_name} IS NOT NULL
                """
            )
        )
        op.drop_column("events", column_name)
        op.alter_column("events", tmp_name, new_column_name=column_name)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for column_name in ("industry_tags", "stage_tags", "benefit_tags", "attendee_types"):
        if not _is_array_column(bind, "events", column_name):
            continue
        tmp_name = f"{column_name}__tmp"
        op.add_column("events", sa.Column(tmp_name, postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        op.execute(
            sa.text(
                f"""
                UPDATE events
                SET {tmp_name} = to_jsonb({column_name})
                WHERE {column_name} IS NOT NULL
                """
            )
        )
        op.drop_column("events", column_name)
        op.alter_column("events", tmp_name, new_column_name=column_name)
