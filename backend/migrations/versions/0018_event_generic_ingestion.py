"""generic event discovery runs, candidates, and provenance

Revision ID: 0018_event_generic_ingestion
Revises: 0017_events_tag_arrays
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0018_event_generic_ingestion"
down_revision = "0017_events_tag_arrays"
branch_labels = None
depends_on = None


def _json_type(bind):
    return postgresql.JSONB() if bind.dialect.name == "postgresql" else sa.JSON()


def upgrade() -> None:
    bind = op.get_bind()
    json_type = _json_type(bind)
    op.create_table(
        "event_discovery_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("triggered_by", sa.Text(), nullable=False),
        sa.Column("strategy", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("records_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_accepted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_pending_review", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_duplicates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text()),
        sa.Column("diagnostics", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.CheckConstraint("triggered_by IN ('manual','schedule')", name="ck_event_discovery_runs_triggered_by"),
    )
    op.create_index("ix_event_discovery_runs_source_started", "event_discovery_runs", ["source_url", "started_at"])
    op.create_table(
        "event_candidates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("event_discovery_runs.id"), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_identifier", sa.Text()),
        sa.Column("extraction_method", sa.Text(), nullable=False),
        sa.Column("normalized_data", json_type, nullable=False),
        sa.Column("field_confidences", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("evidence", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("raw_payload", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("content_hash", sa.Text()),
        sa.Column("review_status", sa.Text(), nullable=False, server_default="pending_review"),
        sa.Column("validation_errors", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("duplicate_event_id", sa.Uuid(), sa.ForeignKey("events.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("review_status IN ('accepted','pending_review','rejected','duplicate')", name="ck_event_candidates_review_status"),
    )
    op.create_index("ix_event_candidates_run_id", "event_candidates", ["run_id"])
    op.create_index("ix_event_candidates_status_created", "event_candidates", ["review_status", "created_at"])
    op.create_table(
        "event_provenance",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("event_candidates.id")),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_identifier", sa.Text()),
        sa.Column("extraction_method", sa.Text(), nullable=False),
        sa.Column("field_confidences", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("evidence", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("raw_payload", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("content_hash", sa.Text()),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("event_id", "source_url", "source_identifier", name="uq_event_provenance_event_source"),
    )
    op.create_index("ix_event_provenance_event_id", "event_provenance", ["event_id"])
    op.create_index("ix_event_provenance_source_identifier", "event_provenance", ["source_url", "source_identifier"])


def downgrade() -> None:
    op.drop_table("event_provenance")
    op.drop_table("event_candidates")
    op.drop_table("event_discovery_runs")
