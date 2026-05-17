"""Trestle backend — Founder Resource Discovery Engine API."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import search
from app.routers import scout

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    # Startup
    print("🚀 Trestle API starting up...")
    yield
    # Shutdown
    print("🛑 Trestle API shutting down...")

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Trestle",
    description="Founder Resource Discovery Engine — Michigan (and beyond)",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend origin + local dev
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://localhost:3000",
    "https://trestle.vercel.app",
    "https://trestle-ai.vercel.app",
]
# Allow override via env
extra_origins = os.getenv("CORS_ORIGINS", "")
if extra_origins:
    origins.extend(o.strip() for o in extra_origins.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(search.router, prefix="/api")
app.include_router(scout.router, prefix="/api")

# ---------------------------------------------------------------------------
# Health / root
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "trestle-api"}

@app.get("/")
async def root() -> dict:
    return {
        "name": "Trestle API",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "search": "POST /api/search",
            "scout": "POST /api/scout/run",
            "scout_status": "GET /api/scout/status",
        },
    }
