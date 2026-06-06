from __future__ import annotations

from backend.services.llm import get_llm_client as _get_singleton_client
from backend.services.llm.base import LLMClient


def get_llm_client() -> LLMClient:
    """FastAPI dependency returning the configured multi-provider LLM client."""
    return _get_singleton_client()
