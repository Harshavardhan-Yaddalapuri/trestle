## Cursor Cloud specific instructions

### Overview

Trestle is an AI-powered conversational assistant for startup founders with two services:

| Service | Directory | Port | Command |
|---------|-----------|------|---------|
| Backend (FastAPI) | `backend/` | 8000 | Via `docker compose up api` or `uvicorn backend.main:app --reload --port 8000` |
| Frontend (Next.js 15) | `frontend/` | 3000 | `cd frontend && npm run dev` |

Docker Compose (`docker-compose.yml`) orchestrates all services including Postgres and Redis.

### Multi-developer workflow

This codebase has multiple contributors who may use different tools, npm versions, and OS environments. Do not modify lockfiles (`package-lock.json`, etc.) or auto-generated files (`next-env.d.ts`, etc.) unless the change is intentional and necessary.

### Startup caveats

- **Docker Compose** is the preferred way to run the full stack (`docker compose up`). The API depends on Postgres and Redis.
- **Frontend standalone**: `cd frontend && npm install && npm run dev` works independently on port 3000.
- **Backend standalone**: `uvicorn backend.main:app --reload --port 8000` works for the health endpoint without Docker, but database-dependent features need Postgres.

### Design system

The M3 design spec is documented in `docs/design-system.md`. Frontend components follow Material 3 conventions with the Grass Green palette.

### Lint & Test

- Frontend: `cd frontend && npx eslint .`
- Backend: `cd backend && python -m pytest` (pytest + pytest-asyncio; config in `pyproject.toml` or `pytest.ini`)
