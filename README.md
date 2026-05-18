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
- Tavily API key (free tier)
- Firecrawl API key (free tier)
- Ollama running locally (`ollama pull mistral`)

### 1. Clone and configure
```bash
cd trestle
cp backend/.env.example backend/.env
# Fill in your keys
```

### 2. Start services
```bash
docker-compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000

### 3. Set up Supabase tables

Run the SQL in `scripts/supabase_schema.sql` in your Supabase SQL Editor.

## Key Features

1. **Freshness-first search** — live scraping + diff detection
2. **Local LLM** — Ollama for intent parsing + explanation generation
3. **Per-user memory** — agent remembers your profile and past queries
4. **Change detection** — periodic re-scrape alerts you when things change
5. **No seed data** — resources are discovered on-demand per user query

## API Endpoints

- `POST /api/search` — Search resources (scrapes fresh if local data is thin)
- `POST /api/scout/run` — Run scout agent (verify → discover → match → summarize)
- `GET /api/scout/status` — Scout agent status
- `POST /api/auth/signup` — Sign up
- `POST /api/auth/login` — Log in
- `GET /api/profiles/me` — Get current profile
- `PATCH /api/profiles/me` — Update profile
- `GET /api/profiles/onboarding-steps` — Onboarding questionnaire

## Project Structure

```
trestle/
  backend/
    app/
      main.py           # FastAPI app factory
      config.py         # Pydantic settings
      database.py       # Supabase client
      middleware/
        auth.py         # JWT verification
      models/
        schemas.py      # Pydantic models
      routers/
        auth.py         # Auth routes
        profile.py      # Profile CRUD + onboarding
        search.py       # Main search endpoint
        scout.py        # Scout agent run
      services/
        llm_client.py       # Ollama client
        intent_parser.py    # Query → structured intent
        source_router.py    # Intent → scrapable sources
        scraper_service.py  # Firecrawl + Tavily + diff
        resource_service.py # Supabase CRUD + search
        memory_service.py   # Per-user memory
        tavily_search.py    # Tavily client
        firecrawl_scraper.py # Firecrawl client
    Dockerfile
    requirements.txt
  frontend/
    app/
      page.tsx          # Landing page
      login/page.tsx    # Login
      signup/page.tsx   # Signup
      onboarding/page.tsx # Conversational onboarding
      dashboard/page.tsx  # Chat dashboard
      search/page.tsx     # Search results
      _components/
        SearchInput.tsx
    lib/
      supabase.ts       # Supabase client
    Dockerfile
    package.json
  docker-compose.yml
  scripts/
    supabase_schema.sql  # DB setup
```

## Environment Variables

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
SUPABASE_ANON_KEY=your-anon-key
TAVILY_API_KEY=your-tavily-key
FIRECRAWL_API_KEY=your-firecrawl-key
FRONTEND_URL=http://localhost:3000
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

## License

MIT
