"""Firecrawl — deep page scraping with markdown output."""
from __future__ import annotations
from typing import Any, Dict, Optional
import httpx
from app.config import settings

class FirecrawlClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.firecrawl_api_key
        self.base_url = "https://api.firecrawl.dev/v1"

    async def scrape(self, url: str, formats: Optional[list] = None) -> Dict[str, Any]:
        """Scrape a single URL and return structured data."""
        if not self.api_key:
            raise RuntimeError("Firecrawl API key not configured")
        endpoint = f"{self.base_url}/scrape"
        payload = {
            "url": url,
            "formats": formats or ["markdown", "html"],
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    async def crawl(self, url: str, limit: int = 10) -> Dict[str, Any]:
        """Crawl a site with link depth limit."""
        if not self.api_key:
            raise RuntimeError("Firecrawl API key not configured")
        endpoint = f"{self.base_url}/crawl"
        payload = {"url": url, "limit": limit}
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()


def get_firecrawl() -> FirecrawlClient:
    return FirecrawlClient()
