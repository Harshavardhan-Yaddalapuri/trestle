"""Supabase client + raw SQL for advanced queries."""
from __future__ import annotations
from supabase import create_client, Client
from app.config import settings

supabase: Client = create_client(settings.supabase_url, settings.supabase_service_key)
