"""Firecrawl scraping integration for extracting structured data from resource URLs."""
from __future__ import annotations

from typing import Any, Dict, Optional
import httpx

from app.config import settings

FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"


class FirecrawlScraper:
    """Firecrawl client for scraping resource pages."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.firecrawl_api_key
        if not self.api_key:
            raise ValueError("FIRECRAWL_API_KEY not set")

    async def scrape(
        self,
        url: str,
        formats: list[str] | None = None,
    ) -> Dict[str, Any]:
        """Scrape a URL and return structured content."""
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"url": url}
        if formats:
            payload["formats"] = formats
        else:
            payload["formats"] = ["markdown"]

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{FIRECRAWL_BASE}/scrape",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("success") and data.get("data"):
            return data["data"]
        return {"url": url, "markdown": "", "metadata": {}}

    async def extract_resource_info(self, url: str) -> Dict[str, Any]:
        """Scrape a resource URL and return structured info for our DB."""
        data = await self.scrape(url, formats=["markdown"])
        markdown = data.get("markdown", "")
        meta = data.get("metadata", {})

        return {
            "title": meta.get("title", "Untitled"),
            "description": meta.get("description", markdown[:500] if markdown else ""),
            "url": url,
            "last_scraped": meta.get("scrapedAt"),
            "source_markdown": markdown[:2000] if markdown else "",
        }


# Singleton
firecrawl_client: FirecrawlScraper | None = None


def get_firecrawl() -> FirecrawlScraper:
    global firecrawl_client
    if firecrawl_client is None:
        firecrawl_client = FirecrawlScraper()
    return firecrawl_client
