from __future__ import annotations

import re
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.profile import Profile
from backend.schemas.intent import ExtractedEntities
from backend.schemas.profile import COMPANY_STAGES

CONFIDENCE_THRESHOLD = 0.7

_US_STATE_RE = re.compile(r"^US-([A-Z]{2})$", re.IGNORECASE)
_COUNTRY_CODE_RE = re.compile(r"^[A-Z]{2}$", re.IGNORECASE)

# Stage alias normalization
_STAGE_ALIASES: dict[str, str] = {
    "pre-seed": "pre_seed",
    "pre_seed": "pre_seed",
    "preseed": "pre_seed",
    "seed": "seed",
    "series-a": "series_a",
    "series_a": "series_a",
    "series a": "series_a",
    "series-b": "series_b_plus",
    "series_b_plus": "series_b_plus",
    "series b": "series_b_plus",
    "idea": "idea",
    "other": "other",
}


def _normalize_stage(raw: str) -> str | None:
    lowered = raw.lower().strip()
    return _STAGE_ALIASES.get(lowered) or (raw if raw in COMPANY_STAGES else None)


def _parse_location(location: str) -> dict[str, str]:
    m = _US_STATE_RE.match(location)
    if m:
        return {"incorporation_country": "US", "incorporation_state": m.group(1).upper()}
    if _COUNTRY_CODE_RE.match(location):
        return {"incorporation_country": location.upper()}
    return {"location": location}


async def apply_entities_to_profile(
    session_id: str,
    entities: ExtractedEntities,
    confidence: float,
    db: AsyncSession,
) -> list[str]:
    """Apply extracted entities to the profile. Returns field names actually updated.

    Only runs when confidence >= CONFIDENCE_THRESHOLD. Idempotent — skips no-op updates.
    """
    if confidence < CONFIDENCE_THRESHOLD:
        return []

    result = await db.execute(sa.select(Profile).where(Profile.session_id == session_id))
    profile = result.scalar_one_or_none()

    updates: dict[str, object] = {}

    # Stage
    if entities.stage:
        normalized = _normalize_stage(entities.stage)
        if normalized and (profile is None or profile.company_stage != normalized):
            updates["company_stage"] = normalized

    # Location → parsed fields
    if entities.location:
        parsed = _parse_location(entities.location)
        for field_name, value in parsed.items():
            current = getattr(profile, field_name, None) if profile else None
            if current != value:
                updates[field_name] = value

    # Industries (append + dedup, preserve order)
    if entities.industries:
        current = list(profile.industry or []) if profile else []
        additions = [i for i in entities.industries if i not in current]
        if additions:
            updates["industry"] = current + additions

    # Funding raised
    if entities.funding_amount_usd_cents is not None:
        current = profile.funding_raised_usd_cents if profile else None
        if current != entities.funding_amount_usd_cents:
            updates["funding_raised_usd_cents"] = entities.funding_amount_usd_cents

    # Team size
    if entities.team_size is not None and entities.team_size >= 1:
        current = profile.team_size if profile else None
        if current != entities.team_size:
            updates["team_size"] = entities.team_size

    if not updates:
        return []

    now = datetime.now(timezone.utc)
    if profile is None:
        db.add(Profile(session_id=session_id, created_at=now, updated_at=now, **updates))
    else:
        for field_name, value in updates.items():
            setattr(profile, field_name, value)
        profile.updated_at = now

    await db.commit()
    return list(updates.keys())
