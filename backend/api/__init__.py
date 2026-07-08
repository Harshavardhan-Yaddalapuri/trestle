from fastapi import APIRouter

from backend.api import admin, auth, chat, conversations, email, events, grants, health, lifecycle, memory, skills, users

api_router = APIRouter()
api_router.include_router(health.api_router)
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(conversations.router)
api_router.include_router(users.router)
api_router.include_router(skills.router)
api_router.include_router(grants.router)
api_router.include_router(events.router)
api_router.include_router(lifecycle.router)
api_router.include_router(admin.router)
api_router.include_router(memory.router)
api_router.include_router(email.router)

__all__ = [
    "api_router",
    "admin",
    "auth",
    "chat",
    "conversations",
    "email",
    "events",
    "grants",
    "health",
    "lifecycle",
    "memory",
    "skills",
    "users",
]
