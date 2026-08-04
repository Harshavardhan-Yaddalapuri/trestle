"""Shared vocabulary for classifying discovered founder events.

Every source adapter maps free-text event copy onto the same tag vocabulary so
that `services.events.matching` can score events from different providers
against a single founder profile.

Phrases are matched on a word-prefix boundary: `investor` matches "investors"
but `ai` will not match "Chennai" or "Ukraine". Short tokens (<= 3 characters)
require a full word match because they are too ambiguous to prefix-match.
"""
from __future__ import annotations

import html
import re
from datetime import UTC, datetime
from typing import Any

_HTML_TAG_RE = re.compile(r"<[^>]+>")

# Tokens at or below this length must match a whole word rather than a prefix.
_WHOLE_WORD_MAX_LEN = 3

INDUSTRY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ai": ("ai", "artificial intelligence", "machine learning", "llm"),
    "biotech": ("biotech", "life sciences", "pharma", "wet lab"),
    "climate": ("climate", "cleantech", "decarbonization", "energy transition"),
    "hardware": ("hardware", "manufacturing", "iot", "robotics"),
    "fintech": ("fintech", "payments", "banking", "financial"),
    "healthcare": ("healthcare", "digital health", "medtech", "health"),
    "saas": ("saas", "software"),
}

STAGE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "idea": ("idea stage", "first-time founder"),
    "pre_seed": ("pre-seed", "pre seed"),
    "seed": ("seed stage", "seed founders", "seed startup"),
    "series_a": ("series a",),
    "growth": ("growth stage", "series b", "series c"),
}

BENEFIT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "networking": ("networking", "mixer", "community"),
    "investor_access": ("investor", "vc", "fundraising", "demo day", "pitch"),
    "customer_discovery": ("customer", "go-to-market", "gtm", "sales"),
    "partnerships": ("partnership", "corporate", "business development"),
    "hiring": ("hiring", "talent", "recruiting", "job fair"),
    "media_visibility": ("media", "press", "pr"),
    "lab_access": ("lab", "wet lab", "research park"),
}

ATTENDEE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "founders": ("founder", "startup", "entrepreneur"),
    "investors": ("investor", "vc", "angel"),
    "developers": ("developer", "engineer"),
    "students": ("student", "university"),
}

HIGH_QUALITY_HOST_PATTERNS: tuple[str, ...] = (
    "techstars",
    "ycombinator",
    "startup grind",
    "mit",
    "stanford",
    "berkeley",
    "google for startups",
    "aws startups",
)

HIGH_QUALITY_HOST_SCORE = 0.85
KNOWN_HOST_SCORE = 0.55
UNKNOWN_HOST_SCORE = 0.5


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    escaped = re.escape(phrase)
    suffix = r"\b" if len(phrase) <= _WHOLE_WORD_MAX_LEN else ""
    return re.compile(rf"\b{escaped}{suffix}", re.IGNORECASE)


def _compile(mapping: dict[str, tuple[str, ...]]) -> dict[str, tuple[re.Pattern[str], ...]]:
    return {
        tag: tuple(_phrase_pattern(phrase) for phrase in phrases)
        for tag, phrases in mapping.items()
    }


_COMPILED_KEYWORDS: dict[int, dict[str, tuple[re.Pattern[str], ...]]] = {
    id(INDUSTRY_KEYWORDS): _compile(INDUSTRY_KEYWORDS),
    id(STAGE_KEYWORDS): _compile(STAGE_KEYWORDS),
    id(BENEFIT_KEYWORDS): _compile(BENEFIT_KEYWORDS),
    id(ATTENDEE_KEYWORDS): _compile(ATTENDEE_KEYWORDS),
}


def normalize_text(value: Any) -> str:
    """Strip HTML markup, unescape entities and collapse whitespace."""
    if not value:
        return ""
    text = _HTML_TAG_RE.sub(" ", str(value))
    text = html.unescape(text)
    return " ".join(text.split())


def extract_tags(text: str, mapping: dict[str, tuple[str, ...]]) -> list[str]:
    """Return every tag in `mapping` whose phrases appear in `text`."""
    if not text:
        return []
    compiled = _COMPILED_KEYWORDS.get(id(mapping)) or _compile(mapping)
    return [
        tag
        for tag, patterns in compiled.items()
        if any(pattern.search(text) for pattern in patterns)
    ]


def host_quality_score(host_name: str | None) -> float:
    """Confidence that a host runs events worth a founder's time."""
    if not host_name:
        return UNKNOWN_HOST_SCORE
    haystack = host_name.lower()
    if any(pattern in haystack for pattern in HIGH_QUALITY_HOST_PATTERNS):
        return HIGH_QUALITY_HOST_SCORE
    return KNOWN_HOST_SCORE


def parse_iso_datetime(value: Any) -> datetime | None:
    """Parse an ISO-8601 date or datetime into an aware UTC datetime."""
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def merge_tags(*tag_groups: list[str] | tuple[str, ...]) -> list[str]:
    """Union tag groups while preserving first-seen order."""
    merged: list[str] = []
    for group in tag_groups:
        for tag in group:
            if tag not in merged:
                merged.append(tag)
    return merged
