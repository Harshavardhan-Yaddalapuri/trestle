from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, search, scout, profile

origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://host.docker.internal:3000",
    os.getenv("FRONTEND_URL", ""),
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Trestle API starting...")
    yield
    print("🛑 Trestle API shutting down...")

app = FastAPI(
    title="Trestle",
    description="Founder Resource Discovery Engine — freshness-first",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in origins if o],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(profile.router, prefix="/api/profiles", tags=["profiles"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(scout.router, prefix="/api/scout", tags=["scout"])

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}
