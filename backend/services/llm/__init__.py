from __future__ import annotations

from backend.services.llm.base import LLMClient
from backend.services.llm.deepseek import DeepseekClient

_singleton: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _singleton
    if _singleton is None:
        _singleton = DeepseekClient()
    return _singleton


__all__ = ["LLMClient", "get_llm_client", "DeepseekClient"]
