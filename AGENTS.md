## Cursor Cloud specific instructions

### Overview

Trestle is an AI-powered founder resource discovery engine with two services:

| Service | Directory | Port | Command |
|---------|-----------|------|---------|
| Backend (FastAPI) | `backend/` | 8000 | `cd backend && ../.venv/bin/uvicorn app.main:app --reload --port 8000` |
| Frontend (Next.js 16) | `frontend/` | 3000 | `cd frontend && npm run dev` |

The Makefile has convenience targets: `make dev-be`, `make dev-fe`, `make install`, `make seed`, `make test`.

### Multi-developer workflow

This codebase has multiple contributors who may use different tools, npm versions, and OS environments. Do not modify lockfiles (`package-lock.json`, etc.) or auto-generated files (`next-env.d.ts`, etc.) unless the change is intentional and necessary. Differences in tooling versions can produce cosmetic diffs (e.g. `libc` metadata fields in lockfiles) that create noise for other developers.

### Startup caveats

- **Supabase is required at import time.** The backend will crash on startup if `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are not set in `backend/.env`. These must be valid (the key must be a valid JWT). Without real Supabase credentials, the server starts but database-dependent endpoints (`/api/api/search`, `/api/scout/run`) return 500 errors.
- **Double API prefix.** The search router declares its own `/api/search` prefix and the app mounts it at `/api`, so the actual search path is `POST /api/api/search` (not `/api/search`). The scout endpoints are at `/api/scout/run` and `/api/scout/status`.
- **python3.12-venv** must be installed via apt before creating the venv (`sudo apt-get install -y python3.12-venv`). The update script handles this.
- **pytest** is not in `requirements.txt` but is needed for `make test`. The update script installs it.

### Lint

- Frontend: `cd frontend && npx eslint .` (existing lint warnings/errors in the codebase are pre-existing, not introduced by setup)
- Backend: no linter is configured in the repo

### Tests

- Backend: `cd backend && ../.venv/bin/python -m pytest tests/ -v` (no test files exist yet; Makefile target echoes "No tests yet")
- Frontend: no test framework is configured
