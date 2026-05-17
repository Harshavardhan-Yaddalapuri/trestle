"""Tavily search integration for discovery of Michigan startup resources."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
import httpx

from app.config import settings

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class TavilySearch:
    """Tavily search client for discovering grants, accelerators, events, etc."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.tavily_api_key
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY not set")

    async def search(
        self,
        query: str,
        search_depth: str = "basic",
        max_results: int = 5,
        include_domains: List[str] | None = None,
        exclude_domains: List[str] | None = None,
    ) -> List[Dict[str, Any]]:
        """Run a Tavily search and return cleaned results."""
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
        }
        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(TAVILY_SEARCH_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        return [
            {
                "title": r.get("title", "Untitled"),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
                "score": r.get("score", 0.0),
                "published_date": r.get("published_date"),
            }
            for r in results
            if r.get("url")
        ]

    async def discover_michigan_resources(
        self, resource_type: str | None = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for a specific type of Michigan resource."""
        query_map = {
            "grant": "Michigan startup grants 2025 2026 funding",
            "accelerator": "Michigan startup accelerators incubator program",
            "pitch_competition": "Michigan pitch competition startup contest 2025",
            "coworking": "Michigan coworking space startup office",
            "event": "Michigan startup event conference 2025",
            "mentorship": "Michigan startup mentorship program advisor",
            "tax_credit": "Michigan business tax credit startup incentive",
            "hiring_program": "Michigan startup hiring workforce program",
        }
        query = query_map.get(resource_type, "Michigan startup small business resources 2025 2026")
        return await self.search(query=query, search_depth="advanced", max_results=limit)


# Singleton
tavily_client: TavilySearch | None = None


def get_tavily() -> TavilySearch:
    """Lazy-init singleton."""
    global tavily_client
    if tavily_client is None:
        tavily_client = TavilySearch()
    return tavily_client
