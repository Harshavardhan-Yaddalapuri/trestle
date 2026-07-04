"""Orchestrator: runs every chat turn through the full intent→handler pipeline.

Entry point: run_turn(). Production code in api/chat.py calls this.
Tests use FakeLLMClient via dependency override and CHAT_USE_ORCHESTRATOR=True (default).
"""
from __future__ import annotations

import asyncio
import time
from typing import AsyncIterator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.config import Settings
from backend.core.errors import UpstreamError
from backend.core.logging import get_logger
from backend.db.models.memory import AgentMemory
from backend.schemas.intent import ExtractedEntities
from backend.services.intent.classifier import classify
from backend.services.llm.base import LLMClient
from backend.services.memory.extractor import extract_memory_candidates
from backend.services.orchestrator.context_loader import load_turn_context
from backend.services.orchestrator.entity_application import (
    CONFIDENCE_THRESHOLD,
    apply_entities_to_profile,
)
from backend.services.orchestrator.events import (
    FinishEvent,
    LLMTokenEvent,
    OrchestratorEvent,
)
from backend.services.orchestrator.router import route

logger = get_logger(__name__)


def _has_profile_entities(entities: ExtractedEntities) -> bool:
    return any([
        entities.stage,
        entities.location,
        entities.industries,
        entities.team_size is not None,
        entities.funding_amount_usd_cents is not None,
    ])


async def run_turn(
    session_id: str,
    conversation_id: UUID,
    user_message: str,
    llm_client: LLMClient,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> AsyncIterator[OrchestratorEvent]:
    """Main orchestrator entry point. Yields OrchestratorEvent objects.

    The caller (chat.py _run_producer) translates each event to the appropriate
    Redis Stream SSE event without changing the wire format.
    """
    start = time.monotonic()
    tool_calls_made: list[str] = []
    output_chars = 0

    async with session_factory() as db:
        # 1. Classify intent
        try:
            intent = await classify(user_message, llm_client)
        except UpstreamError:
            intent_json = '{"intent":"unknown","confidence":0.0,"entities":{}}'
            from backend.schemas.intent import ExtractedEntities, IntentResult
            intent = IntentResult(
                intent="unknown",
                confidence=0.0,
                entities=ExtractedEntities(),
                classified_by="llm",
            )

        # 2. Load turn context (profile, memories, history)
        ctx = await load_turn_context(
            session_id=session_id,
            conversation_id=conversation_id,
            user_message=user_message,
            intent=intent,
            llm_client=llm_client,
            settings=settings,
            db=db,
        )

        # 3. Extract and persist high-confidence memory candidates
        candidates = extract_memory_candidates(user_message, intent)
        for candidate in candidates:
            if candidate.confidence >= CONFIDENCE_THRESHOLD:
                db.add(AgentMemory(
                    session_id=session_id,
                    conversation_id=conversation_id,
                    kind=candidate.kind,
                    content=candidate.content,
                    structured=candidate.structured,
                    confidence=candidate.confidence,
                ))
        if any(c.confidence >= CONFIDENCE_THRESHOLD for c in candidates):
            await db.commit()

        # 4. Apply profile entities as a side effect for non-exclusive intents.
        # profile_update and correction handlers apply entities themselves
        # (with tool_call/tool_result tracking), so skip here to avoid double-apply.
        if intent.intent not in ("profile_update", "correction") and _has_profile_entities(intent.entities):
            await apply_entities_to_profile(
                session_id, intent.entities, intent.confidence, db
            )

        # 5. Route to handler
        handler = route(intent)
        handler_name = getattr(handler, "__name__", str(handler))

        # 6. Run handler with total turn timeout
        try:
            async with asyncio.timeout(settings.ORCHESTRATOR_TIMEOUT_SECONDS):
                async for event in handler(ctx):
                    if isinstance(event, LLMTokenEvent):
                        output_chars += len(event.delta)
                    elif hasattr(event, "name") and isinstance(event, FinishEvent.__class__):
                        pass
                    yield event
        except asyncio.TimeoutError:
            logger.warning(
                "orchestrator_timeout",
                session_id=session_id,
                handler=handler_name,
                elapsed_s=round(time.monotonic() - start, 2),
            )
            yield LLMTokenEvent(delta="\n\nSorry, I took too long. Please try again.")
            yield FinishEvent(reason="error")
            return

    # Logging
    duration_ms = int((time.monotonic() - start) * 1000)
    input_tokens_est = sum(
        max(1, len(m.content or "") // 4) for m in ctx.history
    ) + len(user_message) // 4
    output_tokens_est = max(1, output_chars // 4)
    cost_est = (
        input_tokens_est / 1_000_000 * settings.DEEPSEEK_INPUT_PRICE_PER_MTOK
        + output_tokens_est / 1_000_000 * settings.DEEPSEEK_OUTPUT_PRICE_PER_MTOK
    )

    logger.info(
        "orchestrator_turn",
        session_id=session_id,
        intent_label=intent.intent,
        intent_confidence=round(intent.confidence, 3),
        intent_classified_by=intent.classified_by,
        handler_name=handler_name,
        tool_calls=tool_calls_made,
        llm_input_tokens=input_tokens_est,
        llm_output_tokens=output_tokens_est,
        llm_cost_estimate_usd=round(cost_est, 6),
        duration_ms=duration_ms,
    )
