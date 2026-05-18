"""Smart scraper — firecrawl + tavily + diff + change detection."""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.services.firecrawl_scraper import get_firecrawl
from app.services.tavily_search import get_tavily
from app.services.llm_client import get_llm
from app.services.resource_service import resource_service
from app.models.schemas import ResourceCreate, FetchedResource, ScoutChanges

class ScraperService:
    """Fetch, parse, diff, and summarize changes from web sources."""

    async def fetch_and_parse(self, url: str) -> Dict[str, Any]:
        """Use Firecrawl to deep-scrape a single URL."""
        fc = get_firecrawl()
        try:
            data = await fc.scrape(url, formats=["markdown", "html"])
            result = data.get("data", data)
            return {
                "markdown": result.get("markdown", ""),
                "html": result.get("html", ""),
                "title": result.get("metadata", {}).get("title", ""),
                "status_code": result.get("metadata", {}).get("statusCode", 200),
            }
        except Exception as e:
            return {"error": str(e), "markdown": "", "html": "", "title": "", "status_code": 0}

    async def search_tavily(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Use Tavily to find relevant URLs."""
        tav = get_tavily()
        try:
            results = await tav.search(query, max_results=max_results, include_answer=False)
            return results
        except Exception:
            return []

    async def discover(self, intent: Dict[str, Any], max_results: int = 10) -> List[Dict[str, Any]]:
        """Discover resources via Tavily search for fresh URLs."""
        query_parts = filter(None, [
            intent.get("need_type"),
            intent.get("location"),
            intent.get("state"),
            intent.get("stage"),
        ] + (intent.get("keywords", [])))
        query = " ".join(query_parts) + " startup resources"
        results = await self.search_tavily(query, max_results=max_results)
        return [
            {
                "url": r.get("url"),
                "title": r.get("title"),
                "snippet": r.get("content", "")[:500],
                "score": r.get("score", 0),
                "source": "tavily",
            }
            for r in results if r.get("url")
        ]

    async def diff_url(self, url: str) -> Optional[ScoutChanges]:
        """Check if a known URL has changed. Returns a ChangeSummary or None."""
        existing = await resource_service.get_by_url(url)
        if not existing:
            return None

        fresh = await self.fetch_and_parse(url)
        if "error" in fresh:
            return ScoutChanges(
                resource_id=str(existing.id),
                url=url,
                change_type="removed",
                summary=f"Page is no longer reachable: {fresh['error']}",
                detected_at=datetime.now(timezone.utc),
            )

        old_hash = existing.source_hash or ""
        new_hash = hashlib.sha256((fresh["markdown"] or "").encode()).hexdigest()[:16]

        if old_hash == new_hash:
            return None  # No change

        # Use LLM to summarize changes
        llm = get_llm()
        prompt = f"""Summarize the meaningful changes between the old and new versions of this web page.
        Focus on: deadlines, eligibility, funding amounts, contact info, application status.

        Old page (first 2000 chars): {(existing.description or "")[:2000]}
        New page (first 2000 chars): {fresh["markdown"][:2000]}

        Respond with a single sentence summary."""
        try:
            summary = await llm.generate(prompt, max_tokens=150)
        except Exception:
            summary = "Content has changed — details may need review."

        return ScoutChanges(
            resource_id=str(existing.id),
            url=url,
            change_type="modified",
            summary=summary.strip(),
            detected_at=datetime.now(timezone.utc),
        )

    async def scrape_new_resource(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a fresh URL and return structured resource data."""
        data = await self.fetch_and_parse(url)
        if "error" in data or not data.get("markdown"):
            return None

        # Use LLM to extract structured fields
        llm = get_llm()
        prompt = f"""Extract structured startup resource data from this web page.
        Return valid JSON with these fields:
        {{
            "name": "program name",
            "type": "grant|accelerator|pitch_competition|event|coworking|mentorship|tax_credit|hiring_program|other",
            "description": "2-3 sentence summary",
            "url": "page URL",
            "application_url": "application URL if found, else same as url",
            "location": ["city", "state"],
            "industry": ["relevant industries"],
            "stage": ["relevant stages"],
            "deadline": "YYYY-MM-DD or null",
            "prize_amount": "funding amount or null",
            "eligibility": {{"key": "value"}}
        }}

        Page title: {data['title']}
        Page content: {data['markdown'][:3000]}
        """
        try:
            parsed = await llm.parse_json(prompt)
            resource = ResourceCreate(**parsed)
            saved = await resource_service.upsert_from_scrape(resource, data["markdown"])
            return {"resource": saved, "status": "new"}
        except Exception as e:
            return {"error": str(e), "url": url}


scraper_service = ScraperService()
