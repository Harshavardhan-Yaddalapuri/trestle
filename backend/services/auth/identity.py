"""Canonical session-id scheme for authenticated users.

Anonymous sessions use raw UUIDs (e.g. "550e8400-e29b-41d4-a716-446655440000").
Authenticated sessions use a stable prefixed string derived from the user's UUID.
This lets every existing query work unchanged: it just filters on a different
value of session_id.
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa

USER_SESSION_PREFIX = "user:"


def canonical_session_id_for_user(user_id: uuid.UUID) -> str:
    return f"{USER_SESSION_PREFIX}{user_id}"


def is_user_session_id(session_id: str) -> bool:
    return session_id.startswith(USER_SESSION_PREFIX)


def user_session_join_expr() -> sa.sql.ClauseElement:
    """ON clause for joining grant_tracks to users via the polymorphic session_id.

    Works on both SQLite (VARCHAR uuid) and PostgreSQL (UUID type).
    The '||' concatenation operator is ANSI SQL and supported by both.
    """
    return sa.text("grant_tracks.session_id = 'user:' || CAST(users.id AS TEXT)")
