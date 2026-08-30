"""Events discovery: fetch configured sources, then upsert what was found.

Per-source parsing lives in `services.events.adapters`; this module only walks
the configured source URLs, delegates to the adapter that claims each one, and
persists the results.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logging import get_logger
from backend.db.models.event import Event
from backend.services.events.adapters.registry import get_adapter_for_source_url
from backend.services.events.parser import DiscoveredEvent

logger = get_logger(__name__)

__all__ = [
    "DiscoveredEvent",
    "discover_events_from_web",
    "upsert_discovered_events",
]


async def discover_events_from_web(settings: Any) -> list[DiscoveredEvent]:
    """Scan every configured source URL and return de-duplicated events."""
    urls = settings.EVENT_SOURCE_URLS_LIST
    if not urls:
        return []

    discovered: dict[str, DiscoveredEvent] = {}
    async with httpx.AsyncClient(
        headers={"User-Agent": settings.INGEST_USER_AGENT},
        timeout=settings.EVENTS_HTTP_TIMEOUT_SECONDS,
        follow_redirects=True,
    ) as client:
        for source_url in urls:
            adapter = get_adapter_for_source_url(source_url)
            try:
                events = await adapter.discover(client, settings, source_url)
            except httpx.HTTPError:
                logger.warning(
                    "events_source_fetch_failed",
                    source_url=source_url,
                    adapter=adapter.source_name,
                )
                continue
            except Exception:
                logger.exception(
                    "events_source_adapter_failed",
                    source_url=source_url,
                    adapter=adapter.source_name,
                )
                continue

            logger.info(
                "events_source_scanned",
                source_url=source_url,
                adapter=adapter.source_name,
                discovered=len(events),
            )
            for event in events:
                discovered[event.source_id] = event

    return list(discovered.values())


def _to_db_dict(record: DiscoveredEvent, fetched_at: datetime) -> dict[str, Any]:
    return {
        "source_id": record.source_id,
        "source": record.source,
        "source_payload": record.source_payload,
        "source_fetched_at": fetched_at,
        "name": record.name,
        "description": record.description,
        "url": record.url,
        "host_name": record.host_name,
        "starts_at": record.starts_at,
        "ends_at": record.ends_at,
        "timezone": record.timezone,
        "is_virtual": record.is_virtual,
        "location_text": record.location_text,
        "city": record.city,
        "region": record.region,
        "country": record.country,
        "industry_tags": record.industry_tags or None,
        "stage_tags": record.stage_tags or None,
        "benefit_tags": record.benefit_tags or None,
        "attendee_types": record.attendee_types or None,
        "cost_usd_cents": record.cost_usd_cents,
        "application_required": record.application_required,
        "host_quality_score": record.host_quality_score,
        "status": record.status,
    }


async def upsert_discovered_events(
    session: AsyncSession,
    records: list[DiscoveredEvent],
    fetched_at: datetime,
) -> tuple[int, int]:
    """Insert new events and refresh existing ones, keyed on source_id."""
    if not records:
        return 0, 0

    source_ids = [r.source_id for r in records]
    result = await session.execute(
        sa.select(Event.source_id).where(Event.source_id.in_(source_ids))
    )
    existing_ids = {row.source_id for row in result}

    inserted = 0
    updated = 0
    now = datetime.now(UTC)

    conn = await session.connection()
    is_postgres = conn.dialect.name == "postgresql"
    if is_postgres:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        for record in records:
            data = _to_db_dict(record, fetched_at)
            stmt = pg_insert(Event).values(id=uuid.uuid4(), created_at=now, updated_at=now, **data)
            update_fields = {k: v for k, v in data.items() if k != "source_id"}
            stmt = stmt.on_conflict_do_update(
                index_elements=["source_id"],
                set_={**update_fields, "updated_at": now},
            )
            await session.execute(stmt)
            if record.source_id in existing_ids:
                updated += 1
            else:
                inserted += 1
    else:
        for record in records:
            data = _to_db_dict(record, fetched_at)
            if record.source_id in existing_ids:
                update_fields = {k: v for k, v in data.items() if k != "source_id"}
                await session.execute(
                    sa.update(Event)
                    .where(Event.source_id == record.source_id)
                    .values(**update_fields, updated_at=now)
                )
                updated += 1
            else:
                session.add(Event(id=uuid.uuid4(), created_at=now, updated_at=now, **data))
                inserted += 1

    await session.commit()
    return inserted, updated
