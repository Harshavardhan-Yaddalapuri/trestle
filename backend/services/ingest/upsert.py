"""DB upsert layer for ingested grants.

upsert_ingested_grants — INSERT or UPDATE a batch of IngestedGrant records.
archive_missing_grants — soft-archive grants absent from the latest fetch.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logging import get_logger
from backend.db.models.grant import Grant
from backend.services.ingest.base import IngestedGrant

logger = get_logger(__name__)


@dataclass
class UpsertResult:
    inserted: int
    updated: int


def _to_db_dict(record: IngestedGrant, fetched_at: datetime) -> dict:
    return {
        "source_id": record.source_id,
        "source": record.source,
        "name": record.name,
        "type": record.type,
        "description": record.description,
        "url": record.url,
        "application_url": record.application_url,
        "amount_min": record.amount_min_usd_cents,
        "amount_max": record.amount_max_usd_cents,
        "deadline": record.deadline,
        "rolling": record.rolling,
        "stage": record.stage or None,
        "industry": record.industry or None,
        "location": record.location or None,
        "eligibility": record.eligibility,
        "provider_name": record.provider_name,
        "provider_type": record.provider_type,
        "status": record.status,
        "source_payload": record.source_payload,
        "source_fetched_at": fetched_at,
    }


async def upsert_ingested_grants(
    session: AsyncSession,
    source: str,
    records: list[IngestedGrant],
    fetched_at: datetime,
) -> tuple[int, int]:
    """Upsert a batch. Returns (inserted, updated). One transaction per call."""
    if not records:
        return 0, 0

    source_ids = [r.source_id for r in records]
    result = await session.execute(
        sa.select(Grant.source_id).where(Grant.source_id.in_(source_ids))
    )
    existing_ids = {row.source_id for row in result}

    conn = await session.connection()
    is_postgres = conn.dialect.name == "postgresql"

    inserted = 0
    updated = 0
    now = datetime.now(timezone.utc)

    if is_postgres:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        for record in records:
            data = _to_db_dict(record, fetched_at)
            stmt = pg_insert(Grant).values(
                id=uuid.uuid4(), created_at=now, updated_at=now, **data
            )
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
                    sa.update(Grant)
                    .where(Grant.source_id == record.source_id)
                    .values(**update_fields, updated_at=now)
                )
                updated += 1
            else:
                session.add(
                    Grant(id=uuid.uuid4(), created_at=now, updated_at=now, **data)
                )
                inserted += 1

    await session.commit()
    return inserted, updated


async def archive_missing_grants(
    session: AsyncSession,
    source: str,
    fresh_source_ids: set[str],
    fetched_at: datetime,
) -> int:
    """Mark active grants from `source` that are absent from `fresh_source_ids` as archived.

    Returns the count of newly-archived rows.
    Guard against empty set to avoid invalid NOT IN () SQL.
    """
    if not fresh_source_ids:
        return 0

    now = datetime.now(timezone.utc)
    result = await session.execute(
        sa.update(Grant)
        .where(
            Grant.source == source,
            Grant.source_id.not_in(fresh_source_ids),
            Grant.status == "active",
        )
        .values(status="archived", updated_at=now)
    )
    await session.commit()
    count: int = result.rowcount
    if count:
        logger.info("ingest_grants_archived", source=source, count=count)
    return count
