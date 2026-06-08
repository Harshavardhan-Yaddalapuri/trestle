"""Shared constants and helpers for alert job functions."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

TERMINAL_STATUSES = ("awarded", "rejected", "withdrawn", "abandoned")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def prefs_enabled(prefs: dict[str, Any] | None, key: str) -> bool:
    """Return True if the alert preference key is enabled (default True if missing)."""
    if not prefs:
        return True
    val = prefs.get(key, True)
    if isinstance(val, bool):
        return val
    return str(val).lower() != "false"
