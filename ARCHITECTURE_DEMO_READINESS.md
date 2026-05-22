# Trestle — Architecture Assessment & Demo Readiness Plan
**Version:** 0.2 → 0.3 (Demo Ready)  
**Date:** May 19, 2026  
**Author:** Aurthur (System Architect)  
**Status:** IN REVIEW — pending Floyd + Jason sign-off, then Arceus approval

---

## 1. What Trestle Is (Team Briefing)

Trestle is an **AI-powered founder resource discovery engine** with a freshness-first approach. It answers questions like:

> *"What grants are open for pre-revenue AI founders in Detroit?"*

**Core loop:**
1. Founder asks a natural-language question
2. AI parses intent (location, stage, need type, industry, demographics)
3. System searches local DB first → if thin, scrapes live sources (Tavily + Firecrawl)
4. AI explains WHY each result fits + gives a concrete next step
5. System remembers the founder's profile and improves future answers
6. Scout agent periodically re-checks resources and alerts on changes

**Key differentiator:** Every result shows a **freshness badge** — "Verified 3 days ago" vs "Never verified" — so founders don't waste time on dead links.

**Target user:** Michigan-based startup founders (expandable to other states).

---

## 2. Current Architecture (High Level)

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Next.js 15    │────▶│   FastAPI 0.115    │────▶│   Supabase      │
│   (Frontend)    │◄────│   (Backend)        │◄────│   (PG + Auth)   │
│   Port 3000     │     │   Port 8000        │     │   SaaS          │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │
         │                       │
         ▼                       ▼
    Supabase Auth           ┌──────────────┐
    (Client-side)           │   Ollama     │
                            │   (Local LLM)│
                            │   Port 11434  │
                            └──────────────┘
                                   │
                                   ▼
                            ┌──────────────┐
                            │  Tavily     │
                            │  Firecrawl  │
                            │  (Free tier)│
                            └──────────────┘
```

---

## 3. Existing Assets (What We Have)

### Backend (`~/trestle/backend/`)
- ✅ FastAPI app factory (`main.py`)
- ✅ Pydantic schemas (`models/schemas.py`) — 258 lines, well-structured
- ✅ Router stubs: auth, profile, search, scout
- ✅ Service layer: intent parser, scraper, resource CRUD, memory, LLM client, source router
- ✅ Firecrawl + Tavily clients
- ✅ Dockerfile
- ✅ `requirements.txt`
- ❌ **CRITICAL:** Supabase Python client is **synchronous**. Every route calls `await supabase.table(...)` — **this will crash at runtime.**
- ❌ **CRITICAL:** Auth middleware (`middleware/auth.py`) hits a non-existent endpoint (`/auth/v1/verify`). JWT verification is broken.
- ⚠️ No `.env` file — backend won't boot without it.
- ⚠️ No error handling for external API failures (Tavily down → 500).
- ⚠️ Scout uses global in-memory state (`_last_run`, `_runs_today`) — resets on every deploy.

### Frontend (`~/trestle/frontend/`)
- ✅ Next.js 15 + Tailwind v4 with Material Design 3 tokens
- ✅ Landing page (hero + search input + feature cards)
- ✅ Login / Signup pages (Supabase client-side auth)
- ✅ Onboarding flow (7-step conversational questionnaire)
- ✅ Dashboard (chat UI with result cards, citations, freshness badges)
- ✅ Search input component
- ❌ **Search page (`search/page.tsx`) is a placeholder** — no actual API call.
- ⚠️ No `package-lock.json` — `npm install` will be slow.
- ⚠️ Dashboard makes API call to `/api/search` but search page doesn't.

### Database (`scripts/supabase_schema.sql`)
- ✅ `resources` table — 12 types, with JSONB provenance, status, timestamps
- ✅ `profiles` table — linked to `auth.users`, with RLS
- ✅ `memories` table — per-user conversational memory
- ✅ `scout_runs` table — run logging
- ✅ Indexes on type, status, location (GIN), last_verified, user_id
- ✅ RLS policies for all tables
- ✅ `vector` extension enabled (future-proofing)

### DevOps
- ✅ `docker-compose.yml` — backend + frontend
- ✅ Dockerfiles for both services
- ❌ No CI/CD, no health checks beyond `/health`

---

## 4. Critical Blockers (Must Fix Before Demo)

| # | Blocker | Severity | Owner | Fix |
|---|---------|----------|-------|-----|
| 1 | **Async/sync mismatch** — `await` on sync Supabase calls | 🔴 P0 | Jason | Remove `await` from all `supabase.table()` calls, or wrap in `asyncio.to_thread()` |
| 2 | **Auth middleware broken** — `/auth/v1/verify` doesn't exist | 🔴 P0 | Jason | Use `supabase.auth.get_user(token)` or local JWT decode with Supabase JWT secret |
| 3 | **No `.env` configured** — backend won't start | 🔴 P0 | Jason / Harsha | Copy `.env.example` to `.env` and fill keys |
| 4 | **Search page is a placeholder** — no results display | 🔴 P0 | Floyd | Wire `/search?q=...` to call `/api/search` and render `FitResult` cards |
| 5 | **Ollama dependency for demo** — may not be running locally | 🟡 P1 | Jason | Add mock LLM fallback when `OLLAMA_BASE_URL` unreachable |
| 6 | **No API error handling** — Tavily/Firecrawl down = 500 | 🟡 P1 | Jason | Wrap all external calls in try/except with graceful degradation |
| 7 | **No seed data / no first-query experience** — empty DB = no results until scraping | 🟡 P1 | Jason | Add 10-20 Michigan-specific seed resources so first query isn't empty |

---

## 5. API Contract (Validated — Minor Fixes Needed)

The API contract is largely correct and exists in `schemas.py`. Here are the verified endpoints:

### Auth
- `POST /api/auth/signup` → `Token`
- `POST /api/auth/login` → `Token`

### Profiles
- `GET /api/profiles/me` → `ProfileResponse` (auto-creates if missing)
- `PATCH /api/profiles/me` → `ProfileResponse`
- `GET /api/profiles/onboarding-steps` → `OnboardingStep[]`

### Search
- `POST /api/search` → `SearchResponse`
  - Body: `SearchRequest` { query, profile_id?, session_id?, limit? }
  - Response: { query_parsed: IntentResult, results: FitResult[], total_found, sources_queried, fresh_sources_scraped }

### Scout
- `POST /api/scout/run` → `ScoutRunResponse`
- `GET /api/scout/status` → `ScoutStatus`

### Health
- `GET /health` → `{ status: "ok", version: "0.2.0" }`

**Changes needed:**
- Auth middleware must attach `user` dict to request state so routers can read `profile_id` from JWT, not just rely on `profile_id` in body.
- Search endpoint should default to anonymous search (no auth required) for landing page usage.

---

## 6. Database Schema (Validated — No Changes Needed)

The schema in `scripts/supabase_schema.sql` is solid for demo purposes:
- Soft deletes via `status` enum (`active`, `stale`, `dead`, `pending_review`)
- `vector` extension ready for future semantic search
- JSONB `provenance` for audit trail
- `source_hash` for change detection
- `last_scraped` / `last_verified` for freshness badges
- RLS policies correct

**No schema changes required for demo.**

---

## 7. Technology Decisions (ADR)

### ADR-1: Keep existing stack (FastAPI + Next.js + Supabase + Ollama)
- **Rationale:** Rewriting anything costs demo time. The scaffold is 80% there. Fix the 20%.
- **Risk:** Ollama requires local runtime. Mitigate with mock fallback.

### ADR-2: Use Supabase Auth (don't build custom)
- **Rationale:** Auth is already wired client-side. Fix the server-side JWT verification.
- **Risk:** Supabase free tier limits. For demo, acceptable.

### ADR-3: Tavily + Firecrawl free tiers for scraping
- **Rationale:** No build time. Free tier covers demo usage. Tavily = search discovery, Firecrawl = deep page scrape.
- **Risk:** Rate limits. Mitigate with local caching and graceful fallback.

### ADR-4: No seed data → seed data for demo
- **Rationale:** Empty DB = dead first query. Add 15 Michigan resources so the demo flows.
- **Risk:** Stale data. Mark them as `pending_review` with clear provenance.

### ADR-5: Single Docker Compose for local demo
- **Rationale:** One command to boot. No infra complexity.
- **Risk:** Ollama not in Docker. Document `ollama pull mistral` prerequisite.

---

## 8. Failure Mode Design

| External Service | Failure Mode | Fallback |
|-----------------|---------------|----------|
| Tavily API | Rate limit / timeout | Return empty `discovered` list; rely on local DB |
| Firecrawl API | Rate limit / timeout | Return error; skip fresh scrape; use Tavily snippet only |
| Ollama (local LLM) | Not running / timeout | Use mock LLM ( deterministic intent parse + canned explanations) |
| Supabase Auth | JWT expiry | Return 401; frontend redirects to login |
| Supabase DB | Connection failure | Return 503 with retry-after header |

---

## 9. Demo-Ready Checklist

- [ ] Fix async/sync mismatch in all backend services
- [ ] Fix auth middleware JWT verification
- [ ] Add `.env` with real keys
- [ ] Add mock LLM fallback for Ollama
- [ ] Add 15 Michigan seed resources to Supabase
- [ ] Wire search page to `/api/search`
- [ ] Add error handling to all external API calls
- [ ] Test full flow: landing → search (anon) → signup → onboarding → dashboard → query → results
- [ ] Docker compose up works end-to-end
- [ ] 3-minute demo script practiced

---

## 10. Next Steps

1. **Jason** — Fix backend blockers (async/sync, auth, error handling, mock LLM, seed data)
2. **Floyd** — Wire search page, polish dashboard UI, ensure mobile responsiveness
3. **Jim** — Verify Docker compose works, ensure env vars are correct
4. **Aurthur** — This doc is ready for Arceus approval once Jason and Floyd confirm API contract is implementable.

**No code until this architecture is approved by Arceus.**
