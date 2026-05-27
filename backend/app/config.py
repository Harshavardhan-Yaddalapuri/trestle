from __future__ import annotations
import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_service_key: str
    supabase_anon_key: Optional[str] = None
    # Ollama (local LLM)
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "mistral"
    # External services
    tavily_api_key: Optional[str] = None
    firecrawl_api_key: Optional[str] = None
    # Frontend
    frontend_url: str = "http://localhost:3000"
    # CORS
    cors_origins: Optional[str] = None

    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()
