"""LLM client: IBM Watsonx primary, OpenAI fallback."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
import httpx

from app.config import settings


class LLMClient:
    """Unified LLM client — IBM Watsonx primary, OpenAI fallback."""

    def __init__(self):
        # Track which backend is active
        self.provider = "none"
        self._openai_key = settings.openai_api_key
        self._watsonx_key = settings.watsonx_api_key
        self._watsonx_project = settings.watsonx_project_id
        self._watsonx_url = settings.watsonx_url

    async def _watsonx_generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.3) -> str:
        """Generate text using IBM watsonx Granite."""
        # First get IAM token
        token_url = "https://iam.cloud.ibm.com/identity/token"
        token_data = {
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": self._watsonx_key,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            token_resp = await client.post(token_url, data=token_data)
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]

        # Generate
        gen_url = f"{self._watsonx_url}/ml/v1/text/generation"
        payload = {
            "model_id": "ibm/granite-3-2-8b-instruct",
            "project_id": self._watsonx_project,
            "input": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "decoding_method": "greedy",
            },
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(gen_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        # Extract text
        results = data.get("results", [{}])
        if results:
            return results[0].get("generated_text", "")
        return ""

    async def _openai_generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.3) -> str:
        """Generate text using OpenAI (fallback)."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._openai_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.3) -> str:
        """Generate text — tries Watsonx first, falls back to OpenAI."""
        if self._watsonx_key and self._watsonx_project and self._watsonx_project != "your-project-id-here":
            try:
                result = await self._watsonx_generate(prompt, max_tokens, temperature)
                self.provider = "watsonx"
                return result
            except Exception:
                pass  # Fall through to OpenAI

        if self._openai_key:
            result = await self._openai_generate(prompt, max_tokens, temperature)
            self.provider = "openai"
            return result

        raise RuntimeError("No LLM provider configured")

    async def parse_json(self, prompt: str, max_tokens: int = 512, temperature: float = 0.3) -> Dict[str, Any]:
        """Generate text and parse as JSON."""
        text = await self.generate(prompt, max_tokens, temperature)
        # Clean up potential markdown code blocks
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        return json.loads(text)


# Singleton
_llm_client: LLMClient | None = None


def get_llm() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
