from fastapi import APIRouter

from backend.api import admin, chat, conversations, grants, health, memory, skills, users

api_router = APIRouter()
api_router.include_router(health.api_router)
api_router.include_router(chat.router)
api_router.include_router(conversations.router)
api_router.include_router(users.router)
api_router.include_router(skills.router)
api_router.include_router(grants.router)
api_router.include_router(admin.router)
api_router.include_router(memory.router)

__all__ = ["api_router", "admin", "chat", "conversations", "grants", "health", "memory", "skills", "users"]
