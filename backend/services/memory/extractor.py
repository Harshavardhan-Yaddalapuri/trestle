"""Deterministic memory candidate extraction — regex + entity-based, no LLM."""
from __future__ import annotations

import re

from backend.schemas.intent import IntentResult
from backend.schemas.memory import MemoryIn

_PREFERENCE_RE = re.compile(
    r"\b(i\s+prefer|i\s+like|i\s+want|i\s+love|i\s+'d\s+rather|i\s+would\s+rather|"
    r"prefer(?:ably)?|rather\s+have|looking\s+for(?:\s+something)?)\b",
    re.IGNORECASE,
)

_CONSTRAINT_RE = re.compile(
    r"\b(i\s+need|we\s+need|must|have\s+to|required|require|need\s+to|"
    r"has\s+to|it\s+has\s+to|cannot|can't|won't\s+work|"
    r"before\s+\w+|\bdeadline\b|\bby\s+\w+)\b",
    re.IGNORECASE,
)


def extract_memory_candidates(message: str, intent_result: IntentResult) -> list[MemoryIn]:
    """Return a list of MemoryIn proposals for the caller to optionally persist.

    Rules (deterministic, no LLM):
    - intent == "correction" → emit one correction at confidence 1.0.
    - preference phrases → emit preference candidate.
    - constraint phrases → emit constraint candidate.
    - observation from entity extraction when intent is informational (discover/deep_dive)
      and entities carry industry/stage/location not obviously covered by profile_update.
    """
    if not message or not message.strip():
        return []

    candidates: list[MemoryIn] = []

    # Correction intent always wins and is the only output.
    if intent_result.intent == "correction":
        candidates.append(
            MemoryIn(
                kind="correction",
                content=message[:500],
                confidence=1.0,
            )
        )
        return candidates

    # Preference detection.
    if _PREFERENCE_RE.search(message):
        candidates.append(
            MemoryIn(
                kind="preference",
                content=message[:500],
                confidence=0.9,
            )
        )

    # Constraint detection.
    if _CONSTRAINT_RE.search(message):
        candidates.append(
            MemoryIn(
                kind="constraint",
                content=message[:500],
                confidence=0.85,
            )
        )

    # Observation: entities revealed in a non-profile-update turn may be worth
    # remembering (e.g. the user mentions industries mid-conversation during
    # discover/deep_dive but isn't explicitly updating their profile).
    if intent_result.intent in ("discover", "deep_dive", "smalltalk", "match_request"):
        entities = intent_result.entities
        observation_parts: list[str] = []
        if entities.industries:
            observation_parts.append(f"industries: {', '.join(entities.industries)}")
        if entities.stage:
            observation_parts.append(f"stage: {entities.stage}")
        if entities.location:
            observation_parts.append(f"location: {entities.location}")
        if entities.team_size is not None:
            observation_parts.append(f"team_size: {entities.team_size}")
        if observation_parts:
            candidates.append(
                MemoryIn(
                    kind="observation",
                    content=f"User mentioned: {'; '.join(observation_parts)}",
                    structured={
                        k: v
                        for k, v in {
                            "industries": entities.industries or None,
                            "stage": entities.stage,
                            "location": entities.location,
                            "team_size": entities.team_size,
                        }.items()
                        if v is not None
                    },
                    confidence=0.7,
                )
            )

    return candidates
