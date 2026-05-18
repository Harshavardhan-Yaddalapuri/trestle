"""Profile CRUD — auto-create on first auth, update via onboarding."""
from __future__ import annotations
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import ProfileCreate, ProfileUpdate, ProfileResponse
from app.middleware.auth import require_auth
from app.database import supabase

router = APIRouter()

@router.get("/me")
async def get_me(user: Dict[str, Any] = Depends(require_auth)):
    uid = user.get("id")
    row = supabase.table("profiles").select("*").eq("user_id", uid).maybe_single().execute()
    if not row.data:
        # Auto-create empty profile
        created = supabase.table("profiles").insert({"user_id": uid}).execute()
        return created.data[0]
    return row.data

@router.patch("/me")
async def update_me(body: ProfileUpdate, user: Dict[str, Any] = Depends(require_auth)):
    uid = user.get("id")
    data = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    res = supabase.table("profiles").update(data).eq("user_id", uid).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return res.data[0]

@router.get("/onboarding-steps")
async def onboarding_steps():
    """Return the conversational onboarding questionnaire."""
    return [
        {"field": "name", "question": "What's your name?", "type": "text", "required": True},
        {"field": "location", "question": "What city are you building in?", "type": "location", "required": True},
        {"field": "state", "question": "What state?", "type": "select", "options": ["Michigan", "Illinois", "Ohio", "Wisconsin", "Other"], "required": True},
        {"field": "stage", "question": "What stage is your startup at?", "type": "select", "options": ["idea", "pre-revenue", "seed", "series-a", "growth"], "required": True},
        {"field": "industry", "question": "What industry or technologies are you working with?", "type": "multiselect", "options": ["ai", "fintech", "healthcare", "mobility", "cleantech", "manufacturing", "consumer", "saas", "other"], "required": True},
        {"field": "funding_need", "question": "What kind of support are you looking for right now?", "type": "multiselect", "options": ["grants", "accelerator", "mentorship", "coworking", "hiring", "pitch_competition", "tax_credits"], "required": True},
        {"field": "goals", "question": "In one sentence: what's your biggest goal in the next 6 months?", "type": "text", "required": True},
    ]
