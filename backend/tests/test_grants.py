from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.seed.loader import load_grants_from_dir, upsert_grants

SEED_DIR = Path(__file__).parent.parent / "seed" / "grants"


# ── helpers ───────────────────────────────────────────────────────────────────


async def _list(client, **params) -> dict:
    res = await client.get("/api/grants", params=params)
    assert res.status_code == 200, res.text
    return res.json()


async def _get(client, ref: str) -> tuple[int, dict]:
    res = await client.get(f"/api/grants/{ref}")
    return res.status_code, res.json()


# ── 1. empty table ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_grants_empty(client):
    body = await _list(client)
    assert body == {"items": [], "next_cursor": None, "total_estimate": None}


# ── 2. ordering by deadline ASC NULLS LAST ────────────────────────────────────


@pytest.mark.asyncio
async def test_list_grants_ordered_by_deadline(client, seeded_grants):
    body = await _list(client)
    items = body["items"]
    assert len(items) == 5

    # Collect deadlines; None should be last.
    deadlines = [it["deadline"] for it in items]
    non_null = [d for d in deadlines if d is not None]
    null_count = sum(1 for d in deadlines if d is None)

    assert non_null == sorted(non_null), "non-null deadlines must be ascending"
    assert deadlines.index(None) == len(deadlines) - 1 if null_count == 1 else True
    assert null_count == 1, "YC (rolling) should be the only grant with null deadline"


# ── 3. type filter ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_filter_by_type_accelerator(client, seeded_grants):
    body = await _list(client, type="accelerator")
    assert len(body["items"]) == 1
    assert body["items"][0]["source_id"] == "yc-w26"


# ── 4. stage filter (seed + any) ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_filter_by_stage_seed(client, seeded_grants):
    body = await _list(client, stage="seed")
    source_ids = {it["source_id"] for it in body["items"]}

    # YC and NSF have 'seed' in their stage; Mozilla and Anthropic have 'any'.
    assert "yc-w26" in source_ids
    assert "nsf-sbir-phase-1" in source_ids
    assert "mozilla-builders" in source_ids
    assert "anthropic-academic-grants" in source_ids

    # Activate has only ['pre_seed'] – no 'seed', no 'any' – must be excluded.
    assert "activate-fellowship" not in source_ids

    # Every returned grant must have 'seed' or 'any' in its stage.
    for item in body["items"]:
        stage = item["stage"] or []
        assert "seed" in stage or "any" in stage, f"{item['source_id']} should not match"


# ── 5. text search ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_filter_by_q_safety(client, seeded_grants):
    body = await _list(client, q="safety")
    assert len(body["items"]) == 1
    assert body["items"][0]["source_id"] == "anthropic-academic-grants"


# ── 6. cursor pagination ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cursor_pagination_returns_all_no_duplicates(client, seeded_grants):
    seen_ids: list[str] = []
    cursor = None

    while True:
        params: dict = {"limit": 2}
        if cursor:
            params["cursor"] = cursor
        body = await _list(client, **params)
        for item in body["items"]:
            assert item["id"] not in seen_ids, f"duplicate: {item['id']}"
            seen_ids.append(item["id"])
        cursor = body["next_cursor"]
        if cursor is None:
            break

    assert len(seen_ids) == 5


# ── 7. slug and UUID lookup ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_by_slug_and_uuid_return_same(client, seeded_grants):
    code_slug, by_slug = await _get(client, "yc-w26")
    assert code_slug == 200

    grant_uuid = by_slug["id"]
    code_uuid, by_uuid = await _get(client, grant_uuid)
    assert code_uuid == 200

    assert by_slug == by_uuid


# ── 8. 404 on missing grant ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_missing_grant_returns_404(client):
    code, body = await _get(client, "does-not-exist")
    assert code == 404
    assert body["code"] == "not_found"


# ── 9. loader idempotency ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_loader_idempotency(session_factory):
    grants = load_grants_from_dir(SEED_DIR)

    async with session_factory() as session:
        i1, u1 = await upsert_grants(session, grants)
    assert i1 == 5
    assert u1 == 0

    # Run again with identical data – all rows already exist.
    async with session_factory() as session:
        i2, u2 = await upsert_grants(session, grants)
    assert i2 == 0
    assert u2 == 5


# ── 10. loader change detection ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_loader_change_detection(session_factory):
    grants = load_grants_from_dir(SEED_DIR)

    async with session_factory() as session:
        await upsert_grants(session, grants)

    # Re-run with only the modified grant.
    modified = grants[0].model_copy(update={"description": "Updated description for change detection test."})

    async with session_factory() as session:
        inserted, updated = await upsert_grants(session, [modified])

    assert inserted == 0
    assert updated == 1


# ── 11. GrantSeed validator rejects bad amounts ───────────────────────────────


def test_grant_seed_rejects_amount_min_gt_max():
    from pydantic import ValidationError as PydanticValidationError

    from backend.schemas.grant import GrantSeed

    with pytest.raises(PydanticValidationError, match="amount_min"):
        GrantSeed(
            source_id="test",
            name="Test",
            type="grant",
            description="test",
            url="https://example.com",
            provider_name="Test Org",
            amount_min=5000000,
            amount_max=1000000,
        )
