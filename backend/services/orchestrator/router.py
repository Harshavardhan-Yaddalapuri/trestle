from __future__ import annotations

from typing import Callable

from backend.schemas.intent import IntentLabel
from backend.services.orchestrator.handlers import (
    handle_correction,
    handle_deep_dive,
    handle_discover,
    handle_greet,
    handle_lifecycle_action,
    handle_match_request,
    handle_out_of_scope,
    handle_profile_query,
    handle_profile_update,
    handle_smalltalk,
    handle_unknown,
)

# Intents that mutate state — require higher confidence to act
_DESTRUCTIVE_INTENTS: frozenset[IntentLabel] = frozenset({
    "profile_update",
    "lifecycle_action",
    "correction",
})

_CONFIDENCE_FLOOR = 0.4        # below this → always handle_unknown
_DESTRUCTIVE_THRESHOLD = 0.6   # destructive intents need at least this

INTENT_HANDLERS: dict[IntentLabel, Callable] = {
    "greet": handle_greet,
    "discover": handle_discover,
    "match_request": handle_match_request,
    "deep_dive": handle_deep_dive,
    "profile_update": handle_profile_update,
    "profile_query": handle_profile_query,
    "lifecycle_action": handle_lifecycle_action,
    "smalltalk": handle_smalltalk,
    "out_of_scope": handle_out_of_scope,
    "correction": handle_correction,
    "unknown": handle_unknown,
}


def route(intent_result) -> Callable:
    """Return the handler callable for a given IntentResult."""
    confidence = intent_result.confidence
    label = intent_result.intent

    if confidence < _CONFIDENCE_FLOOR:
        return handle_unknown

    if label in _DESTRUCTIVE_INTENTS and confidence < _DESTRUCTIVE_THRESHOLD:
        return handle_unknown

    return INTENT_HANDLERS.get(label, handle_unknown)
