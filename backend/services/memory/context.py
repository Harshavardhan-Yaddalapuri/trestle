"""Build a MemoryContext for prompt injection from a list of AgentMemory rows."""
from __future__ import annotations

from datetime import datetime, timezone

from backend.db.models.memory import AgentMemory
from backend.schemas.memory import MemoryContext

_MAX_OBSERVATIONS = 5
_MAX_CORRECTIONS = 5


def build_memory_context(memories: list[AgentMemory]) -> MemoryContext:
    """Filter, group, and cap memories into a MemoryContext.

    - Expired and soft-deleted memories are excluded.
    - preferences and constraints: all active (durable).
    - observations and corrections: last N by created_at DESC.
    """
    now = datetime.now(timezone.utc)

    def _active(m: AgentMemory) -> bool:
        if m.deleted_at is not None:
            return False
        if m.expires_at is not None and m.expires_at <= now:
            return False
        return True

    active = [m for m in memories if _active(m)]

    preferences = [m.content for m in active if m.kind == "preference"]
    constraints = [m.content for m in active if m.kind == "constraint"]

    observations_sorted = sorted(
        [m for m in active if m.kind == "observation"],
        key=lambda m: m.created_at,
        reverse=True,
    )
    corrections_sorted = sorted(
        [m for m in active if m.kind == "correction"],
        key=lambda m: m.created_at,
        reverse=True,
    )

    return MemoryContext(
        preferences=preferences,
        constraints=constraints,
        recent_observations=[m.content for m in observations_sorted[:_MAX_OBSERVATIONS]],
        corrections=[m.content for m in corrections_sorted[:_MAX_CORRECTIONS]],
    )
