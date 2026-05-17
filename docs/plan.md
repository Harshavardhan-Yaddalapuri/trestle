# Trestle — Founder Resource Discovery Engine
## Implementation Plan (Hackathon Build)

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a founder-facing AI discovery engine + operator dashboard that helps Michigan (and beyond) founders discover resources they'd never find on Google, with freshness/verification as first-class features.

**Architecture:** FastAPI backend with Supabase (auth + PostgreSQL + pgvector) for data layer. IBM Granite 3.3 via watsonx.ai API for all LLM work (intent parsing, explanation generation, change summarization). Next.js frontend. The "scout agent" runs daily but is simulated on-demand for demo.

**Tech Stack:** Python 3.11, FastAPI, Supabase, IBM watsonx.ai (Granite), Next.js + Tailwind, PostgreSQL + pgvector

**Time Budget:** ~8 hours of build time. Demo video + writeup in final hours.

---

## Phase 0: Project Scaffold & Infrastructure (Hour 0)

### Task 0.1: Initialize monorepo structure

**Objective:** Create folder structure for backend + frontend + shared config.

**Create:**
```
trestle/
  backend/
    app/
      __init__.py
      main.py
      config.py
      database.py
      models/
      routers/
      services/
      agents/
    tests/
    requirements.txt
    Dockerfile
  frontend/
    app/
    components/
    lib/
    public/
    package.json
    tsconfig.json
    tailwind.config.ts
  docs/
    plan.md
    data/
  scripts/
```

**Commands:**
```bash
cd ~/trestle
mkdir -p backend/app/{models,routers,services,agents} backend/tests frontend/{app,components,lib,public} scripts docs/data
```

**Verify:** `tree -L 3` or `find . -type d | sort` shows structure.

**Commit:** `git add -A && git commit -m "chore: scaffold project structure"`

---

### Task 0.2: Set up Supabase project and schema

**Objective:** Create Supabase project, define tables for resources, profiles, scout runs.

**Prerequisite:** Supabase account. Create new project.

**SQL to run in Supabase SQL Editor:**

```sql
-- Extension for vector search
CREATE EXTENSION IF NOT EXISTS vector;

-- Resources table with provenance
CREATE TABLE resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('grant','accelerator','pitch_competition','coworking','event','mentorship','tax_credit','hiring_program','filing')),
    description TEXT,
    url TEXT,
    application_url TEXT,
    location TEXT[],
    industry TEXT[],
    stage TEXT[],
    demographics TEXT[],
    funding_range TEXT,
    deadline DATE,
    prize_amount TEXT,
    eligibility JSONB,
    data JSONB,
    embedding VECTOR(768),
    provenance JSONB DEFAULT '{}',
    status TEXT DEFAULT 'active' CHECK (status IN ('active','stale','dead','pending_review')),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Founder profiles
CREATE TABLE profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT,
    location TEXT,
    stage TEXT,
    industry TEXT[],
    demographics TEXT[],
    funding_need TEXT,
    goals TEXT,
    notification_freq TEXT DEFAULT 'daily',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Scout runs (agent execution log)
CREATE TABLE scout_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID REFERENCES profiles(id),
    run_type TEXT DEFAULT 'daily',
    run_at TIMESTAMPTZ DEFAULT now(),
    found_resources UUID[],
    removed_resources UUID[],
    changes_detected JSONB,
    digest TEXT,
    status TEXT DEFAULT 'completed'
);

-- Enable RLS
ALTER TABLE resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE scout_runs ENABLE ROW LEVEL SECURITY;

-- Resources: anyone can read
CREATE POLICY "resources_public_read" ON resources
    FOR SELECT TO anon, authenticated USING (true);

-- Profiles: users can only CRUD their own
CREATE POLICY "profiles_own" ON profiles
    FOR ALL TO authenticated USING (auth.uid() = user_id);

-- Create indexes
CREATE INDEX idx_resources_type ON resources(type);
CREATE INDEX idx_resources_status ON resources(status);
CREATE INDEX idx_resources_location ON resources USING gin(location);
CREATE INDEX idx_resources_embedding ON resources USING ivfflat (embedding vector_cosine_ops);
```

**Also set up:**
- Supabase Auth (Email + OAuth)
- Get `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` for backend
- Get `SUPABASE_ANON_KEY` for frontend

**Verify:** Tables exist in Supabase Table Editor. Insert test row: `INSERT INTO resources (name, type, description) VALUES ('Test Grant', 'grant', 'A test');` and select it back.

---

### Task 0.3: Backend config and Supabase connection

**Objective:** Connect FastAPI backend to Supabase with environment config.

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`

**Backend `requirements.txt`:**
```
fastapi==0.115.0
uvicorn[standard]==0.34.0
python-dotenv==1.0.1
httpx==0.28.1
supabase==2.15.0
pydantic==2.11.0
pydantic-settings==2.9.0
numpy==2.2.0
sentence-transformers==4.1.0
```

**`.env.example`:**
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
WATSONX_API_KEY=your-ibm-api-key
WATSONX_PROJECT_ID=your-project-id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

**`backend/app/config.py`:**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str
    watsonx_api_key: str
    watsonx_project_id: str
    watsonx_url: str = "https://us-south.ml.cloud.ibm.com"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**`backend/app/database.py`:**
```python
from supabase import create_client, Client
from app.config import settings

supabase: Client = create_client(settings.supabase_url, settings.supabase_service_key)
```

**Verify:** `cd backend && python -c "from app.database import supabase; print(supabase)"` connects without error.

**Commit:** Backend config committed.

---

## Phase 1: Data Ingestion & Seeding (Hour 1)

### Task 1.1: Ingest StartMidwest baseline data

**Objective:** Transform provided Google Sheet into structured JSON and load into Supabase.

**Files:**
- Create: `scripts/ingest_startmidwest.py`
- Create: `docs/data/michigan_baseline.json` (output)

**Process:**
1. Download/copy the StartMidwest Google Sheet to CSV/JSON.
2. Transform each row to match resource schema:
   - Map columns: name, type, city, url, description, deadline, prize, etc.
   - Normalize `type` to enum values.
   - Build `location` array from city + state.
   - Build `eligibility` JSONB from any criteria columns.
   - Set `provenance` with `source_url`, `first_added`, `last_verified`.

**Sample row:**
```json
{
  "name": "MEDC Mobility Grant",
  "type": "grant",
  "description": "Non-dilutive funding for mobility startups...",
  "url": "https://medc.org/grants/mobility",
  "location": ["Detroit", "Michigan"],
  "industry": ["mobility", "transportation"],
  "stage": ["pre-revenue", "early-revenue"],
  "eligibility": {"geography": "Michigan-based", "stage": "pre-revenue"},
  "provenance": {
    "source_url": "https://medc.org/grants",
    "first_added": "2025-03-10",
    "last_verified": "2026-05-16",
    "verified_by": "manual_ingest"
  }
}
```

**Load:** Run script to batch-insert into Supabase `resources` table.

**Target:** At least 50 Michigan resources loaded with full provenance.

**Verify:** `SELECT COUNT(*) FROM resources WHERE location @> ARRAY['Michigan']::text[];` returns > 40.

---

### Task 1.2: Add sample Illinois data (multi-state proof)

**Objective:** Hand-curate 10-15 Illinois resources to prove architecture is config-driven.

**Files:**
- Create: `docs/data/illinois_baseline.json`

**Process:**
1. Manually research 10 Illinois resources (grants, accelerators, events).
2. Use same schema as Michigan.
3. Tag with `location: ["Chicago", "Illinois"]`.

**Verify:** `SELECT COUNT(*) FROM resources WHERE location @> ARRAY['Illinois']::text[];` returns >= 10.

---

### Task 1.3: Generate resource embeddings

**Objective:** Create vector embeddings for semantic search.

**Files:**
- Create: `scripts/generate_embeddings.py`

**Process:**
1. Fetch all resources from Supabase.
2. For each resource, build text: `"{name}. {description}. Type: {type}. Location: {location}. Stage: {stage}. Industry: {industry}."`
3. Use lightweight model (e.g., `sentence-transformers/all-MiniLM-L6-v2`) to generate 384-dim embedding.
4. Upsert into Supabase `resources.embedding` column.

**NOTE:** On hackathon free tier, embedding generation is heavy. Alternative: generate locally and upload.

**Verify:** Run a vector query: `SELECT name FROM resources ORDER BY embedding <-> (SELECT embedding FROM resources LIMIT 1) LIMIT 5;` returns semantically similar results.

---

## Phase 2: IBM Granite Integration (Hour 2-3)

### Task 2.1: IBM watsonx.ai API client

**Objective:** Build reusable client for Granite 3.3 8B Instruct.

**Files:**
- Create: `backend/app/services/watsonx.py`

**Requirements:**
- Authenticate with IBM Cloud IAM (apikey → access token)
- Generate completions via `POST /ml/v1/text/generation`
- Support: `model_id=ibm/granite-3-3-8b-instruct`, `project_id`, `parameters` (max_tokens, temperature)
- Support tool-calling format for agent tools

**Code skeleton:**
```python
import httpx
from app.config import settings

class WatsonXClient:
    def __init__(self):
        self.api_key = settings.watsonx_api_key
        self.project_id = settings.watsonx_project_id
        self.base_url = settings.watsonx_url
        self.access_token = None
    
    async def _get_token(self):
        # IAM token exchange
        pass
    
    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        # POST to text/generation
        pass
    
    async def chat(self, messages: list, tools: list = None) -> dict:
        # Tool-calling format for agent
        pass
```

**Test:** `python -c "from app.services.watsonx import client; print(client.generate('Hello'))"` returns text.

**Commit:** WatsonX client committed.

---

### Task 2.2: Query intent parser

**Objective:** Use Granite to parse founder free-text queries into structured search criteria.

**Files:**
- Create: `backend/app/services/intent_parser.py`

**Input:** "I'm a solo Black woman founder in Detroit, pre-revenue, building AI for manufacturers. What grants in the next 90 days?"

**Prompt to Granite:**
```
Parse the founder's query into structured search criteria. Return ONLY valid JSON matching this schema:
{"location": "...", "stage": "...", "need_type": "grant|accelerator|event|coworking|mentorship", "timeline": "90_days|6_months|ongoing", "industry": [...], "demographics": [...], "funding_range": "..."}

Query: {user_query}
```

**Output validation:** Pydantic model, fallback to fuzzy matching if parse fails.

**Commit:** Intent parser committed.

---

### Task 2.3: Explanation generator

**Objective:** For each retrieved resource, Granite generates personalized "Why this fits you" and next step.

**Files:**
- Create: `backend/app/services/explanation.py`

**Prompt to Granite:**
```
Given this founder profile and resource, write a concise 2-sentence explanation in plain English:
- Why this resource fits this founder
- What the next step is

Keep it under 100 words. No marketing speak.

Founder: {profile_summary}
Resource: {resource_summary}
```

**Commit:** Explanation generator committed.

---

### Task 2.4: Change summarizer (freshness demo)

**Objective:** Simulate how Granite would summarize detected changes between old and new page versions.

**Files:**
- Create: `backend/app/services/change_summarizer.py`

**Input:** Diff of two text versions of a resource page.
**Output:** Human-readable summary: "Deadline changed from June 1 to August 15. Prize pool increased to $25K."

**For demo:** Use mock diffs. Show 2-3 examples.

**Commit:** Change summarizer committed.

---

## Phase 3: Core API (Hour 3-4)

### Task 3.1: Resource search endpoint

**Objective:** `/search` — founder submits query, gets ranked results.

**Files:**
- Create: `backend/app/routers/search.py`

**Flow:**
1. Receive `POST /api/search` with `{ "query": "...", "profile_id": "optional" }`
2. If `profile_id` provided, load profile context.
3. Parse query with intent parser.
4. Hybrid retrieval:
   - Structured filters (WHERE type='grant' AND location @> ['Detroit'])
   - Semantic similarity over embedding
5. Rank by combined score.
6. For top 5, generate explanations via Granite.
7. Return JSON with `results` array.

**Response shape:**
```json
{
  "query_parsed": {"location": "Detroit", "stage": "pre-revenue", ...},
  "results": [
    {
      "resource": {...},
      "fit_explanation": "This fits you because...",
      "next_step": "Apply by August 15 at...",
      "confidence_badge": "Verified 2 weeks ago",
      "fit_score": 0.94
    }
  ]
}
```

**Test with curl:**
```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "solo founder in detroit pre-revenue manufacturing grants"}'
```

**Commit:** Search endpoint committed.

---

### Task 3.2: Agent/scout simulation endpoint

**Objective:** `/scout/run` — simulated daily agent run for demo.

**Files:**
- Create: `backend/app/routers/scout.py`

**Flow:**
1. Load profile.
2. Step 1 — VERIFY: Check top 10 matching resources. Return which ones are still active.
3. Step 2 — FETCH: Simulate monitoring feeds. "Found 1 new event from startdtw.com."
4. Step 3 — MATCH: Check if new resources fit profile.
5. Step 4 — COMPOSE: Generate digest text.
6. Return digest + changes.

**For demo:** This is a single synchronous call. In production it would run as a cron.

**Response includes:** `verification_results`, `new_resources_found`, `digest_text`, `changes_detected`.

**Commit:** Scout endpoint committed.

---

### Task 3.3: Profile CRUD + auth

**Objective:** `/profiles` endpoints with Supabase auth.

**Files:**
- Create: `backend/app/routers/profiles.py`

**Endpoints:**
- `POST /api/profiles` — create (requires auth)
- `GET /api/profiles/me` — get current user's profile
- `PATCH /api/profiles/me` — update

**Uses Supabase auth middleware to validate JWT.

---

## Phase 4: Frontend (Hour 4-6)

### Task 4.1: Next.js scaffold + Supabase auth

**Objective:** Initialize Next.js app with Supabase client-side auth.

**Commands:**
```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --eslint --app --no-src-dir
npm install @supabase/supabase-js @supabase/auth-ui-react
```

**Create:**
- `frontend/lib/supabase.ts` — client initialization
- `frontend/app/auth/callback/page.tsx` — OAuth callback
- `frontend/app/login/page.tsx` — login with Supabase Auth UI

**Commit:** Frontend scaffold committed.

---

### Task 4.2: Founder chat interface

**Objective:** Single-page chat UI. Founder types query, sees results.

**Files:**
- Create: `frontend/app/page.tsx` (hero + chat)
- Create: `frontend/components/ChatInput.tsx`
- Create: `frontend/components/ResultCard.tsx`

**Design:**
- Centered chat input (like Perplexity/ChatGPT)
- Results appear as cards below
- Each card: resource name, type badge, fit explanation, next step, confidence badge
- Follow-up suggestion chips: "Refine by location", "Show grants only", "Earlier deadlines"

**API integration:** `fetch('http://localhost:8000/api/search', {body: JSON.stringify({query})})`

**Demo query hardcoded:** Show "solo Black woman founder Detroit pre-revenue manufacturing" → results.

**Commit:** Chat interface committed.

---

### Task 4.3: Scout run visualization

**Objective:** Show the agent running in real time (simulated steps).

**Files:**
- Create: `frontend/components/ScoutRun.tsx`

**Design:**
- Stepper UI: VERIFY → FETCH → MATCH → COMPOSE
- Each step shows animation + result
- Final: digest card with "Here's what changed today"
- CTA: "Set up daily scout" (form for email/profile)

**For demo:** Trigger via button. Not actually scheduled.

---

### Task 4.4: Operator dashboard

**Objective:** Dashboard for StartMidwest staff. Shows resources needing review.

**Files:**
- Create: `frontend/app/dashboard/page.tsx`
- Create: `frontend/components/ReviewQueue.tsx`

**Features:**
- "Resources flagged this week" (mock data: 5 resources)
- For each: old value → new value → approve/reject buttons
- "Add new resource" form
- Stats: total active, stale, pending review

**For demo:** Use mock data. Show the concept.

---

## Phase 5: Multi-State + Freshness Demo (Hour 6-7)

### Task 5.1: Config-driven state switching

**Objective:** Same backend, different data source based on state parameter.

**Files:**
- Modify: `backend/app/routers/search.py` — add `?state=michigan|illinois` param

**Logic:** When `state=illinois`, filter resources WHERE location @> ['Illinois'].

**Frontend:** Toggle or query param to switch states. Show Michigan → Illinois → both have working results.

**Commit:** Multi-state switch committed.

---

### Task 5.2: Demo video script + recording

**Objective:** Prepare and record 2-min demo video.

**Script (2 minutes):**
```
[0:00-0:10] Hook: "Michigan loses founders because they can't find help. Trestle fixes that."
[0:10-0:35] Founder search: Type query → results appear with personalized explanations
[0:35-0:55] Scout run: Hit "Run my scout" → watch agent verify/fetch/match/compose
[0:55-1:15] Freshness: Show operator dashboard → approve a change → founder sees updated data
[1:15-1:35] Multi-state: Switch to Illinois → same architecture, different resources
[1:35-1:55] Close: "Aisha discovers what she didn't know existed. She stays in Detroit."
```

**Record with:** Screen recording tool (QuickTime, OBS). Voiceover.

---

## Phase 6: Writeup & Submission (Hour 7-8)

### Task 6.1: Problem/Solution writeup

**Objective:** Written submission per hackathon requirements.

**Sections:**
1. Problem Statement (150 words)
2. Solution Overview (200 words)
3. Technology Used (IBM watsonx.ai Granite, Supabase, Next.js, FastAPI)
4. Michigan Impact (150 words)
5. Future Roadmap (100 words)

---

### Task 6.2: Code repository cleanup

**Objective:** Clean repo, add README, make sure it runs.

**Files:**
- `README.md` — setup instructions, demo link
- `backend/README.md` — API docs
- `frontend/README.md` — frontend docs
- `.env.example` files (no real keys)
- `docs/demo_video.md` — link to video

**Verify:** `docker-compose up` or `make dev` works.

---

## INVENTORY: What Must Work for the Demo

### The "Golden Path" (demo flow that must not break):
1. Founder opens app → sees chat input
2. Types: "solo Black woman founder in Detroit pre-revenue building AI for manufacturing. What grants in next 90 days?"
3. Backend parses intent → searches resources → returns 3-5 ranked results
4. Each result has: name, type badge, fit explanation, next step, confidence badge
5. Founder clicks "Run my daily scout"
6. Scout animation: VERIFY → FETCH → MATCH → COMPOSE
7. Final digest appears with 1-2 new items + 1 removed item with explanation
8. Switch to Illinois query → returns Illinois resources
9. Operator dashboard: 5 resources flagged, approve one

### The Backup Plan:
If the live app breaks during judging, the demo video shows the full flow. The video is the primary deliverable; the live app is bonus.

---

## RISK REGISTER

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| IBM watsonx API not responding | Medium | High | Cache sample outputs; use mock Granite responses for demo |
| Supabase free tier hits limits | Low | High | Have local PostgreSQL fallback; data is small |
| Embedding generation takes too long | Medium | Medium | Pre-generate before hackathon; upload to DB |
| Frontend teammate drops | Medium | High | Build minimal HTML frontend as backup; no Next.js dependency |
| Demo video fails to upload | Low | Medium | Have backup on YouTube + Google Drive |
| Scope creep (building too much) | HIGH | HIGH | Strict 8-hour cutoff; no new features after hour 6 |

---

## COMMIT STRATEGY

Every task = one commit. Clean history for judges to review.
```
chore: scaffold project structure
data: ingest StartMidwest baseline
feat: watsonx Granite client
feat: intent parser
feat: search endpoint with RAG
feat: chat UI
feat: scout run visualization
feat: operator dashboard
data: add Illinois resources
feat: multi-state switching
docs: demo video + writeup
```
