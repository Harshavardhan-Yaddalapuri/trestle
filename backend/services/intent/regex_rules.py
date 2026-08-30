"""Fast regex/keyword classification rules. Compiled once at import time."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from backend.schemas.intent import ExtractedEntities, IntentLabel

_GRANT_REF_PATTERN = re.compile(
    r"\b([A-Z]{2,}(?:\s+[A-Z]+)*|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
)


def _no_entities(text: str) -> ExtractedEntities:
    return ExtractedEntities()


def _extract_grant_refs(text: str) -> ExtractedEntities:
    refs = _GRANT_REF_PATTERN.findall(text)
    return ExtractedEntities(grant_refs=refs)


def _lifecycle_track(text: str) -> ExtractedEntities:
    refs = _GRANT_REF_PATTERN.findall(text)
    return ExtractedEntities(action="track", grant_refs=refs)


def _lifecycle_untrack(text: str) -> ExtractedEntities:
    refs = _GRANT_REF_PATTERN.findall(text)
    return ExtractedEntities(action="untrack", grant_refs=refs)


def _lifecycle_dismiss(text: str) -> ExtractedEntities:
    refs = _GRANT_REF_PATTERN.findall(text)
    return ExtractedEntities(action="dismiss", grant_refs=refs)


@dataclass
class RegexRule:
    pattern: re.Pattern[str]
    intent: IntentLabel
    confidence: float
    entity_extractor: Callable[[str], ExtractedEntities] = field(
        default=_no_entities
    )


RULES: list[RegexRule] = [
    RegexRule(
        pattern=re.compile(
            r"^\s*(hi|hello|hey|yo|sup|good\s+(morning|afternoon|evening))\b",
            re.IGNORECASE,
        ),
        intent="greet",
        confidence=0.95,
    ),
    RegexRule(
        pattern=re.compile(
            r"\b(find|show|recommend|suggest|match)\b.*\b(grants?|funding|opportunities)\b",
            re.IGNORECASE,
        ),
        intent="match_request",
        confidence=0.85,
    ),
    RegexRule(
        pattern=re.compile(
            r"\b(events?|conferences?|meetups?|summits?|workshops?)\b.*"
            r"\b(attend|find|discover|recommend|looking)\b"
            r"|\b(looking|find|recommend|discover)\b.*"
            r"\b(events?|conferences?|meetups?|summits?|workshops?)\b",
            re.IGNORECASE,
        ),
        intent="event_request",
        confidence=0.9,
    ),
    RegexRule(
        pattern=re.compile(
            r"\b(what do you (know|have)|my profile|what.*on file)\b",
            re.IGNORECASE,
        ),
        intent="profile_query",
        confidence=0.85,
    ),
    RegexRule(
        pattern=re.compile(
            r"\b(track|save|bookmark)\b",
            re.IGNORECASE,
        ),
        intent="lifecycle_action",
        confidence=0.7,
        entity_extractor=_lifecycle_track,
    ),
    RegexRule(
        pattern=re.compile(
            r"\b(untrack|unsave|remove)\b",
            re.IGNORECASE,
        ),
        intent="lifecycle_action",
        confidence=0.7,
        entity_extractor=_lifecycle_untrack,
    ),
    RegexRule(
        pattern=re.compile(
            r"\b(dismiss|hide|not interested|skip)\b",
            re.IGNORECASE,
        ),
        intent="lifecycle_action",
        confidence=0.7,
        entity_extractor=_lifecycle_dismiss,
    ),
    RegexRule(
        pattern=re.compile(
            r"^\s*(thanks?|thank you|ty|cool|nice|👍|🙏)\b",
            re.IGNORECASE,
        ),
        intent="smalltalk",
        confidence=0.9,
    ),
    RegexRule(
        pattern=re.compile(
            r"\b(weather|poem|joke|recipe|code|programming)\b",
            re.IGNORECASE,
        ),
        intent="out_of_scope",
        confidence=0.6,
    ),
]
