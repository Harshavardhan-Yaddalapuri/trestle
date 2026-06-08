from __future__ import annotations

from backend.core.errors import ValidationError
from backend.services.lifecycle.states import LIFECYCLE_STATUSES, TERMINAL_STATUSES

LEGAL_TRANSITIONS: dict[str, frozenset[str]] = {
    "interested": frozenset({"researching", "drafting", "withdrawn", "abandoned"}),
    "researching": frozenset({"drafting", "interested", "withdrawn", "abandoned"}),
    "drafting": frozenset({"submitted", "researching", "withdrawn", "abandoned"}),
    "submitted": frozenset({"under_review", "awarded", "rejected", "withdrawn"}),
    "under_review": frozenset({"awarded", "rejected", "withdrawn"}),
    "awarded": frozenset(),
    "rejected": frozenset({"researching"}),
    "withdrawn": frozenset({"interested"}),
    "abandoned": frozenset({"interested"}),
}

# For automated transitions: submitted→under_review or any non-terminal→abandoned.
# Step 16 will enforce this; validate_transition checks it when transition_kind="automated".


def validate_transition(from_status: str, to_status: str, transition_kind: str) -> None:
    """Raise ValidationError if the requested transition is not legal."""
    if to_status not in LEGAL_TRANSITIONS.get(from_status, frozenset()):
        raise ValidationError(
            f"Cannot transition from '{from_status}' to '{to_status}'",
            code="invalid_lifecycle_transition",
        )

    if transition_kind == "automated":
        is_valid_automated = (from_status == "submitted" and to_status == "under_review") or (
            from_status not in TERMINAL_STATUSES and to_status == "abandoned"
        )
        if not is_valid_automated:
            raise ValidationError(
                f"Automated transition from '{from_status}' to '{to_status}' is not permitted",
                code="invalid_lifecycle_transition",
            )
