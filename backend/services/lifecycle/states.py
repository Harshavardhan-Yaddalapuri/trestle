from __future__ import annotations

LIFECYCLE_STATUSES = (
    "interested",
    "researching",
    "drafting",
    "submitted",
    "under_review",
    "awarded",
    "rejected",
    "withdrawn",
    "abandoned",
)

TERMINAL_STATUSES: frozenset[str] = frozenset(
    {"awarded", "rejected", "withdrawn", "abandoned"}
)
