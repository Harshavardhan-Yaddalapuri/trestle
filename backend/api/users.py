from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import require_user
from backend.db.models.profile import Profile
from backend.db.models.user import User
from backend.db.session import get_db
from backend.middleware.auth import UserCtx
from backend.schemas.alerts import AlertPreferencesIn, AlertPreferencesOut
from backend.schemas.profile import ProfileIn, ProfileOut

router = APIRouter(prefix="/users", tags=["users"])

_PREF_DEFAULTS = {
    "deadline_reminders": True,
    "new_grant_matches": True,
    "check_ins": True,
}


@router.get("/profile", response_model=ProfileOut)
async def get_profile(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
    session_id = request.state.session_id

    result = await db.execute(
        sa.select(Profile).where(Profile.session_id == session_id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        return ProfileOut(session_id=session_id)

    return ProfileOut.model_validate(profile)


@router.put("/profile", response_model=ProfileOut)
async def upsert_profile(
    request: Request,
    body: ProfileIn,
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
    session_id = request.state.session_id
    fields = body.model_dump(exclude_unset=True)

    conn = await db.connection()
    is_postgres = conn.dialect.name == "postgresql"

    if is_postgres:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        now = sa.func.now()
        stmt = pg_insert(Profile).values(
            id=uuid.uuid4(),
            session_id=session_id,
            created_at=now,
            updated_at=now,
            **fields,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["session_id"],
            set_={**fields, "updated_at": now},
        )
        await db.execute(stmt)
        await db.commit()
    else:
        result = await db.execute(
            sa.select(Profile).where(Profile.session_id == session_id)
        )
        profile = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if profile is None:
            profile = Profile(
                session_id=session_id,
                created_at=now,
                updated_at=now,
                **fields,
            )
            db.add(profile)
        else:
            for k, v in fields.items():
                setattr(profile, k, v)
            profile.updated_at = now

        await db.commit()
        await db.refresh(profile)
        return ProfileOut.model_validate(profile)

    result = await db.execute(
        sa.select(Profile).where(Profile.session_id == session_id)
    )
    profile = result.scalar_one()
    return ProfileOut.model_validate(profile)


@router.get("/alert-preferences", response_model=AlertPreferencesOut)
async def get_alert_preferences(
    current_user: UserCtx = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> AlertPreferencesOut:
    result = await db.execute(sa.select(User).where(User.id == current_user.id))
    user = result.scalar_one()
    prefs = user.alert_preferences or {}
    return AlertPreferencesOut(
        deadline_reminders=prefs.get("deadline_reminders", _PREF_DEFAULTS["deadline_reminders"]),
        new_grant_matches=prefs.get("new_grant_matches", _PREF_DEFAULTS["new_grant_matches"]),
        check_ins=prefs.get("check_ins", _PREF_DEFAULTS["check_ins"]),
    )


@router.put("/alert-preferences", response_model=AlertPreferencesOut)
async def update_alert_preferences(
    body: AlertPreferencesIn,
    current_user: UserCtx = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> AlertPreferencesOut:
    result = await db.execute(sa.select(User).where(User.id == current_user.id))
    user = result.scalar_one()

    update = body.model_dump(exclude_unset=True, exclude_none=True)
    existing = dict(user.alert_preferences or {})
    existing.update(update)
    user.alert_preferences = existing
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return AlertPreferencesOut(
        deadline_reminders=existing.get("deadline_reminders", _PREF_DEFAULTS["deadline_reminders"]),
        new_grant_matches=existing.get("new_grant_matches", _PREF_DEFAULTS["new_grant_matches"]),
        check_ins=existing.get("check_ins", _PREF_DEFAULTS["check_ins"]),
    )
