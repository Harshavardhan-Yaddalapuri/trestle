# Trestle v0.2

AI-powered founder resource discovery engine. Freshness-first.  

## Architecture

- **Backend:** FastAPI + Supabase (PostgreSQL + Auth) + Ollama (local LLM)
- **Frontend:** Next.js 15 + Tailwind CSS v4
- **Scraping:** Firecrawl + Tavily (free tiers)
- **Packaging:** Docker + docker-compose

## Quick Start

### Prerequisites

- Docker + docker-compose
- Supabase project (free tier)
- [Ollama](https://ollama.com) running locally with a model pulled
- Tavily API key (free tier, optional)
- Firecrawl API key (free tier, optional)

### 1. Setup

```bash
make setup          # creates .env from template
#        OR manually:
cp .env.example .env
```

Edit `.env` with your keys:
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_ANON_KEY` — from your Supabase project settings
- `TAVILY_API_KEY`, `FIRECRAWL_API_KEY` — optional, for live scraping
- `OLLAMA_MODEL` — defaults to `mistral`; pull it first with `ollama pull mistral`

### 2. Start

```bash
make dev            # docker compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- Health check: http://localhost:8000/health

### 3. Set up Supabase

Run `scripts/supabase_schema.sql` in your Supabase SQL Editor to create tables and policies.

## Key Features

1. **Freshness-first search** — live scraping + diff detection
2. **Local LLM** — Ollama for intent parsing + explanation generation
3. **Per-user memory** — agent remembers your profile and past queries
4. **Change detection** — periodic re-scrape alerts when things change
5. **No seed data** — resources are discovered on-demand per user query

## Make Targets

| Command | Does |
|---------|------|
| `make setup` | Create `.env` from template |
| `make dev` | Build and start all services |
| `make down` | Stop services |
| `make clean` | Tear down and remove local images |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/search` | Search resources (fresh scraping) |
| `POST` | `/api/scout/run` | Run scout agent pipeline |
| `GET` | `/api/scout/status` | Scout agent status |
| `POST` | `/api/auth/signup` | Create account |
| `POST` | `/api/auth/login` | Sign in |
| `GET` | `/api/profiles/me` | Get profile |
| `PATCH` | `/api/profiles/me` | Update profile |
| `GET` | `/api/profiles/onboarding-steps` | Onboarding questionnaire |

## Project Structure

```
trestle/
  backend/
    app/
      main.py              # FastAPI app factory
      config.py            # Pydantic settings
      database.py          # Supabase client
      middleware/auth.py   # JWT verification
      models/schemas.py    # Pydantic models
      routers/             # auth, profile, search, scout
      services/            # LLM, intent, scraping, memory
    Dockerfile
    requirements.txt
  frontend/
    app/                   # Next.js pages + components
    lib/supabase.ts        # Supabase client
    Dockerfile
    package.json
  scripts/
    supabase_schema.sql    # DB migration
  docker-compose.yml
  Makefile
  .env.example
```

## License

MIT
