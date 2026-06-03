from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
import sqlalchemy as sa

from backend.db.models.grant_association import GrantTrack

SEED_DIR = Path(__file__).parent.parent / "seed" / "grants"

SESSION_A = "assoc-sess-a"
SESSION_B = "assoc-sess-b"


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def grants(session_factory):
    """Seed grants and return a list of their source_ids in stable order."""
    from backend.seed.loader import load_grants_from_dir, upsert_grants

    seed_grants = load_grants_from_dir(SEED_DIR)
    async with session_factory() as session:
        await upsert_grants(session, seed_grants)
    return [g.source_id for g in seed_grants]


# ── helpers ───────────────────────────────────────────────────────────────────


async def _track(client, session_id: str, grant_id: str, note: str | None = None) -> tuple[int, dict]:
    body: dict = {"grant_id": grant_id}
    if note is not None:
        body["note"] = note
    res = await client.post(
        "/api/grants/track",
        json=body,
        headers={"X-Session-Id": session_id},
    )
    return res.status_code, res.json()


async def _untrack(client, session_id: str, grant_ref: str) -> int:
    res = await client.delete(
        f"/api/grants/track/{grant_ref}",
        headers={"X-Session-Id": session_id},
    )
    return res.status_code


async def _list_tracked(client, session_id: str, **params) -> tuple[int, dict]:
    res = await client.get(
        "/api/grants/tracked",
        params=params,
        headers={"X-Session-Id": session_id},
    )
    return res.status_code, res.json()


async def _dismiss(client, session_id: str, grant_id: str, reason: str | None = None) -> tuple[int, dict]:
    body: dict = {"grant_id": grant_id}
    if reason is not None:
        body["reason"] = reason
    res = await client.post(
        "/api/grants/dismiss",
        json=body,
        headers={"X-Session-Id": session_id},
    )
    return res.status_code, res.json()


async def _undismiss(client, session_id: str, grant_ref: str) -> int:
    res = await client.delete(
        f"/api/grants/dismiss/{grant_ref}",
        headers={"X-Session-Id": session_id},
    )
    return res.status_code


async def _list_dismissed(client, session_id: str, **params) -> tuple[int, dict]:
    res = await client.get(
        "/api/grants/dismissed",
        params=params,
        headers={"X-Session-Id": session_id},
    )
    return res.status_code, res.json()


async def _match(client, session_id: str, body: dict | None = None) -> tuple[int, dict]:
    res = await client.post(
        "/api/grants/match",
        json=body or {},
        headers={"X-Session-Id": session_id},
    )
    return res.status_code, res.json()


# ── Tracking tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_track_by_uuid(client, grants):
    # 1. POST /grants/track with valid UUID grant_id → 200 with GrantTrackOut.
    res = await client.get("/api/grants", headers={"X-Session-Id": SESSION_A})
    items = res.json()["items"]
    grant = items[0]

    status, body = await _track(client, SESSION_A, grant["id"])
    assert status == 200
    assert body["id"] is not None
    assert body["grant"]["id"] == grant["id"]
    assert body["note"] is None
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_track_by_slug(client, grants):
    # 2. POST /grants/track with slug ref → same result.
    slug = grants[0]
    status, body = await _track(client, SESSION_A, slug, note="apply soon")
    assert status == 200
    assert body["grant"]["source_id"] == slug
    assert body["note"] == "apply soon"


@pytest.mark.asyncio
async def test_track_twice_updates_note_no_duplicate(client, grants):
    # 3. POST /grants/track twice → second call updates note, no new row.
    slug = grants[0]
    status1, body1 = await _track(client, SESSION_A, slug, note="first note")
    assert status1 == 200
    first_id = body1["id"]

    status2, body2 = await _track(client, SESSION_A, slug, note="second note")
    assert status2 == 200
    assert body2["id"] == first_id, "should update the existing row, not create a new one"
    assert body2["note"] == "second note"


@pytest.mark.asyncio
async def test_track_delete_then_delete_again_404(client, grants):
    # 4. POST /track → DELETE → 204. Subsequent DELETE → 404.
    slug = grants[0]
    await _track(client, SESSION_A, slug)

    status1 = await _untrack(client, SESSION_A, slug)
    assert status1 == 204

    status2 = await _untrack(client, SESSION_A, slug)
    assert status2 == 404


@pytest.mark.asyncio
async def test_track_after_soft_delete_reuses_row(client, grants):
    # 5. POST → DELETE (soft-delete) → POST again → same row id, note updated.
    slug = grants[0]
    _, body1 = await _track(client, SESSION_A, slug, note="original")
    original_id = body1["id"]

    await _untrack(client, SESSION_A, slug)

    _, body2 = await _track(client, SESSION_A, slug, note="restored")
    assert body2["id"] == original_id, "should reuse the same row after undelete"
    assert body2["note"] == "restored"


@pytest.mark.asyncio
async def test_list_tracked_active_ordered_by_updated_at_desc(client, grants, session_factory):
    # 6. GET /grants/tracked returns only active tracks, ordered by updated_at DESC.
    # Insert two tracks with explicit timestamps so ordering is deterministic.
    from backend.db.models.grant import Grant as GrantModel

    async with session_factory() as session:
        result = await session.execute(sa.select(GrantModel).limit(2))
        db_grants = result.scalars().all()

    now = datetime.now(timezone.utc)
    t_older = now - timedelta(seconds=5)
    t_newer = now

    async with session_factory() as session:
        track_older = GrantTrack(
            session_id=SESSION_A,
            grant_id=db_grants[0].id,
            created_at=t_older,
            updated_at=t_older,
        )
        track_newer = GrantTrack(
            session_id=SESSION_A,
            grant_id=db_grants[1].id,
            created_at=t_newer,
            updated_at=t_newer,
        )
        session.add_all([track_older, track_newer])
        await session.commit()

    status, body = await _list_tracked(client, SESSION_A)
    assert status == 200
    items = body["items"]
    assert len(items) == 2
    # Newer track first.
    assert items[0]["grant"]["id"] == str(db_grants[1].id)
    assert items[1]["grant"]["id"] == str(db_grants[0].id)


@pytest.mark.asyncio
async def test_list_tracked_cross_session_isolation(client, grants):
    # 7. Session B cannot see Session A's tracks.
    slug = grants[0]
    await _track(client, SESSION_A, slug)

    status, body = await _list_tracked(client, SESSION_B)
    assert status == 200
    assert body["items"] == []


@pytest.mark.asyncio
async def test_list_tracked_cursor_pagination(client, grants, session_factory):
    # 8. Track 5 grants, paginate with limit=2.
    from backend.db.models.grant import Grant as GrantModel

    async with session_factory() as session:
        result = await session.execute(sa.select(GrantModel).limit(5))
        db_grants = result.scalars().all()

    assert len(db_grants) >= 5, "Need at least 5 seeded grants"

    now = datetime.now(timezone.utc)
    async with session_factory() as session:
        for i, g in enumerate(db_grants[:5]):
            t = now - timedelta(seconds=50 - i * 10)  # spread timestamps
            track = GrantTrack(
                session_id=SESSION_A,
                grant_id=g.id,
                created_at=t,
                updated_at=t,
            )
            session.add(track)
        await session.commit()

    status, page1 = await _list_tracked(client, SESSION_A, limit=2)
    assert status == 200
    assert len(page1["items"]) == 2
    assert page1["next_cursor"] is not None

    status, page2 = await _list_tracked(client, SESSION_A, limit=2, cursor=page1["next_cursor"])
    assert status == 200
    assert len(page2["items"]) == 2
    assert page2["next_cursor"] is not None

    status, page3 = await _list_tracked(client, SESSION_A, limit=2, cursor=page2["next_cursor"])
    assert status == 200
    assert len(page3["items"]) == 1
    assert page3["next_cursor"] is None

    # No overlapping ids across pages.
    all_ids = (
        [it["id"] for it in page1["items"]]
        + [it["id"] for it in page2["items"]]
        + [it["id"] for it in page3["items"]]
    )
    assert len(all_ids) == len(set(all_ids))


@pytest.mark.asyncio
async def test_track_nonexistent_grant_404(client, grants):
    # 9. POST /grants/track for nonexistent grant → 404.
    status, _ = await _track(client, SESSION_A, "00000000-0000-0000-0000-000000000000")
    assert status == 404


@pytest.mark.asyncio
async def test_track_note_too_long_422(client, grants):
    # 10. POST /grants/track with note > 500 chars → 422.
    slug = grants[0]
    long_note = "x" * 501
    status, _ = await _track(client, SESSION_A, slug, note=long_note)
    assert status == 422


# ── Dismissal tests ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dismiss_returns_dismissal_out(client, grants):
    # 11. POST /grants/dismiss → 200 with GrantDismissalOut.
    slug = grants[0]
    status, body = await _dismiss(client, SESSION_A, slug, reason="not_interested")
    assert status == 200
    assert body["id"] is not None
    assert "grant_id" in body
    assert body["reason"] == "not_interested"
    assert "created_at" in body


@pytest.mark.asyncio
async def test_dismiss_twice_updates_reason_no_duplicate(client, grants):
    # 12. POST /grants/dismiss twice → second call updates reason, no new row.
    slug = grants[0]
    status1, body1 = await _dismiss(client, SESSION_A, slug, reason="not_eligible")
    assert status1 == 200
    first_id = body1["id"]

    status2, body2 = await _dismiss(client, SESSION_A, slug, reason="too_competitive")
    assert status2 == 200
    assert body2["id"] == first_id, "should update the existing row"
    assert body2["reason"] == "too_competitive"


@pytest.mark.asyncio
async def test_undismiss_then_repeat_404(client, grants):
    # 13. DELETE /grants/dismiss/{ref} → 204. Repeat → 404.
    slug = grants[0]
    await _dismiss(client, SESSION_A, slug)

    status1 = await _undismiss(client, SESSION_A, slug)
    assert status1 == 204

    status2 = await _undismiss(client, SESSION_A, slug)
    assert status2 == 404


@pytest.mark.asyncio
async def test_list_dismissed_cross_session_isolation(client, grants):
    # 14. GET /grants/dismissed returns dismissals for current session only.
    slug = grants[0]
    await _dismiss(client, SESSION_A, slug)

    status, body = await _list_dismissed(client, SESSION_B)
    assert status == 200
    assert body["items"] == []


@pytest.mark.asyncio
async def test_dismiss_invalid_reason_422(client, grants):
    # 15. POST /grants/dismiss with invalid reason → 422.
    slug = grants[0]
    status, _ = await _dismiss(client, SESSION_A, slug, reason="invalid_reason")  # type: ignore[arg-type]
    assert status == 422


@pytest.mark.asyncio
async def test_undismiss_nonexistent_404(client, grants):
    # 16. DELETE /grants/dismiss/{ref} for nonexistent dismissal → 404.
    slug = grants[0]
    status = await _undismiss(client, SESSION_A, slug)
    assert status == 404


# ── Matching integration tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_match_dismissed_grant_absent_by_default(client, grants):
    # 17. Dismiss a grant → POST /grants/match → that grant absent from results.
    # Use include_ineligible=True so the grant would appear if not dismissed.
    slug = grants[0]

    # Confirm grant appears before dismissal (get grant_id from dismiss response to
    # avoid an unauthenticated GET that would pollute the client cookie jar).
    _, dismiss_body = await _dismiss(client, SESSION_A, slug)
    grant_id = dismiss_body["grant_id"]
    await _undismiss(client, SESSION_A, slug)  # clean up

    _, before = await _match(client, SESSION_A, {"include_ineligible": True})
    before_ids = [r["grant"]["id"] for r in before["results"]]
    assert grant_id in before_ids, "grant should appear before dismissal"

    await _dismiss(client, SESSION_A, slug)

    status, body = await _match(client, SESSION_A, {"include_ineligible": True})
    assert status == 200
    result_ids = [r["grant"]["id"] for r in body["results"]]
    assert grant_id not in result_ids


@pytest.mark.asyncio
async def test_match_include_dismissed_shows_dismissed_flag(client, grants):
    # 18. include_dismissed=true → dismissed grant appears with dismissed=true.
    slug = grants[0]

    _, dismiss_body = await _dismiss(client, SESSION_A, slug)
    grant_id = dismiss_body["grant_id"]

    status, body = await _match(
        client, SESSION_A, {"include_dismissed": True, "include_ineligible": True}
    )
    assert status == 200
    dismissed_result = next(
        (r for r in body["results"] if r["grant"]["id"] == grant_id), None
    )
    assert dismissed_result is not None, "dismissed grant should appear with include_dismissed=true"
    assert dismissed_result["dismissed"] is True


@pytest.mark.asyncio
async def test_match_tracked_grant_shows_tracked_flag(client, grants):
    # 19. Track a grant → /grants/match shows tracked=true for it; others false.
    # Use include_ineligible=True so the grant appears regardless of eligibility.
    slug = grants[0]

    _, track_body = await _track(client, SESSION_A, slug)
    grant_id = track_body["grant"]["id"]

    status, body = await _match(client, SESSION_A, {"include_ineligible": True})
    assert status == 200

    tracked_result = next(
        (r for r in body["results"] if r["grant"]["id"] == grant_id), None
    )
    assert tracked_result is not None
    assert tracked_result["tracked"] is True

    # Every other result should have tracked=false.
    for r in body["results"]:
        if r["grant"]["id"] != grant_id:
            assert r["tracked"] is False


@pytest.mark.asyncio
async def test_match_tracked_cross_session_isolation(client, grants):
    # 20. Session A tracks grant X; Session B's /grants/match shows tracked=false for X.
    # Get grant_id from the track response to avoid unauthenticated GETs that pollute
    # the client cookie jar and would override the X-Session-Id header in later calls.
    slug = grants[0]

    _, track_body = await _track(client, SESSION_A, slug)
    grant_id = track_body["grant"]["id"]

    status, body = await _match(client, SESSION_B, {"include_ineligible": True})
    assert status == 200
    result = next((r for r in body["results"] if r["grant"]["id"] == grant_id), None)
    assert result is not None, "grant should appear for session B with include_ineligible=True"
    assert result["tracked"] is False
