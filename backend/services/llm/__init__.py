from __future__ import annotations

from backend.services.llm.base import LLMClient
from backend.services.llm.deepseek import DeepseekClient
from backend.services.llm.multi_provider import MultiProviderClient, build_multi_provider_client

_singleton: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _singleton
    if _singleton is None:
        _singleton = build_multi_provider_client()
    return _singleton


__all__ = [
    "LLMClient",
    "get_llm_client",
    "DeepseekClient",
    "MultiProviderClient",
    "build_multi_provider_client",
]
