"""Founder memory / long-term context persistence in Supabase."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from app.database import supabase


class MemoryService:
    """CRUD for founder memory / conversation context."""

    TABLE = "memories"

    async def create(
        self,
        content: str,
        category: str = "interaction",
        profile_id: UUID | None = None,
        session_id: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        data = {
            "profile_id": str(profile_id) if profile_id else None,
            "session_id": session_id,
            "category": category,
            "content": content,
            "metadata": metadata or {},
        }
        result = supabase.table(self.TABLE).insert(data).execute()
        return result.data[0] if result.data else {}

    async def get_by_profile(
        self, profile_id: UUID, limit: int = 50, category: str | None = None
    ) -> List[Dict[str, Any]]:
        query = (
            supabase.table(self.TABLE)
            .select("*")
            .eq("profile_id", str(profile_id))
            .order("created_at", desc=True)
            .limit(limit)
        )
        if category:
            query = query.eq("category", category)
        result = query.execute()
        return result.data or []

    async def get_by_session(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        result = (
            supabase.table(self.TABLE)
            .select("*")
            .eq("session_id", session_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    async def search_memories(
        self,
        profile_id: UUID,
        keyword: str,
        category: str | None = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Full-text search on memory content."""
        query = (
            supabase.table(self.TABLE)
            .select("*")
            .eq("profile_id", str(profile_id))
            .ilike("content", f"%{keyword}%")
            .order("created_at", desc=True)
            .limit(limit)
        )
        if category:
            query = query.eq("category", category)
        result = query.execute()
        return result.data or []

    async def get_profile_memory_summary(self, profile_id: UUID) -> str:
        """Get a text summary of all memories for this profile."""
        memories = await self.get_by_profile(profile_id, limit=50)
        if not memories:
            return ""
        lines = []
        for m in memories:
            cat = m.get("category", "note")
            content = m.get("content", "")
            lines.append(f"[{cat}] {content}")
        return "\n".join(lines)


memory_service = MemoryService()
