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

### Alert worker

The arq alert worker is a separate process from the API. It handles three alert types:
- **Deadline reminders** — 14, 7, and 1 day before grant deadlines (cron: daily 13:00 UTC)
- **New grant matches** — when new grants are added that match a user's profile (cron: every 6 hours)
- **Check-ins** — for stale grant tracks with no lifecycle update in 14 days (cron: Monday 14:00 UTC)

Run locally:
```bash
arq backend.services.jobs.settings.WorkerSettings
```

Via Docker Compose (automatically started):
```bash
docker compose up worker
```

Admin trigger (manual scan + inline send, for testing):
```bash
curl -X POST http://localhost:8000/api/admin/alerts/trigger/check_in
curl -X POST http://localhost:8000/api/admin/alerts/trigger/deadline_reminder
curl -X POST http://localhost:8000/api/admin/alerts/trigger/new_grant_match
```

User alert preferences:
```bash
# GET current preferences (requires auth cookie)
curl http://localhost:8000/api/users/alert-preferences -H "Cookie: trestle_session=<token>"
# PUT partial update
curl -X PUT http://localhost:8000/api/users/alert-preferences \
  -H "Cookie: trestle_session=<token>" \
  -H "Content-Type: application/json" \
  -d '{"deadline_reminders": false}'
```

### Lint & Test

- Frontend: `cd frontend && npx eslint .`
- Backend: `cd backend && python -m pytest` (pytest + pytest-asyncio; config in `pyproject.toml` or `pytest.ini`)
