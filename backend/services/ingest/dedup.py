"""Cross-source deduplication for ingested grants.

run_dedup_pass — called after each ingest sweep. Marks duplicate grants via
is_duplicate_of so they are excluded from matching and list endpoints.

SBIR.gov wins as canonical for SBIR/STTR opportunities (richer metadata).
Grants.gov wins otherwise.

Dialect note: JSON field extraction differs between SQLite and Postgres.
Uses func.json_extract for SQLite and col[key].astext for Postgres JSONB.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import sqlalchemy as sa
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logging import get_logger
from backend.db.models.grant import Grant

logger = get_logger(__name__)

_TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "ref", "referrer",
})


class DedupResult(BaseModel):
    source: str
    grants_checked: int
    duplicates_found: int
    sbirgov_canonical_wins: int
    grantsgov_canonical_wins: int


def _normalize_url(url: str) -> str:
    """Strip tracking params, lowercase host, strip trailing slash."""
    try:
        parsed = urlparse(url.strip())
        qs = {
            k: v
            for k, v in parse_qs(parsed.query).items()
            if k not in _TRACKING_PARAMS
        }
        query = urlencode({k: v[0] for k, v in sorted(qs.items())})
        return urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            "",
            query,
            "",
        ))
    except Exception:
        return url.lower().rstrip("/")


def _json_text_eq(
    col: sa.Column,
    key: str,
    value: str,
    is_postgres: bool,
) -> sa.ColumnElement:
    """WHERE col->key == value, dialect-aware."""
    if is_postgres:
        return col[key].astext == value
    return sa.func.json_extract(col, f"$.{key}") == value


async def run_dedup_pass(
    session: AsyncSession,
    source: str,
    ingested_source_ids: set[str],
) -> DedupResult:
    """Evaluate dedup for all just-ingested source_ids.

    Marks non-canonical rows with is_duplicate_of, dedup_match_kind,
    dedup_checked_at. Sets dedup_checked_at on all evaluated rows.
    """
    if not ingested_source_ids:
        return DedupResult(
            source=source,
            grants_checked=0,
            duplicates_found=0,
            sbirgov_canonical_wins=0,
            grantsgov_canonical_wins=0,
        )

    conn = await session.connection()
    is_postgres = conn.dialect.name == "postgresql"

    grants_checked = 0
    duplicates_found = 0
    sbirgov_canonical_wins = 0
    grantsgov_canonical_wins = 0
    now = datetime.now(timezone.utc)

    for source_id in ingested_source_ids:
        # Load the grant
        result = await session.execute(
            sa.select(Grant).where(Grant.source_id == source_id)
        )
        grant = result.scalar_one_or_none()
        if grant is None:
            continue

        # Skip already-evaluated or already-marked rows
        if grant.is_duplicate_of is not None or grant.dedup_checked_at is not None:
            continue

        grants_checked += 1

        canonical_id, match_kind = await _find_duplicate(
            session, grant, source, is_postgres
        )

        if canonical_id is not None and match_kind is not None:
            # Determine canonical side and non-canonical row to mark
            if source == "sbirgov":
                # sbirgov is canonical; mark the grantsgov row as duplicate
                dup_result = await session.execute(
                    sa.update(Grant)
                    .where(Grant.id == canonical_id)
                    .values(
                        is_duplicate_of=grant.id,
                        dedup_match_kind=match_kind,
                        dedup_checked_at=now,
                    )
                )
                # canonical_id here is the grantsgov row; sbirgov (grant) is canonical
                sbirgov_canonical_wins += 1
                duplicates_found += 1
            else:
                # source == "grantsgov"; sbirgov is still canonical
                # Mark this grantsgov row as duplicate of the sbirgov row
                await session.execute(
                    sa.update(Grant)
                    .where(Grant.id == grant.id)
                    .values(
                        is_duplicate_of=canonical_id,
                        dedup_match_kind=match_kind,
                        dedup_checked_at=now,
                    )
                )
                sbirgov_canonical_wins += 1
                duplicates_found += 1

        # Set dedup_checked_at on the current row regardless of match
        await session.execute(
            sa.update(Grant)
            .where(Grant.id == grant.id, Grant.dedup_checked_at.is_(None))
            .values(dedup_checked_at=now)
        )

    await session.commit()

    logger.info(
        "dedup_pass_complete",
        source=source,
        checked=grants_checked,
        found=duplicates_found,
    )

    return DedupResult(
        source=source,
        grants_checked=grants_checked,
        duplicates_found=duplicates_found,
        sbirgov_canonical_wins=sbirgov_canonical_wins,
        grantsgov_canonical_wins=grantsgov_canonical_wins,
    )


async def _find_duplicate(
    session: AsyncSession,
    grant: Grant,
    source: str,
    is_postgres: bool,
) -> tuple[sa.UUID | None, str | None]:
    """Try topic_number match then URL match. Returns (other_grant_id, match_kind)."""
    # ── 1. Topic-number match ────────────────────────────────────────────────
    topic_id = await _topic_number_match(session, grant, source, is_postgres)
    if topic_id is not None:
        return topic_id, "topic_number"

    # ── 2. URL-based fallback ─────────────────────────────────────────────────
    url_id = await _url_match(session, grant, source)
    if url_id is not None:
        return url_id, "url"

    return None, None


async def _topic_number_match(
    session: AsyncSession,
    grant: Grant,
    source: str,
    is_postgres: bool,
) -> sa.UUID | None:
    """Find a cross-source match by topic number."""
    if source == "sbirgov":
        # Extract this topic's number from eligibility._topic_number
        topic_num: str | None = None
        eligibility = grant.eligibility or {}
        if isinstance(eligibility, dict):
            topic_num = eligibility.get("_topic_number")
        if not topic_num:
            return None

        # Look for grantsgov row where source_payload.number matches
        stmt = sa.select(Grant.id).where(
            Grant.source == "grantsgov",
            Grant.is_duplicate_of.is_(None),
            _json_text_eq(Grant.source_payload, "number", topic_num, is_postgres),
        )
        result = await session.execute(stmt)
        row = result.first()
        return row[0] if row else None

    elif source == "grantsgov":
        # Extract opportunity number from source_payload.number
        sp = grant.source_payload or {}
        opp_number: str | None = None
        if isinstance(sp, dict):
            opp_number = sp.get("number")
        if not opp_number:
            return None

        # Look for sbirgov row where eligibility._topic_number matches
        stmt = sa.select(Grant.id).where(
            Grant.source == "sbirgov",
            Grant.is_duplicate_of.is_(None),
            _json_text_eq(Grant.eligibility, "_topic_number", opp_number, is_postgres),
        )
        result = await session.execute(stmt)
        row = result.first()
        return row[0] if row else None

    return None


async def _url_match(
    session: AsyncSession,
    grant: Grant,
    source: str,
) -> sa.UUID | None:
    """Find a cross-source match by normalized URL."""
    if not grant.url:
        return None

    normalized = _normalize_url(grant.url)
    other_source = "grantsgov" if source == "sbirgov" else "sbirgov"

    result = await session.execute(
        sa.select(Grant.id, Grant.url).where(
            Grant.source == other_source,
            Grant.is_duplicate_of.is_(None),
            Grant.url.isnot(None),
        )
    )
    rows = result.all()
    for row in rows:
        if _normalize_url(row[1]) == normalized:
            return row[0]

    return None
