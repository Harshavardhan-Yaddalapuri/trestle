"""Resource CRUD + structured search against Supabase."""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from app.database import supabase
from app.models.schemas import ResourceCreate, ResourceResponse

class ResourceService:
    TABLE = "resources"

    async def create(self, resource: ResourceCreate) -> ResourceResponse:
        data = resource.model_dump(exclude_unset=True)
        result = supabase.table(self.TABLE).insert(data).execute()
        return ResourceResponse(**result.data[0])

    async def create_many(self, resources: List[ResourceCreate]) -> List[ResourceResponse]:
        if not resources:
            return []
        data = [r.model_dump(exclude_unset=True) for r in resources]
        result = supabase.table(self.TABLE).insert(data).execute()
        return [ResourceResponse(**r) for r in result.data]

    async def get_all(self, limit: int = 200, status: str = "active") -> List[ResourceResponse]:
        result = supabase.table(self.TABLE).select("*").eq("status", status).limit(limit).execute()
        return [ResourceResponse(**r) for r in result.data]

    async def get_by_id(self, resource_id: UUID) -> Optional[ResourceResponse]:
        result = supabase.table(self.TABLE).select("*").eq("id", str(resource_id)).maybe_single().execute()
        if result.data:
            return ResourceResponse(**result.data)
        return None

    async def get_by_url(self, url: str) -> Optional[ResourceResponse]:
        result = supabase.table(self.TABLE).select("*").eq("url", url).maybe_single().execute()
        if result.data:
            return ResourceResponse(**result.data)
        return None

    async def search_structured(
        self, query_text: Optional[str] = None,
        location: Optional[str] = None, resource_type: Optional[str] = None,
        stage: Optional[str] = None, industry: Optional[str] = None,
        status: str = "active", limit: int = 20
    ) -> List[ResourceResponse]:
        sup = supabase.table(self.TABLE).select("*").eq("status", status)
        if resource_type:
            sup = sup.eq("type", resource_type)
        if location:
            sup = sup.contains("location", [location])
        if stage:
            sup = sup.contains("stage", [stage])
        if industry:
            sup = sup.contains("industry", [industry])
        if query_text:
            sup = sup.or_(f"name.ilike.%{query_text}%,description.ilike.%{query_text}%")
        result = sup.limit(limit).execute()
        return [ResourceResponse(**r) for r in result.data]

    async def search_by_intent(self, intent: Dict[str, Any], limit: int = 10) -> List[ResourceResponse]:
        """Heuristic scoring based on intent."""
        location = intent.get("location") or intent.get("state")
        resource_type = intent.get("need_type")
        stage = intent.get("stage")
        industry = intent.get("industry", [])
        demographics = intent.get("demographics", [])

        resources = await self.get_all(limit=200)
        scored: List[tuple[float, ResourceResponse]] = []

        for r in resources:
            score = 0.0
            if resource_type and r.type == resource_type:
                score += 4.0
            if location and r.location:
                loc_lower = [l.lower() for l in r.location]
                if location.lower() in loc_lower:
                    score += 3.0
                elif any(location.lower() in ll for ll in loc_lower):
                    score += 1.5
            if stage and r.stage:
                stage_lower = [s.lower() for s in r.stage]
                if stage.lower() in stage_lower:
                    score += 2.0
            if industry and r.industry:
                ind_lower = [i.lower() for i in r.industry]
                for ind in industry:
                    if ind.lower() in ind_lower:
                        score += 1.5
            if demographics and r.demographics:
                demo_lower = [d.lower() for d in r.demographics]
                for demo in demographics:
                    if demo.lower() in demo_lower:
                        score += 2.0
            if r.status == "active":
                score += 0.5
            if score > 0:
                scored.append((score, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:limit]]

    async def upsert_from_scrape(self, resource: ResourceCreate, raw_content: str) -> ResourceResponse:
        """Create or update a resource from scraped data."""
        existing = await self.get_by_url(resource.url or "")
        source_hash = hashlib.sha256((raw_content or "").encode()).hexdigest()[:16]
        now = datetime.now(timezone.utc).isoformat()

        data = {
            **resource.model_dump(exclude_unset=True),
            "last_scraped": now,
            "last_verified": now,
            "source_hash": source_hash,
        }

        if existing:
            result = supabase.table(self.TABLE).update(data).eq("id", str(existing.id)).execute()
        else:
            result = supabase.table(self.TABLE).insert(data).execute()

        return ResourceResponse(**result.data[0])

    async def get_freshness_report(self) -> Dict[str, Any]:
        result = supabase.table(self.TABLE).select("status,last_scraped,last_verified").execute()
        counts = {"active": 0, "stale": 0, "dead": 0, "pending_review": 0, "total": 0}
        never_scraped = 0
        for r in result.data:
            counts[r.get("status", "active")] += 1
            counts["total"] += 1
            if not r.get("last_scraped"):
                never_scraped += 1
        return {**counts, "never_scraped": never_scraped}


resource_service = ResourceService()
