"""Quick smoke test of the intent classifier against the real Deepseek API.

Run from repo root:
    python -m backend.scripts.classify_demo

Skips gracefully if DEEPSEEK_API_KEY is not set.
"""
from __future__ import annotations

import asyncio
import sys

from backend.core.config import get_settings
from backend.core.logging import configure_logging
from backend.services.intent.classifier import classify
from backend.services.llm import DeepseekClient


SAMPLES = [
    "hi there!",
    "We just hired two engineers and moved to Austin, Texas",
    "Tell me more about the Activate Fellowship — when is the deadline?",
]


async def main() -> None:
    configure_logging()
    settings = get_settings()
    key = settings.DEEPSEEK_API_KEY.get_secret_value()

    if not key:
        print("skipped — no DEEPSEEK_API_KEY set")
        sys.exit(0)

    client = DeepseekClient()
    for msg in SAMPLES:
        print(f"\n>>> {msg!r}")
        result = await classify(msg, client)
        print(
            f"    intent={result.intent!r}  confidence={result.confidence:.2f}"
            f"  by={result.classified_by!r}"
        )
        if result.entities.model_dump(exclude_none=True, exclude={"action"}):
            print(f"    entities={result.entities.model_dump(exclude_none=True)}")


if __name__ == "__main__":
    asyncio.run(main())
