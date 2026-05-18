"""Auth routes — signup, login, refresh via Supabase."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.models.schemas import UserSignup, UserLogin, Token
from app.database import supabase

router = APIRouter()

@router.post("/signup")
async def signup(body: UserSignup) -> Token:
    res = supabase.auth.sign_up({"email": body.email, "password": body.password})
    if hasattr(res, "error") and res.error:
        raise HTTPException(status_code=400, detail=str(res.error))
    return Token(access_token=res.session.access_token)

@router.post("/login")
async def login(body: UserLogin) -> Token:
    res = supabase.auth.sign_in_with_password({"email": body.email, "password": body.password})
    if hasattr(res, "error") and res.error:
        raise HTTPException(status_code=401, detail=str(res.error))
    return Token(access_token=res.session.access_token)
