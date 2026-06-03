from __future__ import annotations

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────


async def _get_profile(client, session_id: str) -> dict:
    res = await client.get(
        "/api/users/profile",
        headers={"X-Session-Id": session_id},
    )
    assert res.status_code == 200
    return res.json()


async def _put_profile(client, session_id: str, body: dict) -> dict:
    res = await client.put(
        "/api/users/profile",
        json=body,
        headers={"X-Session-Id": session_id},
    )
    return res


# ── Tests ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_profile_no_row_returns_empty(client):
    """GET with no row → 200, session_id set, all other fields null, timestamps null."""
    body = await _get_profile(client, "sess-profile-empty")
    assert body["session_id"] == "sess-profile-empty"
    for field in ("founder_name", "company_name", "company_stage", "industry",
                  "location", "website", "one_liner", "goals", "created_at", "updated_at"):
        assert body[field] is None, f"expected {field} to be null"


@pytest.mark.asyncio
async def test_put_profile_creates_and_returns(client):
    """PUT with founder_name and company_name → 200, fields reflected, timestamps set."""
    res = await _put_profile(client, "sess-profile-create", {
        "founder_name": "Alice",
        "company_name": "Acme",
    })
    assert res.status_code == 200
    body = res.json()
    assert body["founder_name"] == "Alice"
    assert body["company_name"] == "Acme"
    assert body["created_at"] is not None
    assert body["updated_at"] is not None
    # Unset fields remain null
    assert body["one_liner"] is None


@pytest.mark.asyncio
async def test_put_profile_partial_update_preserves_other_fields(client):
    """PUT with one_liner on existing profile → only one_liner updated, founder_name preserved."""
    session = "sess-profile-partial"
    await _put_profile(client, session, {"founder_name": "Bob"})

    res = await _put_profile(client, session, {"one_liner": "We make widgets."})
    assert res.status_code == 200
    body = res.json()
    assert body["founder_name"] == "Bob"
    assert body["one_liner"] == "We make widgets."


@pytest.mark.asyncio
async def test_put_profile_industry_array_roundtrips(client):
    """PUT with industry list → array round-trips (SQLite uses JSON)."""
    res = await _put_profile(client, "sess-profile-industry", {
        "industry": ["fintech", "b2b"],
    })
    assert res.status_code == 200
    body = res.json()
    assert body["industry"] == ["fintech", "b2b"]

    # GET confirms persistence
    fetched = await _get_profile(client, "sess-profile-industry")
    assert fetched["industry"] == ["fintech", "b2b"]


@pytest.mark.asyncio
async def test_put_profile_invalid_company_stage_returns_422(client):
    """PUT with company_stage='invalid' → 422."""
    res = await _put_profile(client, "sess-profile-bad-stage", {
        "company_stage": "invalid",
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_put_profile_one_liner_too_long_returns_422(client):
    """PUT with one_liner of 281 chars → 422."""
    res = await _put_profile(client, "sess-profile-long-liner", {
        "one_liner": "x" * 281,
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_put_profile_invalid_website_returns_422(client):
    """PUT with website='not a url' → 422."""
    res = await _put_profile(client, "sess-profile-bad-url", {
        "website": "not a url",
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_put_profile_whitespace_name_stored_as_null(client):
    """PUT with founder_name='   ' → stored as null, GET returns null."""
    res = await _put_profile(client, "sess-profile-whitespace", {
        "founder_name": "   ",
    })
    assert res.status_code == 200
    body = res.json()
    assert body["founder_name"] is None

    fetched = await _get_profile(client, "sess-profile-whitespace")
    assert fetched["founder_name"] is None


@pytest.mark.asyncio
async def test_profile_session_isolation(client):
    """Profile from session A is invisible to session B."""
    await _put_profile(client, "sess-profile-A", {"founder_name": "Alice"})

    body_b = await _get_profile(client, "sess-profile-B")
    assert body_b["founder_name"] is None
    assert body_b["session_id"] == "sess-profile-B"


@pytest.mark.asyncio
async def test_string_list_type_resolves_per_dialect():
    """StringList TypeDecorator resolves to JSON on SQLite and ARRAY on PostgreSQL."""
    from sqlalchemy.dialects import postgresql as pg_dialect, sqlite as sqlite_dialect

    from backend.db.types import StringList

    sl = StringList()
    sqlite_impl = sl.load_dialect_impl(sqlite_dialect.dialect())
    pg_impl = sl.load_dialect_impl(pg_dialect.dialect())

    sqlite_type = type(sqlite_impl).__name__
    pg_type = type(pg_impl).__name__

    print(f"\nSQLite dialect → {sqlite_type}")
    print(f"PostgreSQL dialect → {pg_type}")

    assert "JSON" in sqlite_type.upper()
    assert "ARRAY" in pg_type.upper()
