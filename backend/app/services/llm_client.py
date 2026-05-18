"""Ollama local LLM client — intent parsing, summarization, change detection."""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
import httpx
from app.config import settings

class OllamaClient:
    """Talk to local Ollama instance via HTTP API."""

    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None):
        self.model = model or settings.ollama_model
        self.base_url = base_url or settings.ollama_base_url

    async def generate(self, prompt: str, system: Optional[str] = None, max_tokens: int = 2048, temperature: float = 0.3) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system or "",
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "")

    async def chat(self, messages: List[Dict[str, str]], max_tokens: int = 2048, temperature: float = 0.3) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "")

    async def parse_json(self, prompt: str, system: Optional[str] = None, max_tokens: int = 2048) -> Dict[str, Any]:
        text = await self.generate(prompt, system=system, max_tokens=max_tokens, temperature=0.1)
        # Clean markdown code blocks
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        return json.loads(text)


_singleton: Optional[OllamaClient] = None


def get_llm() -> OllamaClient:
    global _singleton
    if _singleton is None:
        _singleton = OllamaClient()
    return _singleton
