"""Per-user conversational memory — stores in Supabase, retrieved for context."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from uuid import UUID
from app.database import supabase
from app.models.schemas import MemoryCreate, MemoryResponse

class MemoryService:
    TABLE = "memories"

    async def create(self, data: MemoryCreate) -> MemoryResponse:
        payload = data.model_dump(exclude_unset=True)
        result = supabase.table(self.TABLE).insert(payload).execute()
        return MemoryResponse(**result.data[0])

    async def get_by_profile(self, profile_id: UUID, category: Optional[str] = None, limit: int = 20) -> List[MemoryResponse]:
        q = supabase.table(self.TABLE).select("*").eq("profile_id", str(profile_id)).order("created_at", desc=True).limit(limit)
        if category:
            q = q.eq("category", category)
        result = q.execute()
        return [MemoryResponse(**r) for r in result.data]

    async def get_recent(self, profile_id: UUID, limit: int = 10) -> List[MemoryResponse]:
        result = supabase.table(self.TABLE).select("*").eq("profile_id", str(profile_id)).order("created_at", desc=True).limit(limit).execute()
        return [MemoryResponse(**r) for r in result.data]

    async def search_semantic(self, profile_id: UUID, query: str, limit: int = 5) -> List[MemoryResponse]:
        """Simple keyword search over memory content."""
        # TODO: upgrade to vector search when pgvector is set up
        result = supabase.table(self.TABLE).select("*").eq("profile_id", str(profile_id)).ilike("content", f"%{query}%").limit(limit).execute()
        return [MemoryResponse(**r) for r in result.data]


memory_service = MemoryService()
