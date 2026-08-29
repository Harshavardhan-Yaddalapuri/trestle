from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.profile import Profile
from backend.db.models.user import User
from backend.db.session import get_db
from backend.middleware.auth import get_identity, owner_clause
from backend.schemas.alerts import AlertPreferencesIn, AlertPreferencesOut
from backend.schemas.profile import ProfileIn, ProfileOut

router = APIRouter(prefix="/users", tags=["users"])

_PREF_DEFAULTS = {
    "deadline_reminders": True,
    "new_grant_matches": True,
    "check_ins": True,
}


async def _alert_preferences_owner(request: Request, db: AsyncSession) -> User | None:
    """Resolve a real user when authenticated or a stable demo owner by session."""
    current_user = getattr(request.state, "user", None)
    if current_user is not None:
        result = await db.execute(sa.select(User).where(User.id == current_user.id))
        return result.scalar_one_or_none()

    _, session_id = get_identity(request)
    result = await db.execute(sa.select(User).where(User.sub == f"anonymous:{session_id}"))
    return result.scalar_one_or_none()


@router.get("/profile", response_model=ProfileOut)
async def get_profile(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
    user_id, session_id = get_identity(request)
    clause = owner_clause(Profile.user_id, Profile.session_id, request)

    result = await db.execute(
        sa.select(Profile).where(clause)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        return ProfileOut(session_id=session_id, user_id=user_id)

    return ProfileOut.model_validate(profile)


@router.put("/profile", response_model=ProfileOut)
async def upsert_profile(
    request: Request,
    body: ProfileIn,
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
    user_id, session_id = get_identity(request)
    fields = body.model_dump(exclude_unset=True)
    if user_id:
        fields["user_id"] = user_id

    conn = await db.connection()
    is_postgres = conn.dialect.name == "postgresql"

    if is_postgres:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        now = sa.func.now()
        stmt = pg_insert(Profile).values(
            id=uuid.uuid4(),
            session_id=session_id,
            user_id=user_id,
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
        clause = owner_clause(Profile.user_id, Profile.session_id, request)
        result = await db.execute(
            sa.select(Profile).where(clause)
        )
        profile = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if profile is None:
            profile = Profile(
                session_id=session_id,
                user_id=user_id,
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

    clause = owner_clause(Profile.user_id, Profile.session_id, request)
    result = await db.execute(
        sa.select(Profile).where(clause)
    )
    profile = result.scalar_one()
    return ProfileOut.model_validate(profile)


@router.get("/alert-preferences", response_model=AlertPreferencesOut)
async def get_alert_preferences(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AlertPreferencesOut:
    user = await _alert_preferences_owner(request, db)

    if user is None:
        # User row not yet provisioned — return defaults.
        return AlertPreferencesOut(
            deadline_reminders=_PREF_DEFAULTS["deadline_reminders"],
            new_grant_matches=_PREF_DEFAULTS["new_grant_matches"],
            check_ins=_PREF_DEFAULTS["check_ins"],
        )

    prefs = user.alert_prefs or {}
    return AlertPreferencesOut(
        deadline_reminders=prefs.get("deadline_reminders", _PREF_DEFAULTS["deadline_reminders"]),
        new_grant_matches=prefs.get("new_grant_matches", _PREF_DEFAULTS["new_grant_matches"]),
        check_ins=prefs.get("check_ins", _PREF_DEFAULTS["check_ins"]),
    )


@router.put("/alert-preferences", response_model=AlertPreferencesOut)
async def update_alert_preferences(
    body: AlertPreferencesIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AlertPreferencesOut:
    user = await _alert_preferences_owner(request, db)

    if user is None:
        current_user = getattr(request.state, "user", None)
        _, session_id = get_identity(request)
        # Keep anonymous preferences in the existing preference store while
        # leaving founder/company fields solely on Profile.
        user = User(
            id=(
                current_user.id
                if current_user is not None
                else uuid.uuid5(uuid.NAMESPACE_URL, f"trestle:{session_id}")
            ),
            sub=(
                current_user.sub
                if current_user is not None
                else f"anonymous:{session_id}"
            ),
            email=current_user.email if current_user is not None else None,
            alert_prefs={},
        )
        db.add(user)

    update = body.model_dump(exclude_unset=True, exclude_none=True)
    existing = dict(user.alert_prefs or {})
    existing.update(update)
    user.alert_prefs = existing
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return AlertPreferencesOut(
        deadline_reminders=existing.get("deadline_reminders", _PREF_DEFAULTS["deadline_reminders"]),
        new_grant_matches=existing.get("new_grant_matches", _PREF_DEFAULTS["new_grant_matches"]),
        check_ins=existing.get("check_ins", _PREF_DEFAULTS["check_ins"]),
    )
