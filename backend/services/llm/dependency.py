from __future__ import annotations

from backend.services.llm.deepseek import DeepseekClient


def get_llm_client() -> DeepseekClient:
    """FastAPI dependency returning the configured LLM client."""
    return DeepseekClient()
