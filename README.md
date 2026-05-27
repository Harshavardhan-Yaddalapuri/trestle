# Trestle

> **Conversational AI agent for startup founders.** Finds grants, accelerators, and resources you're actually eligible for — not a firehose of irrelevant links.

Trestle is a personal assistant that learns about your startup through natural conversation and proactively surfaces matching opportunities. Built for founders who don't have time to fill out 80-question forms.

## Architecture

| Layer | Stack |
|-------|-------|
| **Frontend** | Next.js 15 (App Router) + Tailwind CSS v4 + shadcn/ui |
| **Backend** | FastAPI + Supabase (PostgreSQL + Auth) |
| **LLM** | Ollama (local) — DeepSeek v4 Pro |
| **Infra** | Docker Compose (frontend, backend, Redis) |

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) + docker compose
- [Ollama](https://ollama.com) running locally with a model pulled
- [Supabase](https://supabase.com) project (free tier)
- Node.js 20+ and Python 3.11+ (for local dev without Docker)

### 1. Clone & configure

```bash
git clone https://github.com/Harshavardhan-Yaddalapuri/trestle.git
cd trestle
cp .env.example .env
# Edit .env with your Supabase URL, service key, and anon key
```

### 2. Start the stack

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Health check | http://localhost:8000/health |

### 3. Set up the database

1. Go to your Supabase project → SQL Editor
2. Run `backend/migrations/001_initial_schema.sql`
3. (Optional) Seed grant data: `cd backend && python scripts/seed_grants.py`

### 4. Register auth redirects

In Supabase Dashboard → Auth → URL Configuration:
- **Site URL:** `http://localhost:3000`
- **Redirect URLs:** `http://localhost:3000/auth/callback`

## User Flow

```
Landing page → Sign up / Login → Dashboard (conversational agent)
                                    ├─ Ask about grants
                                    ├─ Agent matches eligibility
                                    ├─ Save / track grants
                                    └─ Get proactive alerts
```

## Project Structure

```
trestle/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory
│   │   ├── config.py            # Pydantic settings
│   │   ├── database.py          # Supabase client
│   │   ├── middleware/          # JWT auth, CORS
│   │   ├── models/              # Pydantic schemas
│   │   ├── routers/             # auth, profile, search, scout
│   │   └── services/            # LLM, intent parser, scraping, memory
│   ├── migrations/              # SQL schema migrations
│   ├── scripts/                 # Seed data, utilities
│   ├── tests/                   # pytest suite
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Landing page
│   │   ├── login/page.tsx       # Email+password login
│   │   ├── signup/page.tsx      # Account creation
│   │   ├── dashboard/page.tsx   # Chat interface (authed)
│   │   ├── search/              # Demo chat (unauthed)
│   │   ├── auth/                # Auth callback, logout, verify
│   │   └── _sections/           # Landing page components
│   ├── components/ui/           # shadcn/ui components
│   ├── lib/                     # API client, Supabase, session, SSE
│   └── middleware.ts            # Auth session refresh
├── docs/                        # Design docs, PRD, architecture
├── docker-compose.yml
└── .env.example
```

## Security Notes

- **Never commit `.env` files** — they're in `.gitignore`
- All API keys are read from environment variables — no hardcoded secrets
- Supabase service role key should only be used server-side (backend, not frontend)
- Frontend uses the anon key only (safe for client-side)

## License

MIT
