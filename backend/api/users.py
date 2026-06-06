from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.profile import Profile
from backend.db.session import get_db
from backend.schemas.profile import ProfileIn, ProfileOut

from backend.middleware.auth import get_identity, owner_clause

router = APIRouter(prefix="/users", tags=["users"])


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
