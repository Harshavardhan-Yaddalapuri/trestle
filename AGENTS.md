## Cursor Cloud specific instructions

### Overview

Trestle is an AI-powered conversational assistant for startup founders with two services:

| Service | Directory | Port | Command |
|---------|-----------|------|---------|
| Backend (FastAPI) | `backend/` | 8000 | `backend/.venv/bin/uvicorn backend.main:app --reload --port 8000` (run from repo root) |
| Frontend (Next.js 15) | `frontend/` | 3000 | `cd frontend && npm run dev` |

Data lives in **Supabase (cloud)**, not a local Postgres. On the Cloud VM, run the two services standalone (see below); Docker is not available there.

### Multi-developer workflow

This codebase has multiple contributors who may use different tools, npm versions, and OS environments. Do not modify lockfiles (`package-lock.json`, etc.) or auto-generated files (`next-env.d.ts`, etc.) unless the change is intentional and necessary.

### Startup caveats

- **Docker is NOT available on the Cloud VM**, and `docker-compose.yml` is currently broken anyway (its `build: ./backend` / `build: ./frontend` contexts have no Dockerfiles inside those dirs — the only Dockerfiles are the root `Dockerfile.api` / `Dockerfile.web`). Run the services standalone instead.
- **Backend** uses a Python venv at `backend/.venv` (created by the update script). Run it from the repo root: `backend/.venv/bin/uvicorn backend.main:app --reload --port 8000`, then `GET http://localhost:8000/health` → `{"status":"ok"}`. Only the `/health` endpoint is implemented today; the richer `app/` API (routers/middleware/database) referenced by docs and `backend/tests/` does not exist yet, so `pytest` fails on import.
- **Frontend** needs `frontend/.env.local` to boot — `middleware.ts` constructs a Supabase client on every request and throws a 500 if `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` are unset. For UI-only dev, set `NEXT_PUBLIC_DATA_SOURCE=mock` plus placeholder Supabase values (no network calls happen without a session). This file is gitignored; if it goes missing, recreate it. Real auth/login flows require a real Supabase project.
- **Mock vs API**: with `NEXT_PUBLIC_DATA_SOURCE=mock`, the entire hub (`/dashboard`, `/grants`, `/profile`, `/settings`, `/connections`, `/resources`) and `/search` render from local seed data with no backend needed.

### Known issue — the landing page currently breaks dev

`app/_sections/Nav.tsx` and the auth/login/signup pages import `@/lib/supabase`, but `frontend/lib/supabase.ts` is missing from `main` (only `lib/supabase-server.ts` exists — the client file was dropped in a merge). Consequences:
- The landing page `/` and auth pages (`/login`, `/signup`, `/auth/*`) return 500.
- Worse, visiting `/` triggers a hard webpack module-resolution error that **poisons the whole dev compilation**, so every other route then 500s until you restart `npm run dev`. While this is unfixed, avoid hitting `/`; go straight to `/dashboard` or `/grants`. Restoring `lib/supabase.ts` (a browser Supabase client exporting `supabase`) fixes it.

### Design system

The M3 design spec is documented in `docs/design-system.md`. Frontend components follow Material 3 conventions with the Grass Green palette.

### Lint & Test

- Frontend lint: `cd frontend && npm run lint` (or `npx eslint .`). Currently clean except one `no-page-custom-font` warning in `app/layout.tsx`.
- Backend: `pytest` is not installed and the test suite imports modules that don't exist yet (`app.main`, etc.), so it cannot run as-is.
