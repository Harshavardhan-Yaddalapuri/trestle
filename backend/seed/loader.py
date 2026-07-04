from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import sqlalchemy as sa
import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.grant import Grant
from backend.schemas.grant import GrantSeed


def load_grants_from_dir(path: Path) -> list[GrantSeed]:
    grants: list[GrantSeed] = []
    for yaml_file in sorted(path.glob("*.yaml")):
        with yaml_file.open() as f:
            data = yaml.safe_load(f)
        grants.append(GrantSeed.model_validate(data))
    return grants


async def upsert_grants(
    session: AsyncSession, grants: list[GrantSeed]
) -> tuple[int, int]:
    """Upsert a batch of grants. Returns (inserted, updated). One transaction."""
    if not grants:
        return 0, 0

    source_ids = [g.source_id for g in grants]
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

        for seed in grants:
            data = seed.model_dump(exclude={"amount_display"})
            stmt = pg_insert(Grant).values(
                id=uuid.uuid4(), created_at=now, updated_at=now, **data
            )
            update_fields = {k: v for k, v in data.items() if k != "source_id"}
            stmt = stmt.on_conflict_do_update(
                index_elements=["source_id"],
                set_={**update_fields, "updated_at": now},
            )
            await session.execute(stmt)
            if seed.source_id in existing_ids:
                updated += 1
            else:
                inserted += 1
    else:
        for seed in grants:
            data = seed.model_dump(exclude={"amount_display"})
            if seed.source_id in existing_ids:
                update_fields = {k: v for k, v in data.items() if k != "source_id"}
                await session.execute(
                    sa.update(Grant)
                    .where(Grant.source_id == seed.source_id)
                    .values(**update_fields, updated_at=now)
                )
                updated += 1
            else:
                session.add(Grant(id=uuid.uuid4(), created_at=now, updated_at=now, **data))
                inserted += 1

    await session.commit()
    return inserted, updated
