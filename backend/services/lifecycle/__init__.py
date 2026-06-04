from backend.services.lifecycle.states import LIFECYCLE_STATUSES, TERMINAL_STATUSES
from backend.services.lifecycle.transitions import validate_transition


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATUSES


__all__ = [
    "LIFECYCLE_STATUSES",
    "TERMINAL_STATUSES",
    "validate_transition",
    "is_terminal",
]
