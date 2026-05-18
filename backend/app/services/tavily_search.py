"""Tavily web search — free tier, results with citations."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import httpx
from app.config import settings

class TavilyClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.tavily_api_key
        self.base_url = "https://api.tavily.com"

    async def search(self, query: str, search_depth: str = "advanced", max_results: int = 5, include_answer: bool = False) -> List[Dict[str, Any]]:
        """Search the web and return raw results."""
        if not self.api_key:
            return []
        url = f"{self.base_url}/search"
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": include_answer,
            "include_raw_content": True,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])


def get_tavily() -> TavilyClient:
    return TavilyClient()
