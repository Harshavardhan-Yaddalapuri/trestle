from fastapi import APIRouter

from backend.api import chat, conversations, health, skills, users

api_router = APIRouter()
api_router.include_router(health.api_router)
api_router.include_router(chat.router)
api_router.include_router(conversations.router)
api_router.include_router(users.router)
api_router.include_router(skills.router)

__all__ = ["api_router", "chat", "conversations", "health", "skills", "users"]
