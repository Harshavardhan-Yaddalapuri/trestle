"""Supabase JWT verification middleware."""
from __future__ import annotations
import jwt
from datetime import datetime, timezone
from typing import Dict, Optional
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict]:
    """Extract and verify Supabase JWT. Returns user dict or None for anon."""
    if not credentials:
        return None
    token = credentials.credentials
    try:
        # Get Supabase public key using anonymous key
        import httpx
        url = f"{settings.supabase_url}/auth/v1/verify"
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None

async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict:
    user = await get_current_user(credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
