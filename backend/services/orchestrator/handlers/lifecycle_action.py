from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, AsyncIterator

import sqlalchemy as sa

from backend.db.models.grant import Grant
from backend.db.models.grant_association import GrantDismissal, GrantTrack
from backend.services.orchestrator.events import (
    FinishEvent,
    LLMTokenEvent,
    OrchestratorEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from backend.services.orchestrator.prompts import build_lifecycle_system_prompt
from backend.services.orchestrator.response_stream import stream_llm_response

if TYPE_CHECKING:
    from backend.services.orchestrator.context_loader import TurnContext


async def _resolve_grant(db, grant_ref: str) -> Grant | None:
    result = await db.execute(sa.select(Grant).where(Grant.source_id == grant_ref))
    grant = result.scalar_one_or_none()
    if grant:
        return grant
    try:
        gid = uuid.UUID(grant_ref)
        return await db.get(Grant, gid)
    except ValueError:
        pass
    result = await db.execute(
        sa.select(Grant).where(Grant.name.ilike(f"%{grant_ref}%")).limit(1)
    )
    return result.scalar_one_or_none()


async def _track(session_id: str, grant: Grant, db) -> dict:
    now = datetime.now(timezone.utc)
    existing = (await db.execute(
        sa.select(GrantTrack).where(
            GrantTrack.session_id == session_id,
            GrantTrack.grant_id == grant.id,
        )
    )).scalar_one_or_none()

    if existing is not None:
        await db.execute(
            sa.update(GrantTrack)
            .where(GrantTrack.id == existing.id)
            .values(updated_at=now, deleted_at=None)
        )
        await db.commit()
        return {"track_id": str(existing.id), "grant_name": grant.name}
    else:
        track = GrantTrack(session_id=session_id, grant_id=grant.id, created_at=now, updated_at=now)
        db.add(track)
        await db.commit()
        await db.refresh(track)
        return {"track_id": str(track.id), "grant_name": grant.name}


async def _untrack(session_id: str, grant: Grant, db) -> dict:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        sa.update(GrantTrack)
        .where(
            GrantTrack.session_id == session_id,
            GrantTrack.grant_id == grant.id,
            GrantTrack.deleted_at.is_(None),
        )
        .values(deleted_at=now, updated_at=now)
    )
    await db.commit()
    return {"untracked": result.rowcount > 0, "grant_name": grant.name}


async def _dismiss(session_id: str, grant: Grant, db) -> dict:
    now = datetime.now(timezone.utc)
    existing = (await db.execute(
        sa.select(GrantDismissal).where(
            GrantDismissal.session_id == session_id,
            GrantDismissal.grant_id == grant.id,
        )
    )).scalar_one_or_none()

    if existing is None:
        dismissal = GrantDismissal(session_id=session_id, grant_id=grant.id, created_at=now)
        db.add(dismissal)
        await db.commit()
        await db.refresh(dismissal)
        return {"dismissal_id": str(dismissal.id), "grant_name": grant.name}
    return {"dismissal_id": str(existing.id), "grant_name": grant.name}


async def _undismiss(session_id: str, grant: Grant, db) -> dict:
    result = await db.execute(
        sa.delete(GrantDismissal).where(
            GrantDismissal.session_id == session_id,
            GrantDismissal.grant_id == grant.id,
        )
    )
    await db.commit()
    return {"undismissed": result.rowcount > 0, "grant_name": grant.name}


_ACTION_FNS = {
    "track": _track,
    "untrack": _untrack,
    "dismiss": _dismiss,
    "undismiss": _undismiss,
}


async def handle_lifecycle_action(ctx: TurnContext) -> AsyncIterator[OrchestratorEvent]:
    entities = ctx.intent.entities
    action = entities.action
    grant_refs = entities.grant_refs

    if not action or not grant_refs:
        yield LLMTokenEvent(
            delta="I'd need to know which grant and action (track/dismiss) you mean. "
                  "Could you be more specific?"
        )
        yield FinishEvent(reason="stop")
        return

    grant = await _resolve_grant(ctx.db, grant_refs[0])
    if grant is None:
        yield LLMTokenEvent(
            delta=f"I couldn't find a grant matching '{grant_refs[0]}'. "
                  "Could you check the name?"
        )
        yield FinishEvent(reason="stop")
        return

    action_fn = _ACTION_FNS.get(action)
    if action_fn is None:
        yield LLMTokenEvent(delta=f"I don't know how to '{action}' a grant.")
        yield FinishEvent(reason="stop")
        return

    yield ToolCallEvent(name=f"grants.{action}", args={"grant_ref": grant_refs[0], "action": action})
    result = await action_fn(ctx.session_id, grant, ctx.db)
    yield ToolResultEvent(name=f"grants.{action}", result=result)

    system_prompt = build_lifecycle_system_prompt(ctx, action, grant.name)
    async for event in stream_llm_response(ctx, system_prompt):
        yield event
