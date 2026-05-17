"""Resource CRUD + semantic search against Supabase."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.database import supabase
from app.models.schemas import ResourceCreate, ResourceResponse


class ResourceService:
    """CRUD and search for startup resources."""

    TABLE = "resources"

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

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

    async def get_all(self, limit: int = 100, status: str | None = "active") -> List[ResourceResponse]:
        query = supabase.table(self.TABLE).select("*").limit(limit)
        if status:
            query = query.eq("status", status)
        result = query.execute()
        return [ResourceResponse(**r) for r in result.data]

    async def get_by_id(self, resource_id: UUID) -> ResourceResponse | None:
        result = supabase.table(self.TABLE).select("*").eq("id", str(resource_id)).execute()
        if result.data:
            return ResourceResponse(**result.data[0])
        return None

    async def get_by_type(self, resource_type: str, limit: int = 50) -> List[ResourceResponse]:
        result = (
            supabase.table(self.TABLE)
            .select("*")
            .eq("type", resource_type)
            .eq("status", "active")
            .limit(limit)
            .execute()
        )
        return [ResourceResponse(**r) for r in result.data]

    async def update(self, resource_id: UUID, data: Dict[str, Any]) -> ResourceResponse:
        result = (
            supabase.table(self.TABLE)
            .update({**data, "updated_at": "now()"})
            .eq("id", str(resource_id))
            .execute()
        )
        return ResourceResponse(**result.data[0])

    async def delete(self, resource_id: UUID) -> bool:
        result = supabase.table(self.TABLE).delete().eq("id", str(resource_id)).execute()
        return bool(result.data)

    # ------------------------------------------------------------------
    # Structured filtering (text search + metadata filters)
    # ------------------------------------------------------------------

    async def search_structured(
        self,
        query_text: str | None = None,
        location: str | None = None,
        resource_type: str | None = None,
        stage: str | None = None,
        industry: str | None = None,
        status: str = "active",
        limit: int = 20,
    ) -> List[ResourceResponse]:
        """Text + metadata filter search — no semantic/vector yet."""
        sup = supabase.table(self.TABLE).select("*").eq("status", status)

        if resource_type:
            sup = sup.eq("type", resource_type)
        if location:
            # array overlap with location column
            sup = sup.contains("location", [location])
        if stage:
            sup = sup.contains("stage", [stage])
        if industry:
            sup = sup.contains("industry", [industry])
        if query_text:
            sup = sup.or_(f"name.ilike.%{query_text}%,description.ilike.%{query_text}%")

        result = sup.limit(limit).execute()
        return [ResourceResponse(**r) for r in result.data]

    async def search_by_query_parsed(
        self,
        intent: Dict[str, Any],
        limit: int = 10,
    ) -> List[ResourceResponse]:
        """Search using parsed intent — the main search logic."""
        # Expand search criteria
        location = intent.get("location") or intent.get("state")
        resource_type = intent.get("need_type")
        stage = intent.get("stage")
        industry = intent.get("industry", [])

        resources = await self.get_all(limit=200)
        results: List[ResourceResponse] = []
        scored: List[tuple[float, ResourceResponse]] = []

        for r in resources:
            score = 0.0

            # Type match (highest weight)
            if resource_type and r.type == resource_type:
                score += 4.0
            elif resource_type and resource_type in (r.data or {}).get("tags", []):
                score += 2.0

            # Location match
            if location and r.location:
                loc_lower = [l.lower() for l in r.location]
                if location.lower() in loc_lower:
                    score += 3.0
                elif any(location.lower() in ll for ll in loc_lower):
                    score += 1.5

            # Stage match
            if stage and r.stage:
                stage_lower = [s.lower() for s in r.stage]
                if stage.lower() in stage_lower:
                    score += 2.0

            # Industry match
            if industry and r.industry:
                ind_lower = [i.lower() for i in r.industry]
                for ind in industry:
                    if ind.lower() in ind_lower:
                        score += 1.5

            # Demographics match
            demographics = intent.get("demographics", [])
            if demographics and r.demographics:
                demo_lower = [d.lower() for d in r.demographics]
                for demo in demographics:
                    if demo.lower() in demo_lower:
                        score += 2.0

            # Boost active resources
            if r.status == "active":
                score += 0.5

            if score > 0:
                scored.append((score, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:limit]]

    async def get_freshness_report(self) -> Dict[str, Any]:
        """Return counts of active/stale/dead resources."""
        result = supabase.table(self.TABLE).select("status").execute()
        counts = {"active": 0, "stale": 0, "dead": 0, "pending_review": 0}
        for r in result.data:
            counts[r.get("status", "active")] += 1
        return counts


resource_service = ResourceService()
