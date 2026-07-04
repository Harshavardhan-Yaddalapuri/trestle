from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
import sqlalchemy as sa

from backend.db.models.grant_association import GrantLifecycleEvent, GrantTrack
from backend.services.lifecycle import is_terminal, validate_transition
from backend.services.lifecycle.transitions import LEGAL_TRANSITIONS

SEED_DIR = Path(__file__).parent.parent / "seed" / "grants"

SESSION_LC = "lifecycle-sess-a"
SESSION_LB = "lifecycle-sess-b"


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def grants(session_factory):
    from backend.seed.loader import load_grants_from_dir, upsert_grants

    seed_grants = load_grants_from_dir(SEED_DIR)
    async with session_factory() as session:
        await upsert_grants(session, seed_grants)
    return [g.source_id for g in seed_grants]


# ── HTTP helpers ──────────────────────────────────────────────────────────────


async def _track(client, session_id: str, grant_id: str) -> tuple[int, dict]:
    res = await client.post(
        "/api/grants/track",
        json={"grant_id": grant_id},
        headers={"X-Session-Id": session_id},
    )
    return res.status_code, res.json()


async def _transition(
    client,
    session_id: str,
    grant_ref: str,
    to_status: str,
    metadata: dict | None = None,
    note: str | None = None,
) -> tuple[int, dict]:
    body: dict = {"to_status": to_status}
    if metadata is not None:
        body["metadata"] = metadata
    if note is not None:
        body["note"] = note
    res = await client.post(
        f"/api/grants/{grant_ref}/lifecycle",
        json=body,
        headers={"X-Session-Id": session_id},
    )
    return res.status_code, res.json()


async def _list_lifecycle(client, session_id: str, **params) -> tuple[int, dict]:
    res = await client.get(
        "/api/grants/lifecycle",
        params=params,
        headers={"X-Session-Id": session_id},
    )
    return res.status_code, res.json()


async def _lifecycle_events(client, session_id: str, grant_ref: str) -> tuple[int, dict]:
    res = await client.get(
        f"/api/grants/{grant_ref}/lifecycle/events",
        headers={"X-Session-Id": session_id},
    )
    return res.status_code, res.json()


# ── Test 1: new track starts at 'interested', no event rows ──────────────────


@pytest.mark.asyncio
async def test_track_creates_interested_no_events(client, grants):
    slug = grants[0]
    status, body = await _track(client, SESSION_LC, slug)
    assert status == 200
    assert body["lifecycle_status"] == "interested"
    assert body["lifecycle_metadata"] == {}
    assert "lifecycle_updated_at" in body

    ev_status, ev_body = await _lifecycle_events(client, SESSION_LC, slug)
    assert ev_status == 200
    assert ev_body["events"] == []


# ── Test 2: first transition creates 1 event row ─────────────────────────────


@pytest.mark.asyncio
async def test_first_transition_creates_event(client, grants):
    slug = grants[0]
    await _track(client, SESSION_LC, slug)

    status, body = await _transition(client, SESSION_LC, slug, "researching")
    assert status == 200
    assert body["lifecycle_status"] == "researching"

    ev_status, ev_body = await _lifecycle_events(client, SESSION_LC, slug)
    assert ev_status == 200
    events = ev_body["events"]
    assert len(events) == 1
    assert events[0]["from_status"] == "interested"
    assert events[0]["to_status"] == "researching"
    assert events[0]["transition_kind"] == "user"


# ── Test 3: illegal transition → 422 with code ───────────────────────────────


@pytest.mark.asyncio
async def test_illegal_transition_422(client, grants):
    slug = grants[0]
    await _track(client, SESSION_LC, slug)

    # interested → submitted skips states
    status, body = await _transition(client, SESSION_LC, slug, "submitted")
    assert status == 422
    assert body["code"] == "invalid_lifecycle_transition"


# ── Test 4: lifecycle non-tracked grant → 404 ────────────────────────────────


@pytest.mark.asyncio
async def test_lifecycle_untracked_grant_404(client, grants):
    slug = grants[0]
    # Do NOT track — just attempt to transition
    status, _ = await _transition(client, SESSION_LC, slug, "researching")
    assert status == 404


# ── Test 5: cross-session lifecycle → 404 ────────────────────────────────────


@pytest.mark.asyncio
async def test_lifecycle_cross_session_404(client, grants):
    slug = grants[0]
    await _track(client, SESSION_LC, slug)

    # Session B tries to transition Session A's track
    status, _ = await _transition(client, SESSION_LB, slug, "researching")
    assert status == 404


# ── Test 6: full happy path, 5 events, metadata accumulates ──────────────────


@pytest.mark.asyncio
async def test_full_lifecycle_happy_path(client, grants):
    slug = grants[0]
    await _track(client, SESSION_LC, slug)

    steps = [
        ("researching", {}),
        ("drafting", {}),
        ("submitted", {"submitted_at": "2026-06-01", "submission_url": "https://example.com/apply"}),
        ("under_review", {"decision_note": "pending committee"}),
        ("awarded", {"decision_at": "2026-06-15"}),
    ]

    last_body = None
    for to_status, meta in steps:
        status, last_body = await _transition(client, SESSION_LC, slug, to_status, meta)
        assert status == 200, f"step to {to_status} failed: {last_body}"
        assert last_body["lifecycle_status"] == to_status

    # 5 event rows
    _, ev_body = await _lifecycle_events(client, SESSION_LC, slug)
    assert len(ev_body["events"]) == 5

    # Metadata accumulated from all transitions
    assert last_body is not None
    meta = last_body["lifecycle_metadata"]
    assert meta["submitted_at"] == "2026-06-01"
    assert meta["submission_url"] == "https://example.com/apply"
    assert meta["decision_note"] == "pending committee"
    assert meta["decision_at"] == "2026-06-15"


# ── Test 7: transition to terminal status ────────────────────────────────────


@pytest.mark.asyncio
async def test_transition_to_terminal_withdrawn(client, grants):
    slug = grants[0]
    await _track(client, SESSION_LC, slug)

    # submitted → withdrawn (legal terminal path)
    await _transition(client, SESSION_LC, slug, "researching")
    await _transition(client, SESSION_LC, slug, "drafting")
    await _transition(client, SESSION_LC, slug, "submitted")

    status, body = await _transition(client, SESSION_LC, slug, "withdrawn")
    assert status == 200
    assert body["lifecycle_status"] == "withdrawn"


# ── Test 8: no transitions out of 'awarded' ──────────────────────────────────


@pytest.mark.asyncio
async def test_awarded_is_fully_terminal(client, grants):
    slug = grants[0]
    await _track(client, SESSION_LC, slug)
    await _transition(client, SESSION_LC, slug, "researching")
    await _transition(client, SESSION_LC, slug, "drafting")
    await _transition(client, SESSION_LC, slug, "submitted")
    await _transition(client, SESSION_LC, slug, "under_review")
    await _transition(client, SESSION_LC, slug, "awarded")

    # Any further transition should be 422
    status, body = await _transition(client, SESSION_LC, slug, "researching")
    assert status == 422
    assert body["code"] == "invalid_lifecycle_transition"


# ── Test 9: rejected → researching (re-attempt path) ─────────────────────────


@pytest.mark.asyncio
async def test_rejected_to_researching_allowed(client, grants):
    slug = grants[0]
    await _track(client, SESSION_LC, slug)
    await _transition(client, SESSION_LC, slug, "researching")
    await _transition(client, SESSION_LC, slug, "drafting")
    await _transition(client, SESSION_LC, slug, "submitted")
    await _transition(client, SESSION_LC, slug, "rejected")

    status, body = await _transition(client, SESSION_LC, slug, "researching")
    assert status == 200
    assert body["lifecycle_status"] == "researching"


# ── Test 10: GET /lifecycle excludes terminal by default ─────────────────────


@pytest.mark.asyncio
async def test_lifecycle_list_excludes_terminal_by_default(client, grants):
    assert len(grants) >= 2
    slug_active = grants[0]
    slug_terminal = grants[1]

    await _track(client, SESSION_LC, slug_active)
    await _track(client, SESSION_LC, slug_terminal)
    await _transition(client, SESSION_LC, slug_terminal, "abandoned")

    status, body = await _list_lifecycle(client, SESSION_LC)
    assert status == 200
    returned_slugs = [item["grant"]["source_id"] for item in body["items"]]
    assert slug_active in returned_slugs
    assert slug_terminal not in returned_slugs


# ── Test 11: status=awarded,rejected returns only terminal ───────────────────


@pytest.mark.asyncio
async def test_lifecycle_list_terminal_filter(client, grants):
    assert len(grants) >= 2
    slug_active = grants[0]
    slug_awarded = grants[1]

    await _track(client, SESSION_LC, slug_active)
    await _track(client, SESSION_LC, slug_awarded)
    await _transition(client, SESSION_LC, slug_awarded, "withdrawn")

    status, body = await _list_lifecycle(
        client, SESSION_LC, status="awarded,rejected,withdrawn,abandoned"
    )
    assert status == 200
    returned_slugs = [item["grant"]["source_id"] for item in body["items"]]
    assert slug_awarded in returned_slugs
    assert slug_active not in returned_slugs


# ── Test 12: status=drafting returns only drafting ───────────────────────────


@pytest.mark.asyncio
async def test_lifecycle_list_single_status_filter(client, grants):
    assert len(grants) >= 2
    slug_drafting = grants[0]
    slug_researching = grants[1]

    await _track(client, SESSION_LC, slug_drafting)
    await _track(client, SESSION_LC, slug_researching)
    await _transition(client, SESSION_LC, slug_drafting, "researching")
    await _transition(client, SESSION_LC, slug_drafting, "drafting")
    await _transition(client, SESSION_LC, slug_researching, "researching")

    status, body = await _list_lifecycle(client, SESSION_LC, status="drafting")
    assert status == 200
    returned_slugs = [item["grant"]["source_id"] for item in body["items"]]
    assert slug_drafting in returned_slugs
    assert slug_researching not in returned_slugs


# ── Test 13: GET /lifecycle cursor pagination ─────────────────────────────────


@pytest.mark.asyncio
async def test_lifecycle_list_cursor_pagination(client, grants, session_factory):
    from backend.db.models.grant import Grant as GrantModel

    async with session_factory() as session:
        result = await session.execute(sa.select(GrantModel).limit(5))
        db_grants = result.scalars().all()

    assert len(db_grants) >= 5

    now = datetime.now(timezone.utc)
    async with session_factory() as session:
        for i, g in enumerate(db_grants[:5]):
            t = now - timedelta(seconds=50 - i * 10)
            track = GrantTrack(
                session_id=SESSION_LC,
                grant_id=g.id,
                created_at=t,
                updated_at=t,
                lifecycle_updated_at=t,
            )
            session.add(track)
        await session.commit()

    status, page1 = await _list_lifecycle(client, SESSION_LC, limit=2)
    assert status == 200
    assert len(page1["items"]) == 2
    assert page1["next_cursor"] is not None

    status, page2 = await _list_lifecycle(
        client, SESSION_LC, limit=2, cursor=page1["next_cursor"]
    )
    assert status == 200
    assert len(page2["items"]) == 2
    assert page2["next_cursor"] is not None

    status, page3 = await _list_lifecycle(
        client, SESSION_LC, limit=2, cursor=page2["next_cursor"]
    )
    assert status == 200
    assert len(page3["items"]) == 1
    assert page3["next_cursor"] is None

    all_ids = (
        [it["id"] for it in page1["items"]]
        + [it["id"] for it in page2["items"]]
        + [it["id"] for it in page3["items"]]
    )
    assert len(all_ids) == len(set(all_ids))


# ── Test 14: GET /lifecycle/events returns ASC order ─────────────────────────


@pytest.mark.asyncio
async def test_lifecycle_events_asc_order(client, grants):
    slug = grants[0]
    await _track(client, SESSION_LC, slug)

    for to_status in ["researching", "drafting"]:
        await _transition(client, SESSION_LC, slug, to_status)

    _, ev_body = await _lifecycle_events(client, SESSION_LC, slug)
    events = ev_body["events"]
    assert len(events) == 2

    # created_at ASC: first transition first
    t0 = datetime.fromisoformat(events[0]["created_at"].replace("Z", "+00:00"))
    t1 = datetime.fromisoformat(events[1]["created_at"].replace("Z", "+00:00"))
    assert t0 <= t1
    assert events[0]["to_status"] == "researching"
    assert events[1]["to_status"] == "drafting"


# ── Test 15: metadata merge and null-removal ──────────────────────────────────


@pytest.mark.asyncio
async def test_metadata_merge_and_null_removal(client, grants):
    slug = grants[0]
    await _track(client, SESSION_LC, slug)

    # First transition with {a: 1}
    _, body1 = await _transition(
        client, SESSION_LC, slug, "researching", metadata={"a": 1}
    )
    assert body1["lifecycle_metadata"] == {"a": 1}

    # Second transition with {b: 2} — merged
    _, body2 = await _transition(
        client, SESSION_LC, slug, "drafting", metadata={"b": 2}
    )
    assert body2["lifecycle_metadata"] == {"a": 1, "b": 2}

    # Third transition with {a: null} — removes key a
    _, body3 = await _transition(
        client, SESSION_LC, slug, "researching", metadata={"a": None}
    )
    assert body3["lifecycle_metadata"] == {"b": 2}
    assert "a" not in body3["lifecycle_metadata"]


# ── Test 16: validate_transition unit tests (no HTTP, no DB) ─────────────────


class TestValidateTransition:
    def test_all_legal_transitions_accepted(self):
        from backend.services.lifecycle.transitions import LEGAL_TRANSITIONS

        for from_s, targets in LEGAL_TRANSITIONS.items():
            for to_s in targets:
                validate_transition(from_s, to_s, "user")  # no raise

    def test_illegal_transition_raises(self):
        from backend.core.errors import ValidationError as AppValidationError

        with pytest.raises(AppValidationError) as exc_info:
            validate_transition("interested", "submitted", "user")
        assert exc_info.value.code == "invalid_lifecycle_transition"

    def test_terminal_no_transitions(self):
        from backend.core.errors import ValidationError as AppValidationError

        with pytest.raises(AppValidationError):
            validate_transition("awarded", "researching", "user")

    def test_automated_submitted_to_under_review_ok(self):
        validate_transition("submitted", "under_review", "automated")  # no raise

    def test_automated_non_terminal_to_abandoned_ok(self):
        # Only states where abandoned is in LEGAL_TRANSITIONS qualify.
        for from_s in ["interested", "researching", "drafting"]:
            validate_transition(from_s, "abandoned", "automated")  # no raise

    def test_automated_user_transition_blocked(self):
        from backend.core.errors import ValidationError as AppValidationError

        with pytest.raises(AppValidationError) as exc_info:
            validate_transition("interested", "researching", "automated")
        assert exc_info.value.code == "invalid_lifecycle_transition"

    def test_automated_terminal_to_abandoned_blocked(self):
        # Terminal states have no legal transitions at all; the first check blocks it.
        from backend.core.errors import ValidationError as AppValidationError

        with pytest.raises(AppValidationError):
            validate_transition("awarded", "abandoned", "automated")

    def test_unknown_from_status_raises(self):
        from backend.core.errors import ValidationError as AppValidationError

        with pytest.raises(AppValidationError):
            validate_transition("nonexistent", "interested", "user")


# ── Test 17: is_terminal ──────────────────────────────────────────────────────


class TestIsTerminal:
    def test_terminal_statuses(self):
        for s in ("awarded", "rejected", "withdrawn", "abandoned"):
            assert is_terminal(s) is True

    def test_non_terminal_statuses(self):
        for s in ("interested", "researching", "drafting", "submitted", "under_review"):
            assert is_terminal(s) is False
