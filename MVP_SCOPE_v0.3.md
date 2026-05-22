# Trestle v0.3 — MVP Scope & Investor Demo Plan
**"OpenClaw for Michigan Startup Founders"**

**Version:** 0.3 (Demo Ready)  
**Date:** May 21, 2026  
**Demo:** Friday, May 23, 2026 at 10:30 AM EST  
**Team:** 3 developers (Harsha: systems/infra, Dev 2: backend, Dev 3: frontend)  
**Constraint:** 3 working days. No new features — only fixes and polish.

---

## 1. Product Requirements Doc (One Page)

### What Trestle Is
Trestle is an AI-powered resource discovery engine with a **freshness-first** approach. Startup founders ask natural-language questions like *"What grants are open for pre-revenue AI founders in Detroit?"* and Trestle scrapes live sources, verifies freshness, and returns ranked results with explanations, citations, and concrete next steps.

### Target User
Michigan-based startup founders (Detroit, Ann Arbor, Grand Rapids). Expandable post-MVP.

### Core Value Prop
**"Find resources that are still true."** Every result shows a freshness badge ("Verified 3 days ago" vs "Never verified") so founders don't waste time on dead links.

### Core Loop (What The Investor Sees)
1. Founder lands on Trestle → sees value prop
2. Types a natural-language query (can be anonymous)
3. System parses intent (location, stage, need type, industry)
4. Searches local DB first → if thin, scrapes live via Tavily + Firecrawl
5. Returns ranked results with:
   - Fit explanation (WHY this resource matches)
   - Concrete next step (WHAT to do next)
   - Freshness badge (WHEN it was last verified)
   - Source citations
6. Founder signs up, completes a brief onboarding profile
7. Future queries are personalized using their profile
8. (Optional) Scout agent shows change detection on saved resources

### Success Criteria for Demo
- [ ] Full anonymous flow: landing → search → results with freshness badges
- [ ] Full authenticated flow: signup → onboarding → dashboard chat → personalized results
- [ ] At least 3 queries return results with citations in under 10 seconds each
- [ ] Zero 500 errors or blank screens during demo
- [ ] Works on laptop (localhost) — no cloud dependency beyond Supabase

---

## 2. Prioritized Feature List

### P0 — Must Demo (These Block The Pitch)

| ID | Feature | Owner | Est. Hours | AC |
|----|---------|-------|------------|-----|
| P0-1 | Fix async/sync Supabase mismatch | Dev 2 | 2h | All `supabase.table()` calls work at runtime. `docker compose up backend` succeeds. Health endpoint returns 200. |
| P0-2 | Fix auth JWT verification | Dev 2 | 2h | `POST /api/auth/signup` returns valid JWT. `GET /api/profiles/me` with that token returns profile. Frontend dashboard page loads without redirecting to login. |
| P0-3 | Configure .env with real keys | Harsha | 1h | `.env` exists at `backend/.env` with valid Supabase URL, service key, anon key, Tavily key, Firecrawl key. Backend boots without errors. |
| P0-4 | Wire search page to real API | Dev 3 | 3h | Visit `/search?q=grants+for+AI+founders+in+Detroit`. Page calls `POST /api/search` and renders FitResult cards matching the dashboard component styling (freshness badge, fit explanation, next step, citation, match %). |
| P0-5 | Add mock LLM fallback | Dev 2 | 2h | When Ollama is unreachable (set `OLLAMA_BASE_URL=http://localhost:1`), intent parser returns keyword-based results (existing fallback in `parse_intent` already partially handles this — extend to explanations). Search still returns results with deterministic fit explanations. |
| P0-6 | API error handling for external calls | Dev 2 | 2h | Tavily rate-limited → returns empty `discovered` list, local DB results still shown. Firecrawl timeout → skip scrape, show Tavily snippet only. No 500 errors reach the frontend. Every external call wrapped in try/except. |
| P0-7 | Seed 15 Michigan resources | Dev 2 | 2h | Run seed script. `SELECT count(*) FROM resources WHERE status = 'active'` returns ≥ 15. Resources cover: Detroit grants, Ann Arbor accelerators, Michigan pitch competitions, statewide tax credits, coworking spaces. Each has: name, type, description, URL, location, eligibility. |
| P0-8 | Polish landing page search → results flow | Dev 3 | 2h | Entering a query on the landing page and pressing Enter navigates to `/search?q=...` and displays results. Loading state shows "Searching live sources…" spinner. Empty state shows "No results found. Try a broader query." |
| P0-9 | Onboarding streamline (reduce to 3 steps) | Dev 3 | 2h | Onboarding flow asks max 3 questions: location/state, startup stage, what they're looking for. Skip button available. Completing onboarding creates profile and redirects to dashboard. |
| P0-10 | End-to-end demo script validated | Harsha | 1h | Run the demo script (Section 5 below) end-to-end. Every step completes without errors. Total time ≤ 5 minutes. |

**Total P0: ~19 hours** (~6.3 hours/person over 3 days — feasible with buffer)

### P1 — Impressive If Time (Adds Polish But Not Blocking)

| ID | Feature | Owner | Est. Hours | AC |
|----|---------|-------|------------|-----|
| P1-1 | Scout run endpoint works end-to-end | Dev 2 | 3h | `POST /api/scout/run` with a profile returns new/changed resources. Dashboard shows a "Scout" tab or button that triggers a run and displays results. |
| P1-2 | Mobile-responsive polish | Dev 3 | 2h | Landing page, search results, and dashboard are usable on iPhone SE viewport (375px). No horizontal scroll. Chat input accessible. Result cards readable. |
| P1-3 | Cached search results (avoid re-scraping) | Dev 2 | 2h | Same query within 5 minutes returns cached results from DB without calling Tavily/Firecrawl again. Response time < 2 seconds for cached queries. |
| P1-4 | Dashboard "suggested queries" personalized | Dev 3 | 1h | After onboarding, dashboard empty state shows suggested queries based on profile (e.g., if stage="idea" show "Grants for idea-stage founders"). |
| P1-5 | Loading skeleton UI | Dev 3 | 1h | While search results load, result cards show animated skeleton placeholders instead of just a spinner. |
| P1-6 | Freshness badge colors/logic polish | Dev 3 | 1h | "Verified X days ago" shows green (≤7 days), yellow (8-30 days), red (>30 days). "Never verified" shows gray. Consistent across search page and dashboard. |
| P1-7 | Error toast notifications | Dev 3 | 1h | API errors show a toast notification with a retry button instead of raw error text in the chat. |

**Total P1: ~11 hours** (only if P0 is done early)

### P2 — Don't Touch (Would Derail The Demo)

| Feature | Reason |
|---------|--------|
| Vector/semantic search | Requires pgvector + embeddings. 2+ days of work, no demo impact. |
| Multi-state expansion | Michigan-only is fine for demo. Adding Ohio/Illinois = 1 day of seed data + testing. |
| Email notifications / Scout scheduled runs | Requires email infra, cron jobs, async workers. 2+ days. |
| Payment/Stripe integration | Not needed for demo. Distracts from core value prop. |
| CI/CD pipeline | Deploying to cloud adds risk. Demo runs on localhost. |
| Unit tests / integration tests | Existing code has no test suite. Adding tests takes time from fixing bugs. |
| Admin dashboard | No investor cares about admin features. |
| Any UI framework migration | Tailwind v4 + Material Design 3 tokens are working. Don't touch. |
| Supabase client library swap (sync → async) | Audit says fix the `await` calls, not swap libraries. Wrapping in `asyncio.to_thread()` is the safe, fast fix. |
| Docker Compose production hardening | Local dev compose is sufficient for demo. |

---

## 3. Acceptance Criteria Per Feature (Detailed)

### P0-1: Fix async/sync Supabase mismatch
- [ ] Run `docker compose up backend` — no `RuntimeWarning: coroutine was never awaited`
- [ ] All `supabase.table()` calls in `resource_service.py`, `scraper_service.py`, `memory_service.py` use `asyncio.to_thread()` wrapper
- [ ] `GET /health` returns `{"status": "ok", "version": "0.3.0"}`

### P0-2: Fix auth JWT verification
- [ ] `POST /api/auth/signup` with `{"email": "test@demo.com", "password": "demo123456"}` returns `{"access_token": "...", "token_type": "bearer"}`
- [ ] Using that token: `GET /api/profiles/me` returns a profile object (auto-created on first access)
- [ ] Using an invalid token: returns 401
- [ ] Dashboard page loads with `supabase.auth.getSession()` and does not redirect unauthenticated users during normal flow

### P0-3: Configure .env
- [ ] `backend/.env` file exists
- [ ] Contains: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_ANON_KEY`, `TAVILY_API_KEY`, `FIRECRAWL_API_KEY`
- [ ] `OLLAMA_BASE_URL` and `OLLAMA_MODEL` set (even if mock fallback active)
- [ ] Backend starts with `uvicorn app.main:app` without config errors

### P0-4: Wire search page
- [ ] Navigate to `http://localhost:3000/search?q=grants+for+AI+founders+in+Detroit`
- [ ] Page shows loading state for < 3 seconds
- [ ] Results render as cards with: resource name, type badge, description, location tags, deadline (if any), funding range, fit explanation, next step, freshness badge, source citation link
- [ ] Cards match the dashboard component styling (same `FitResult` rendering)
- [ ] If no results: shows "No results found. Try broadening your search." with suggested queries

### P0-5: Mock LLM fallback
- [ ] Set `OLLAMA_BASE_URL=http://localhost:19999` (unreachable)
- [ ] Search for "grants Detroit" — returns results (uses keyword-based intent parse)
- [ ] Fit explanations read: "[Resource name] is a [type] resource for founders in your area."
- [ ] Next steps read: "Check the details at their website."
- [ ] No 500 errors; no "Connection refused" errors visible to user

### P0-6: API error handling
- [ ] Unset `TAVILY_API_KEY` — search still returns local DB results
- [ ] Unset `FIRECRAWL_API_KEY` — search still returns results (no fresh scrape, local DB only)
- [ ] Set `TAVILY_API_KEY=invalid` — search returns local DB results, logs warning
- [ ] No 500 status codes in any scenario — every error path returns a valid `SearchResponse`

### P0-7: Seed data
- [ ] Run seed script (SQL file or Python script)
- [ ] `SELECT count(*) FROM resources WHERE status = 'active'` ≥ 15
- [ ] Resources include at minimum:
  - 3 Michigan grants (e.g., Michigan Business Development Program, Detroit small biz grants, MEDC grants)
  - 2 accelerators (e.g., Techstars Detroit, Ann Arbor SPARK)
  - 2 pitch competitions (e.g., Accelerate Michigan, Detroit Demo Day)
  - 1 tax credit program (e.g., Michigan MEGA tax credits)
  - 3 coworking spaces (e.g., Bamboo Detroit, Cahoots, TechTown)
  - 2 events/workshops
  - 2 mentorship programs
- [ ] Each resource has: name, type, description, url, location (array with Michigan city), eligibility (JSONB), status="active", last_verified=today

### P0-8: Landing page search → results
- [ ] On landing page, type "grants for AI founders Detroit" and press Enter
- [ ] Browser navigates to `/search?q=grants%20for%20AI%20founders%20Detroit`
- [ ] Loading indicator appears while API call is in flight
- [ ] Results render within viewport
- [ ] "No results" state shows with helpful message and suggested queries

### P0-9: Streamlined onboarding
- [ ] Sign up creates account, redirects to onboarding
- [ ] Onboarding shows 3 steps (not 7):
  1. "Where are you based?" (text input with Michigan cities autocomplete or select)
  2. "What stage is your startup?" (select: Idea, Pre-revenue, Seed, Series A, Growth)
  3. "What are you looking for?" (multiselect: Grants, Accelerators, Pitch Competitions, Coworking, Mentorship, Events)
- [ ] "Skip" button on each step
- [ ] "Finish" creates profile, redirects to dashboard
- [ ] Dashboard empty state reflects profile (shows personalized suggestions)

### P0-10: Demo script validated
- [ ] Run the full script in Section 5 below
- [ ] Every step completes without manual intervention
- [ ] Total time ≤ 5 minutes (target: 3-4 minutes to leave buffer)
- [ ] No browser console errors during demo
- [ ] Supabase dashboard shows new user, profile, and search memories created

---

## 4. Risk Register — What Could Fail During Demo

| # | Risk | Probability | Impact | Mitigation | Owner |
|---|------|------------|--------|------------|-------|
| R1 | **Ollama not running / model not pulled** on demo laptop | Medium | High — no LLM = broken intent parse + explanations | P0-5 mock LLM fallback. Pre-pull `mistral` with `ollama pull mistral`. Have `ollama serve` running before demo. | Harsha |
| R2 | **Tavily API rate limit hit** (free tier: 1000 searches/month) | Low | Medium — no fresh discovery | P0-6 graceful degradation. Seed data (P0-7) ensures local DB has results even if Tavily is down. Pre-warm with 5 queries before demo to check limits. | Dev 2 |
| R3 | **Firecrawl API rate limit** (free tier: 500 credits/month) | Low | Low — scraping is bonus | P0-6 fallback. Seed data ensures results. Demo queries don't depend on fresh scrapes. | Dev 2 |
| R4 | **Supabase free tier paused** (inactivity or limit) | Low | Critical — NO app works without DB | Log into Supabase dashboard 24h before demo. Verify project is active. Have a backup Postgres dump ready. | Harsha |
| R5 | **WiFi failure at demo venue** | Medium | Critical — no API calls work | Have a fully offline fallback: seed data in DB, mock LLM active, no Tavily/Firecrawl calls needed. Test offline mode Thursday night. | Harsha |
| R6 | **Browser caching issue** — old JS bundle serves broken code | Medium | Medium — confusing to investor | Hard-refresh before demo. Clear `node_modules/.cache` and rebuild frontend Thursday evening. | Dev 3 |
| R7 | **Docker not running / port conflicts** | Low | High — app won't start | `docker compose up` health check 30 min before demo. Kill any process on ports 3000/8000. | Harsha |
| R8 | **Seed data looks stale** — resources from 2023 show as "active" | Medium | High — undermines "freshness-first" value prop | Set `last_verified` to demo day. Use real, verifiable programs that are known to be active in May 2026. | Dev 2 |
| R9 | **Signup fails** — Supabase auth project misconfigured | Low | Critical — no auth flow | Test signup flow Thursday evening. Verify email confirmations are disabled (or auto-confirm) for demo. | Dev 2 |
| R10 | **Typo in demo query causes zero results** | Medium | Medium — awkward silence | Pre-test demo queries. Have 3 backup queries that are guaranteed to return results from seed data. | All |

### Pre-Demo Checklist (Thursday Night)
- [ ] `docker compose up` from clean state — both services healthy
- [ ] `ollama serve` running, `ollama pull mistral` confirmed
- [ ] `.env` verified — all keys present and valid
- [ ] `SELECT count(*) FROM resources` ≥ 15
- [ ] Run demo script end-to-end twice (once with LLM, once with mock fallback)
- [ ] Test offline mode: Ollama unreachable + Tavily/Firecrawl unreachable → still returns seed data
- [ ] Laptop charged, charger packed, external monitor adapter ready
- [ ] Browser: incognito window ready, no extensions, hard refresh
- [ ] Backup: have a 60-second video recording of the flow as fallback

---

## 5. User Flow — Investor Demo (5 Minutes)

### Minute 0-1: The Hook (Landing Page)
> **Investor sees:** Trestle landing page. Clean hero: *"Find resources that are still true."*

**Demo script:**
1. "This is Trestle. Startup founders waste hours Googling grants and programs — half the links are dead. Trestle scrapes live and tells you what's actually still open."
2. Show landing page with 3 feature cards: Live Verification, AI Explanations, Freshness Badges
3. Type into the hero search: **"grants for pre-revenue AI founders in Detroit"**
4. Hit Enter → navigates to search results page

### Minute 1-2: The Magic (Search Results)
> **Investor sees:** Search results page with 5-8 result cards, each with freshness badge.

**Demo script:**
1. "Watch — it searched our database and scraped live sources."
2. Point at result cards:
   - **Freshness badge:** "Verified today" (green) vs "Never verified" (gray)
   - **Fit explanation:** "This grant matches because you're pre-revenue and in Michigan."
   - **Next step:** "Apply by June 15 — deadline is in the eligibility section."
   - **Citation:** Clickable source link
3. "Every result tells you WHY it fits and WHAT to do next. No more dead ends."

### Minute 2-3: Sign Up & Onboarding
> **Investor sees:** Signup → streamlined onboarding → personalized dashboard.

**Demo script:**
1. Click "Get Started" → sign up with demo email
2. Onboarding (3 quick steps):
   - "Detroit, MI" (location)
   - "Pre-revenue" (stage)
   - Select "Grants" + "Accelerators" (what they want)
3. "That's it. Three questions. Now Trestle knows who you are."

### Minute 3-4: Personalized Dashboard
> **Investor sees:** Dashboard with chat interface and personalized suggestions.

**Demo script:**
1. Dashboard loads. Empty state shows personalized suggestions based on profile
2. Type: **"pitch competitions closing soon in Michigan"**
3. Results return — this time filtered by their profile preferences
4. Point out: "See how the results are now tailored — it knows you're in Detroit at pre-revenue stage."

### Minute 4-5: Scout (Optional, Time Permitting)
> **Investor sees:** Scout tab or button that checks for changes.

**Demo script (only if P1-1 is done):**
1. "And here's the really clever part — Trestle has a Scout agent. It periodically re-checks resources and alerts you on changes."
2. Click Scout → trigger a run on Detroit grants
3. Show: "3 resources unchanged, 1 new grant found, 1 deadline updated"
4. "If a grant closes or a deadline changes, you know immediately. You don't have to keep checking."

**If Scout not ready (P1-1 skipped):**
1. Wrap up: "Post-MVP, we add Scout — an agent that periodically re-checks saved resources and alerts founders on changes. Deadlines, eligibility shifts, new programs."
2. "We're building the operating system for founder resource discovery."

### Minute 5: Wrap
> **Investor sees:** Summary of what they just experienced.

**Demo script:**
1. "In 5 minutes, you saw: anonymous search with live scraping, signup with personalized onboarding, and AI-explained results with freshness verification."
2. "We've been building this for [X weeks/months] with a team of 3. We're targeting Michigan founders first — 50,000+ new business applications filed in Michigan annually."
3. Open for questions.

---

## 6. Developer Work Assignments (72 Hours)

### Harsha — Systems & Infra (Day 1-3)
- **Day 1:** Set up `.env`, verify Supabase project, pull Ollama model, ensure Docker Compose works
- **Day 2:** Write seed data script, validate all 15 resources, test offline mode, create demo script checklist
- **Day 3:** Full end-to-end testing, risk mitigation (pre-pull everything, test offline), dry run demo

### Dev 2 — Backend (Day 1-3)
- **Day 1:** Fix async/sync mismatch (P0-1) + auth JWT (P0-2) — these must ship first
- **Day 2:** Mock LLM fallback (P0-5) + API error handling (P0-6) + seed data insertion (P0-7)
- **Day 3:** Scout endpoint (P1-1 if time) + cache search results (P1-3 if time) + bug fixes from integration testing

### Dev 3 — Frontend (Day 1-3)
- **Day 1:** Wire search page (P0-4) + polish landing page flow (P0-8)
- **Day 2:** Streamline onboarding (P0-9) + loading skeletons (P1-5) + error toast (P1-7)
- **Day 3:** Mobile polish (P1-2) + freshness badge colors (P1-6) + final UI QA + demo dry run

### Daily Sync Schedule
- **Morning standup (9 AM):** 10 min — blockers, progress, priorities
- **Evening check (5 PM):** 5 min — what shipped, what didn't, adjusted plan for tomorrow
- **Thursday night (8 PM):** Full dry run of demo script
- **Friday morning (8-9 AM):** Final checks, laptop prep, 9:30 AM leave for demo

---

## 7. Definition of Done (v0.3)

- [ ] All P0 features (10 items) pass their acceptance criteria
- [ ] `docker compose up` starts backend + frontend cleanly
- [ ] Full demo script runs end-to-end in ≤ 5 minutes
- [ ] Seed data returns results for all 3 demo queries
- [ ] Zero 500 errors during demo script execution
- [ ] Offline mode works (mock LLM + seed data, no Tavily/Firecrawl)
- [ ] Browser console shows no errors during demo
- [ ] ARCHITECTURE_DEMO_READINESS.md updated with v0.3 status

---

*This document supersedes the P0/P1 blockers from ARCHITECTURE_DEMO_READINESS.md. All P0 items from that audit are incorporated here. No new features beyond what is listed. Ship the demo.*
