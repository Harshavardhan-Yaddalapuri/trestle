"""Validation and conservative acceptance rules for generic extraction."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.services.events.generic.types import ExtractedEvent, ValidationResult

_AUTO_ACCEPT_CONFIDENCE = .85
_MAX_TITLE_LENGTH = 300


def validate(candidate: ExtractedEvent, *, extraction_method: str) -> ValidationResult:
    errors: list[str] = []
    if not candidate.name or not candidate.name.strip():
        errors.append("missing_name")
    elif len(candidate.name) > _MAX_TITLE_LENGTH:
        errors.append("name_too_long")
    if candidate.starts_at is None:
        errors.append("missing_starts_at")
    elif candidate.starts_at > datetime.now(UTC) + timedelta(days=3650):
        errors.append("implausible_starts_at")
    if candidate.ends_at and candidate.starts_at and candidate.ends_at < candidate.starts_at:
        errors.append("ends_before_start")
    if candidate.price_usd_cents is not None and candidate.price_usd_cents > 100_000_000:
        errors.append("implausible_price")
    confidence = _minimum_required_confidence(candidate, extraction_method)
    if errors:
        return ValidationResult(status="rejected", errors=errors, confidence=confidence)
    if confidence >= _AUTO_ACCEPT_CONFIDENCE:
        return ValidationResult(status="accepted", confidence=confidence)
    return ValidationResult(status="pending_review", confidence=confidence)


def _minimum_required_confidence(candidate: ExtractedEvent, method: str) -> float:
    """Never infer certainty: omitted confidence is conservative except known feeds."""
    defaults = {"custom_adapter": .99, "api": .98, "ics": .99, "rss": .7, "jsonld": .92, "html": .6, "browser": .7, "llm": .55}
    fallback = defaults.get(method, .5)
    return min(candidate.field_confidences.get("name", fallback), candidate.field_confidences.get("starts_at", fallback))
