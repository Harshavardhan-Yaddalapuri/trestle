"""alert_deliveries, alert_preferences, unsubscribe_token

Revision ID: 0012_alerts
Revises: 0011_auth
Create Date: 2026-06-03

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_alerts"
down_revision: Union[str, None] = "0011_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users: alert_preferences + alert_unsubscribe_token ────────────────────
    op.add_column(
        "users",
        sa.Column(
            "alert_preferences",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.add_column(
        "users",
        sa.Column("alert_unsubscribe_token", sa.Text(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_users_alert_unsubscribe_token", "users", ["alert_unsubscribe_token"]
    )

    # ── grants: last_alerted_to_users_at ─────────────────────────────────────
    op.add_column(
        "grants",
        sa.Column("last_alerted_to_users_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_grants_alert_scan",
        "grants",
        ["status", "created_at", "last_alerted_to_users_at"],
    )

    # ── alert_deliveries ─────────────────────────────────────────────────────
    op.create_table(
        "alert_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("alert_kind", sa.Text(), nullable=False),
        sa.Column("grant_id", sa.Uuid(), nullable=True),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'queued'"),
        ),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            sa.JSON(),
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
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "alert_kind IN ('deadline_reminder','new_grant_match','check_in')",
            name="ck_alert_deliveries_alert_kind_valid",
        ),
        sa.CheckConstraint(
            "status IN ('queued','sent','failed','suppressed')",
            name="ck_alert_deliveries_status_valid",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_alert_deliveries_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["grant_id"],
            ["grants.id"],
            ondelete="SET NULL",
            name="fk_alert_deliveries_grant_id_grants",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_alert_deliveries"),
        sa.UniqueConstraint(
            "user_id", "alert_kind", "key",
            name="uq_alert_deliveries_user_kind_key",
        ),
    )
    op.create_index("ix_alert_deliveries_user_id", "alert_deliveries", ["user_id"])
    op.create_index(
        "ix_alert_deliveries_user_kind_status",
        "alert_deliveries",
        ["user_id", "alert_kind", "status"],
    )
    op.create_index(
        "ix_alert_deliveries_status_created",
        "alert_deliveries",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_alert_deliveries_status_created", table_name="alert_deliveries")
    op.drop_index("ix_alert_deliveries_user_kind_status", table_name="alert_deliveries")
    op.drop_index("ix_alert_deliveries_user_id", table_name="alert_deliveries")
    op.drop_table("alert_deliveries")

    op.drop_index("ix_grants_alert_scan", table_name="grants")
    op.drop_column("grants", "last_alerted_to_users_at")

    op.drop_constraint("uq_users_alert_unsubscribe_token", "users", type_="unique")
    op.drop_column("users", "alert_unsubscribe_token")
    op.drop_column("users", "alert_preferences")
