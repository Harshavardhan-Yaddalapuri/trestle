"""Stub LLM token generator. Used in tests via dep-override (CHAT_USE_ORCHESTRATOR=False).
Production uses orchestrator.run_turn (CHAT_USE_ORCHESTRATOR=True).

Emits whitespace-delimited tokens with a small sleep so the SSE stream is
observably wall-clock-paced, not buffered.
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

TOKEN_DELAY_SECONDS = 0.05


async def stub_token_stream(user_content: str) -> AsyncIterator[str]:
    reply = f"You said: {user_content.strip()} (stubbed response)"
    tokens = reply.split(" ")
    for i, tok in enumerate(tokens):
        await asyncio.sleep(TOKEN_DELAY_SECONDS)
        yield tok if i == 0 else " " + tok
