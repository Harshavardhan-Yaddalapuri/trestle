from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import Settings
from backend.db.models.chat import Message
from backend.db.models.memory import AgentMemory
from backend.db.models.profile import Profile
from backend.schemas.intent import IntentResult
from backend.schemas.match import MatchProfile, MatchResponse
from backend.schemas.memory import MemoryContext
from backend.schemas.profile import ProfileOut
from backend.services.llm.base import LLMClient
from backend.services.llm.types import LLMMessage
from backend.services.memory.context import build_memory_context

_MAX_HISTORY_MESSAGES = 20
_HISTORY_MAX_AGE_DAYS = 7
_HISTORY_TOKEN_BUDGET = 3000
_CHARS_PER_TOKEN = 4


class TurnContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    session_id: str
    conversation_id: UUID
    user_message: str
    profile: ProfileOut
    memory: MemoryContext
    history: list[LLMMessage]
    intent: IntentResult
    match_context: MatchResponse | None = None
    llm_client: LLMClient
    settings: Settings
    db: AsyncSession


def profile_out_to_match_profile(profile: ProfileOut) -> MatchProfile:
    """Convert ProfileOut to MatchProfile for the question engine."""
    return MatchProfile(
        founder_name=profile.founder_name,
        company_name=profile.company_name,
        company_stage=profile.company_stage,
        industry=profile.industry,
        location=profile.location,
        one_liner=profile.one_liner,
        team_size=profile.team_size,
        has_technical_cofounder=profile.has_technical_cofounder,
        funding_raised_usd_cents=profile.funding_raised_usd_cents,
        funding_target_usd_cents=profile.funding_target_usd_cents,
        incorporated=profile.incorporated,
        incorporation_country=profile.incorporation_country,
        incorporation_state=profile.incorporation_state,
        regulatory_status=profile.regulatory_status,
    )


async def load_turn_context(
    session_id: str,
    conversation_id: UUID,
    user_message: str,
    intent: IntentResult,
    llm_client: LLMClient,
    settings: Settings,
    db: AsyncSession,
) -> TurnContext:
    # Load profile (synthetic empty if no row)
    profile_result = await db.execute(
        sa.select(Profile).where(Profile.session_id == session_id)
    )
    profile_row = profile_result.scalar_one_or_none()
    profile = (
        ProfileOut.model_validate(profile_row)
        if profile_row is not None
        else ProfileOut(session_id=session_id)
    )

    # Load active memories
    now = datetime.now(timezone.utc)
    mem_result = await db.execute(
        sa.select(AgentMemory).where(
            AgentMemory.session_id == session_id,
            AgentMemory.deleted_at.is_(None),
            sa.or_(AgentMemory.expires_at.is_(None), AgentMemory.expires_at > now),
        )
    )
    memories = list(mem_result.scalars().all())
    memory = build_memory_context(memories)

    # Load conversation history (last N messages, ≤7 days old)
    cutoff = now - timedelta(days=_HISTORY_MAX_AGE_DAYS)
    hist_result = await db.execute(
        sa.select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.created_at >= cutoff,
        )
        .order_by(Message.created_at.asc())
        .limit(_MAX_HISTORY_MESSAGES)
    )
    raw_messages = list(hist_result.scalars().all())

    # Apply token budget — drop oldest first
    history: list[LLMMessage] = []
    token_count = 0
    for msg in reversed(raw_messages):
        content = msg.content or ""
        tokens = max(1, len(content) // _CHARS_PER_TOKEN)
        if token_count + tokens > _HISTORY_TOKEN_BUDGET:
            break
        history.insert(0, LLMMessage(role=msg.role, content=content))
        token_count += tokens

    return TurnContext(
        session_id=session_id,
        conversation_id=conversation_id,
        user_message=user_message,
        profile=profile,
        memory=memory,
        history=history,
        intent=intent,
        llm_client=llm_client,
        settings=settings,
        db=db,
    )
