# Trestle — High-Level Design (HLD) v2

**Owner:** Aurthur (Architecture)  
**Status:** Draft — pending Floyd + Jason review, then Arceus approval  
**Date:** May 23, 2026  
**Version:** 0.2  
**Parent PRD:** `/Users/harshavardhan/trestle/docs/discovery/prd-trestle-grants.md`

---

## 1. Executive Summary

Trestle is a **24/7 conversational personal assistant for startup founders**. It learns each founder's company, stage, constraints, and goals through natural dialogue — then proactively surfaces opportunities, answers questions, and handles research tasks. **Grants are v1 of many future skills** (competitor tracking, investor matching, regulatory planning, team & hiring, lab access, legal & IP monitoring). The architecture is built to plug new skills into a shared founder profile without rewriting the core.

This HLD translates the approved PRD (v2) into a deployable system architecture. The design prioritizes:

1. **Speed to market:** 8–12 week MVP window before competitors close the conversational moat.
2. **Boring technology:** PostgreSQL + FastAPI + Next.js. No microservices, no Kafka, no premature scale.
3. **Resilience:** Every external dependency has timeout, retry, circuit breaker, and degraded-mode fallback.
4. **Privacy by design:** No PHI. Company metadata only. Clerk for auth, scoped row-level security.
5. **Multi-skill ready:** New skills share the founder profile and conversation memory. No re-onboarding.

---

## 2. System Architecture Overview

Monolith-first. Three deployable units communicating over HTTPS:

```
+-------------------------------------------------------------+
|  CLIENT LAYER                                               |
|  +------------------+    +--------------------------------+ |
|  | Landing Page     |    | Chat Widget (Web / Telegram)   | |
|  | Next.js          |    | Next.js / Bot API              | |
|  +------------------+    +--------------------------------+ |
+-------------------------------------------------------------+
                          |
+-------------------------------------------------------------+
|  API GATEWAY (FastAPI)      /api/v1                         |
|  +------------------+    +------------------+             |
|  | Chat Router      |    | Auth Router      |             |
|  | Grant Router     |    | Alert Router     |             |
|  | Profile Router   |    | Lifecycle Router |             |
|  | Auth Middleware  |    | Merge Router     |             |
|  +------------------+    +------------------+             |
+-------------------------------------------------------------+
                          |
+-------------------------------------------------------------+
|  APPLICATION LAYER                                          |
|  +------------------+    +------------------+             |
|  | Conversation     |    | Eligibility      |           |
|  | Orchestrator     |    | Matching Engine  |             |
|  | (stateful, multi-|    +------------------+             |
|  |  skill aware)    |                                   |
|  +------------------+    +------------------+             |
|  | Proactive Alert  |    | Grant Data       |            |
|  | Scheduler        |    | Pipeline         |             |
|  +------------------+    +------------------+             |
|  +------------------+                                      |
|  | Skill Plugin     |  (future: competitor, investor,    |
|  | Registry         |   regulatory, hiring, lab, legal)   |
|  +------------------+                                      |
+-------------------------------------------------------------+
                          |
+-------------------------------------------------------------+
|  INFRASTRUCTURE LAYER                                       |
|  +------------------+    +------------------+             |
|  | PostgreSQL       |    | Redis            |             |
|  | (Supabase)       |    | (Cache + Queue)  |           |
|  +------------------+    +------------------+             |
|  +------------------+    +------------------+             |
|  | Clerk (Auth)     |    | OpenAI/Anthropic |            |
|  |                  |    | (LLM via API)    |             |
|  +------------------+    +------------------+             |
|  +------------------+                                      |
|  | Grant External   |  (NIH, NSF, Grants.gov, partners)   |
|  | Data Sources     |                                      |
|  +------------------+                                      |
+-------------------------------------------------------------+
```

### Multi-Skill Architecture Note

The founder profile is **general-purpose, not grant-specific**. All future skills read from and write to the same profile:

```
FOUNDER PROFILE (shared across all skills)
├── Company basics        ← read by: grants, investor, hiring, lab
├── Product & regulatory  ← read by: grants, competitor, regulatory
├── Financials            ← read by: grants, investor, hiring
├── Eligibility signals   ← read by: grants, investor
└── Preferences           ← read by: all skills
```

New skills register in a **Skill Plugin Registry** (a `skills` table + runtime config). The Conversation Orchestrator loads the active skill's context into the system prompt. The agent can switch skills mid-conversation: "Switch to investor matching" triggers a skill context swap without losing conversation history.

---

## 3. Component Architecture

### 3.1 Client Layer

**Landing Page (Next.js, Vercel)**
- Static marketing page + "Talk to Trestle" CTA.
- Chat widget embeds via iframe or direct component.
- Clerk for authentication (OAuth, magic link). **No auth wall before first message.**

**Chat Widget (Web)**
- Real-time message stream via Server-Sent Events (SSE) over `/api/v1/chat/stream`.
- React state: message history + pending message UI.
- Anonymous sessions allowed for first contact; Clerk auth triggered on profile save, grant tracking, or proactive alert subscription.
- **Auth is delayed:** demonstrate value before asking for identity.

**Telegram Bot (Future / Stretch)**
- Webhook → FastAPI `/api/v1/bots/telegram`.
- Shares session store with web chat via `user_id`.
- Same orchestration pipeline, different transport.

### 3.2 API Gateway (FastAPI, Render/Railway)

Single monolith exposing REST + SSE endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/chat/message` | POST | Send a chat message, receive async job ID |
| `/api/v1/chat/stream/{job_id}` | SSE | Stream LLM tokens + structured events back to client |
| `/api/v1/grants/match` | POST | Trigger eligibility match for a user profile |
| `/api/v1/grants/{id}` | GET | Deep dive on a specific grant |
| `/api/v1/grants/{id}/lifecycle` | POST | Transition grant through lifecycle states |
| `/api/v1/grants/track` | POST | Add/remove a grant from user's tracking list |
| `/api/v1/alerts` | GET | List pending + historical alerts for user |
| `/api/v1/alerts/dismiss` | POST | Dismiss an alert, capture reason |
| `/api/v1/users/profile` | GET/PUT | General-purpose founder profile CRUD |
| `/api/v1/users/preferences` | PUT | Alert frequency, channel preference, min grant size |
| `/api/v1/auth/magic-link` | POST | Request magic link email |
| `/api/v1/auth/verify` | GET | Validate magic link token, issue Clerk JWT |
| `/api/v1/auth/merge-session` | POST | Merge anonymous session into authenticated user |
| `/api/v1/auth/forgot-password` | POST | Request password reset |
| `/api/v1/auth/reset-password` | POST | Reset password with token |

Auth middleware:
- Clerk JWT validation on every request (except anonymous chat first contact).
- Anonymous sessions get a signed cookie with 30-day TTL; conversion to Clerk auth migrates all data.
- Role: `founder` (default), `admin` (future).

### 3.3 Application Layer

#### 3.3.1 Conversation Orchestrator

The heart of Trestle. A **stateful dialogue management system** — not a simple chatbot. It drives adaptive questioning, multi-turn profile extraction, skill switching, and grant lifecycle awareness.

**Architecture:** Compound AI agent pattern with explicit state machine.

```
[User Input]
    |
    v
[Intent Classifier] -- LLM call #1 (cheap model, structured JSON output)
    |                    Classifies: greet | discover | match_request | deep_dive |
    |                    grant_question | dismiss | edge_case | vague | unknown |
    |                    skill_switch | profile_update | lifecycle_action
    v
[State Manager] -- Reads user profile + last 10 messages + active skill from DB
    |                Determines: which flow, what the agent needs to ask next,
    |                whether profile completeness threshold (0.7) is met
    v
[Question Engine] -- If intent = "discover" and profile incomplete:
    |                    Builds adaptive follow-up questions (1-2 at a time)
    |                    Infers fields from context; skips if user refuses
    |                    Updates "completeness score" after each turn
    v
[Context Builder] -- Assembles prompt:
    |                   - System prompt (persona + active skill context)
    |                   - User profile snapshot
    |                   - Relevant grant context (if match/query)
    |                   - Conversation history (last 20 turns)
    |                   - Active skill instructions
    |                   - Guardrails ("cite sources", "say I don't know",
    |                     "never present grant without source URL")
    v
[LLM Completion] -- Streaming via OpenAI / Anthropic API
    |                Temperature 0.4 for reliability.
    |                Max tokens 2,000 per response.
    v
[Output Guardrails] -- Post-processing layer:
    |                   - Structured extraction: did we learn new profile fields?
    |                   - Source verifier: every grant mention must have source_url
    |                   - Tone checker: founder-friendly language validation
    |                   - Lifecycle state detector: did user imply a state change?
    v
[Session Writer] -- Async write to DB:
    |                   - Append message to conversation log
    |                   - Update extracted profile fields (if any)
    |                   - Update grant suggestions / dismissals / lifecycle states
    |                   - Check if signup trigger conditions met
    v
[Stream to Client]
```

**Key decisions:**
- **Intent classifier is a separate fast call** (GPT-4o-mini or Claude Haiku) before the main completion. This lets us inject relevant grant context and skill context into the prompt without paying for a full completion on every turn.
- **Profile extraction runs in parallel** with streaming the response. The user sees tokens immediately; profile updates happen async.
- **Guardrails are synchronous** — if a hallucinated deadline is detected or source_url is missing, the stream is truncated and a correction message is appended.
- **Question Engine is explicit** — not just "ask whatever the LLM wants." A deterministic module decides which fields are missing, which can be inferred, and what to ask next. Max 2 questions per turn.
- **Signup trigger detector** runs after every turn. If the user saves a grant, asks for a reminder, or hits 3rd session → soft prompt for auth.

#### 3.3.2 Eligibility Matching Engine

Transforms a founder profile into a ranked list of grants. **Every match includes a clickable source_url.**

**Data model:**
- Grant records stored in PostgreSQL with structured eligibility criteria as JSONB.
- Each grant has `eligibility_rules`: deterministic JSON object representing hard constraints.
- **`source_url` is NOT NULL.** No URL = no grant. Period.

**Matching pipeline:**
```
[User Profile] ──SQL query──> [Hard Filter]
                                (stage, location, team_size, funding_raised,
                                 minimum_grant_size, industry_tags, regulatory_stage
                                 → eliminates 80-90% of grants)
                                    |
                                    v
                              [Scoring Layer]
                                (secondary features: industry relevance,
                                 regulatory pathway match, deadline proximity,
                                 past success rate for similar profiles)
                                    |
                                    v
                              [LLM Qualifier]
                                (for top 15 candidates, cheap LLM call
                                 to verify "soft" fit)
                                    |
                                    v
                              [Result: max 5 grants]
                                Each with: name, amount, deadline, source_url,
                                confidence (strong/partial/informational),
                                why_you_qualify explanation
```

**Caching:** Match results cached in Redis keyed by `hash(profile)` with 1-hour TTL. Profile changes invalidate cache.

#### 3.3.3 Grant Data Pipeline

Ingests grant data from external sources into the matching engine. **source_url is mandatory for every record.**

**Sources (MVP):**
1. NIH SBIR/STTR — bulk XML download, parse, store.
2. NSF SBIR — API or scraped feed.
3. Grants.gov — bulk download if available; otherwise API.
4. State programs — manual seed for top 5 states.
5. Private foundations — manual seed for high-value biomed-specific grants.

**Pipeline architecture:**
```
[Scheduler: Daily at 2 AM] ──> [Ingest Job]
                                    |
                                    v
                              [Fetch from sources]
                                    |
                                    v
                              [Normalize to Trestle schema]
                              (source_url required, url verification)
                                    |
                                    v
                              [Upsert into PostgreSQL]
                                    |
                                    v
                              [Invalidate Redis cache]
                                    |
                                    v
                              [Trigger proactive alert scan]
                                    |
                                    v
                              [Weekly URL verification job]
                              (HEAD request all source_urls, flag 404s)
```

**Resilience:**
- Each source fetch has 30s timeout, 3 retries with exponential backoff.
- Circuit breaker: if a source fails 3 times in 24h, skip until next day. Log and alert admin.
- Degraded mode: if no fresh data, serve from cache with "last updated" timestamp visible to user.
- Broken URLs: weekly HEAD check. If 404 → `url_is_live = false`, suppress from matches, alert admin.

#### 3.3.4 Proactive Alert Scheduler

Monitors for events that should trigger agent-initiated messages.

**Trigger types:**
1. **New grant match** — data pipeline found a new grant matching an existing user profile.
2. **Deadline approaching** — grant in user's tracking list has deadline within 30/7/1 days.
3. **Profile change unlock** — user updated profile and now qualifies for previously unmatched grants.
4. **Re-engagement** — user inactive >30 days.
5. **Grant update** — previously dismissed grant changed eligibility rules.
6. **Lifecycle nudge** — grant in INTERESTED/STARTED state with no activity for 30 days.
7. **Review check-in** — grant in UNDER_REVIEW at 50% of expected review duration.
8. **Reconsideration window** — next cycle opens for a RECONSIDERING grant.

**Scheduler:**
- Celery beat (or APScheduler) running every 15 minutes.
- Redis as task queue + result backend.
- Alert generation is an async job: for each trigger, call matching engine, format message via LLM, queue for delivery.

**Delivery channels (MVP = in-app + email, stretch = Telegram/Slack):**
- In-app: Supabase realtime subscription pushes to client.
- Email: Resend API.

**Rate limiting:** Max 1 proactive alert per user per 24 hours. Batched in single message if multiple triggers fire.

---

## 4. Data Flows by Conversational Flow

### 4.1 Flow 1: First Contact (Anonymous)

```
[Visitor clicks "Talk to Trestle"]
    |
    v
[Client] POST /api/v1/chat/message
         {session_id: null, text: "Hey — I'm Trestle..."}
    |
    v
[API] Create anonymous session (UUID v4, 30-day signed cookie)
      Generate system welcome message
      Return job_id
    |
    v
[Client] SSE /api/v1/chat/stream/{job_id}
         Receives: "Hey — I'm Trestle... What are you working on?"
    |
    v
[User types response]
    |
    v
[API] Intent classifier: "discover"
      No profile yet → Conversation orchestrator enters discovery mode
      Stream response asking 1-2 follow-up questions
      Profile extractor runs async, writes partial profile to DB
      No auth prompt. Value first.
```

### 4.2 Flow 2: Discovery Dialogue (Adaptive Probing)

```
[User answers questions over 3-8 turns]
    |
    v
[Conversation Orchestrator]
  - After each turn: extract any new fields (company_name, stage, location, etc.)
  - Store in `profiles` table (JSONB merge update)
  - Track "completeness score" (0-1); when >0.7, agent can offer matching
  - Question Engine decides next question (max 2 at a time)
  - Allow skipping: "If you don't want to share revenue, that's fine"
    |
    v
[User says "find me grants" or agent detects readiness]
    |
    v
[Trigger Flow 3]
```

### 4.3 Flow 3: Eligibility Matching

```
[Intent: "match_request"]
    |
    v
[API] Read full user profile from DB
    |
    v
[Matching Engine]
  - Check Redis cache for hash(profile)
  - If miss: run SQL hard filter → scoring → LLM qualifier
  - If hit: return cached results
  - Every result MUST include source_url
    |
    v
[Conversation Orchestrator]
  - Format top 3-5 grants as natural response
  - Include: name, amount, deadline, source_url, confidence, why_you_qualify
  - Add CTAs: "Tell me more", "Track this", "Show next 3"
    |
    v
[Stream to client]
  "I found 3 grants that match your profile...
   1. NIH SBIR Phase I — $400K | Due June 30
      → https://grants.gov/search-results-detail/PA-FY26-123"
```

### 4.4 Flow 4: Post-Match Lifecycle (14-State Machine)

```
[User says "track this" or "I'm interested"]
    |
    v
[API] Create grant_lifecycle record
      status = SAVED → INTERESTED (if user says "tell me more")
      Set deadline reminder timers
    |
    v
[User progresses through states:]
  INTERESTED → STARTED → APPLIED → SUBMITTED → UNDER_REVIEW
                                              ↓
                                        ┌─ ACCEPTED → AWARDED → ARCHIVED
                                        │
                                        └─ REJECTED → RECONSIDERING → STARTED (reapply)
                                                            ↓
                                                      DISMISSED → ARCHIVED
    |
    v
[Proactive nudges fire per state:]
  - 30 days pre-deadline: "Grant due in 30 days"
  - 7 days pre-deadline: "Now's the time"
  - 50% review mark: "Any updates?"
  - Expected decision date: "Decision should be in soon"
  - 30 days no activity: "Still planning to apply?"
  - Next cycle opens: "Grant is open again. Try again?"
```

### 4.5 Flow 5: Auth Trigger & Session Merge

```
[Signup trigger fires] (save grant, 3rd session, ask for reminder, proactive alert mention)
    |
    v
[Agent soft prompt:]
  "If you create an account, I'll remember all these matches and
   nudge you when deadlines approach. Want to do that now?"
    |
    v
[User accepts]
  → Inline email input or Google OAuth
  → Backend sends magic link or processes OAuth callback
  → POST /api/v1/auth/merge-session with anon_session_id
  → Merge: conversations, profile, tracked grants, dismissed grants
  → Invalidate anon cookie
  → Agent: "Done. All your [N] matches are saved."
    |
    v
[User declines]
  → Continue anonymous. Persist to anon session.
  → After 3 declines total → stop prompting. Mark no_auth: true.
  → Session expires after 30 inactivity days.
```

### 4.6 Flow 6: Deep Dive

```
[User: "Tell me about the NIH SBIR"]
    |
    v
[Intent: "deep_dive"]
    |
    v
[API] Read grant details from DB + source_url verification status
    |
    v
[Conversation Orchestrator]
  - Build context-rich prompt: grant eligibility rules, deadlines,
    budget requirements, common pitfalls, source_url
  - Cross-reference with user profile to personalize
  - Structure response: Eligibility, Deadlines, Budget, Tips, Pitfalls, Next Steps
  - Every claim backed by source_url
    |
    v
[Stream to client with citations]
```

### 4.7 Flow 7: Edge Cases

Handled within Conversation Orchestrator via explicit guardrails in system prompt + post-processing:

| Edge | Mitigation |
|------|------------|
| Agent is wrong | Guardrail detects "correction" intent → triggers profile update + apology flow + re-match |
| New info changes eligibility | Profile change → automatic cache invalidation → re-run match → explain what opened/closed |
| User disagrees | Dismissal captured with reason in `grants_dismissed` table; feeds negative signal to matching model |
| User vague | LLM fallback: reframe to simpler binary questions |
| User defensive | System prompt instructs: "Respect boundaries. Note limitation honestly. Continue with what you have." |
| User contradicts memory | Agent: "Last time you said X. Has that changed?" → update profile, re-run match |
| Dead source URL | Agent: "Link was broken as of [date]. Want me to search for an updated link?" |

---

## 5. Technology Choices & Justification

| Layer | Choice | Alternatives Rejected | Rationale |
|-------|--------|----------------------|-----------|
| **Frontend** | Next.js (App Router) | SvelteKit, Remix | Team expertise from ImpacterAI. Vercel hosting. Clerk integration first-class. SSR for SEO on landing page. |
| **Backend** | FastAPI | Django, Node/Express | Python ecosystem for NLP + ML. Native async support for SSE streaming. Typed with Pydantic for API contracts. |
| **Database** | PostgreSQL (Supabase) | MongoDB, DynamoDB | Relational data. JSONB for flexible profile/grant criteria. Row-level security. Built-in auth. Cost-effective. |
| **Auth** | Clerk | Supabase Auth, Auth0 | Best-in-class UX. OAuth + magic link + session management. Role-based access. |
| **Cache + Queue** | Redis | RabbitMQ, SQS | Simplicity. Used for session cache, match result cache, and Celery task queue. Self-managed or Upstash. |
| **LLM** | OpenAI GPT-4o (primary), Claude Haiku (intent classifier fallback) | Local LLaMA, xAI | Speed and reliability. GPT-4o for main orchestrator. Cheaper Haiku for intent classification. Local models later for cost. |
| **Task Queue** | Celery + Redis | Bull, RQ | Python-native. Proven. Beat scheduler for alerts. |
| **Hosting** | Vercel (frontend) + Render/Railway (backend) | AWS, GCP | No AWS until revenue. $30-100/mo total for MVP. |
| **Realtime** | Supabase Realtime | Socket.io, Pusher | Comes with Supabase. Row-level security channels. |
| **Email** | Resend | SendGrid, AWS SES | Simple API. Good deliverability. Free tier 100/day. |

---

## 6. External Integrations

| System | Purpose | Integration Type | Failure Mode |
|--------|---------|-----------------|------------|
| **Clerk** | Auth, sessions, users | REST API + JWT | Auth unavailable → redirect to maintenance page |
| **OpenAI/Anthropic** | LLM completions, embeddings | HTTP API (SDK) | Timeout after 10s → cached fallback response + "try again later" |
| **NIH / Grants.gov** | Grant data feed | Bulk download / REST | Skip source, serve cached data, flag stale |
| **Resend** | Email alerts (magic link, proactive nudges) | SMTP / REST API | Queue retries ×3; if still failing, in-app only |
| **Supabase** | DB + realtime + auth | SDK / REST / Websocket | Connection pool exhaustion → 503 with retry-after |
| **Telegram Bot API** (stretch) | Bot channel | Webhooks | Webhook failures → polling fallback |

---

## 7. Failure Modes & Mitigation

| Failure | Impact | Detection | Mitigation |
|---------|--------|-----------|------------|
| **LLM hallucinates grant deadline or amount** | High trust erosion | Post-process guardrail cross-references DB | If mismatch > stream correction. If critical > block response and flag. |
| **LLM API timeout/rate limit** | Chat frozen | 10s timeout on streaming | Return "Trestle is thinking too hard — try again in a moment" + log. |
| **Grant data stale (>24h old)** | Bad recommendations | Pipeline health check | Show "last updated" timestamp. Alert admin. |
| **External grant source down** | Narrower database | Pipeline error counter | Circuit breaker skips source. Degraded service. |
| **PostgreSQL connection pool exhausted** | All requests fail | Connection monitor | Proper pool config: max 20, idle_timeout 30s. Alert at 80% utilization. |
| **Redis down** | No caching, no queue | Health check | Backend falls through to DB directly. Alerts disabled. |
| **Auth token expired mid-session** | User kicked out | Clerk middleware | 401 → trigger re-auth flow gracefully. Preserve chat state. |
| **Conversation state machine corruption** | Agent loops or ignores user | Telemetry: avg turns per session spike | State validation on every turn. Max 100 turns per session hard cap. |
| **source_url is dead (404)** | Broken trust | Weekly HEAD check | Suppress grant from matches. Flag for admin update. Agent warns user. |

---

## 8. Security & Privacy

### 8.1 Data Classification

| Data | Classification | Storage |
|------|---------------|---------|
| Company profile (stage, funding, team) | PI (business) | PostgreSQL, encrypted at rest |
| Conversation history | PI (business) | PostgreSQL, encrypted at rest, TTL 2 years |
| Grant database | Public | PostgreSQL |
| User credentials | Sensitive | Clerk (never enters our system) |
| PHI / patient data | **PROHIBITED** | — |

### 8.2 Key Controls

1. **No PHI ever.** System prompt explicitly instructs agent not to ask for or store clinical/patient data.
2. **Row-level security (RLS):** Supabase policies ensure users can only read their own profiles and conversations.
3. **Clerk JWT:** Short-lived (15 min). Refresh token server-side.
4. **Rate limiting:** 60 requests/min per IP, 20 chat messages/min per user.
5. **CORS:** Strict origin whitelist. No wildcard.
6. **Audit log:** All profile mutations, grant tracking, and lifecycle state changes logged with user_id and timestamp.
7. **Data retention:** Conversations retained 2 years. Grants dismissed retained 1 year for model training signals. Right to delete per GDPR/CCPA.
8. **Anonymous session security:** Signed cookie, HttpOnly, Secure, SameSite=Lax. 30-day TTL. No PII stored in anonymous sessions.

---

## 9. Performance Targets

Derived from success criteria in the PRD:

| Target | Metric | How Measured |
|--------|--------|--------------|
| **<5 min time-to-first-match** | Time from first contact to first grant recommendation | Frontend instrumentation: `time_to_first_value` event |
| **≤5 adaptive questions** | Avg questions before match engine fires | DB query on conversation length at first match trigger |
| **<500ms API response** | P95 latency on non-streaming endpoints | Render/Railway APM |
| **<2s time-to-first-token** | P95 latency from message send to first streamed token | Frontend timing on SSE connection |
| **99.9% uptime** | Service availability | Uptime monitor on landing page + API health |

---

## 10. Decision Log (ADRs)

### ADR-001: Monolith over Microservices
**Decision:** Single FastAPI monolith, not separate services for chat, matching, alerts.
**Rationale:** Team of 2-3 engineers. 8-12 week MVP. Network hop overhead > isolation benefit. Split later when a single component justifies its own deploy.
**Status:** Accepted.

### ADR-002: Supabase over Managed Postgres
**Decision:** Supabase (hosted PostgreSQL + realtime + auth + RLS).
**Rationale:** Faster setup than RDS/Cloud SQL. Built-in realtime subscriptions for proactive alerts. RLS simplifies authorization. Free tier covers MVP.
**Status:** Accepted. Revisit at 10K MAU.

### ADR-003: SSE over WebSockets for Chat
**Decision:** Server-Sent Events from FastAPI to Next.js for streaming LLM tokens.
**Rationale:** SSE is HTTP-native, works through most proxies/firewalls, simpler reconnection. WebSockets add complexity for marginal gain. Revisit for bidirectional real-time collaboration features.
**Status:** Accepted.

### ADR-004: OpenAI over Local LLM
**Decision:** GPT-4o via API for MVP, not self-hosted Llama/DeepSeek.
**Rationale:** Need reliability and speed for 8-12 week window. Local models = GPU infra + ops burden + slower throughput. Cost acceptable at <1K DAU.
**Status:** Accepted. Migration path: evaluate local 70B model when DAU > 5K or monthly API cost > $500.

### ADR-005: Intent Classifier as Separate Fast Call
**Decision:** Pre-classify user intent with a cheap LLM (Haiku/4o-mini) before the main completion.
**Rationale:** Building the right context (grant data, profile snapshot, active skill) before the main LLM call saves tokens and improves coherence. Adds ~200ms but saves ~2000 tokens on misrouted completions.
**Status:** Accepted.

### ADR-006: Delayed Auth (Value-First Signup)
**Decision:** Anonymous sessions with delayed signup triggers, not auth-wall-first.
**Rationale:** PRD success metric: ≥20% of users who see first match convert to signup. Auth before value = dead. Session merge ensures no data loss on conversion.
**Status:** Accepted.

### ADR-007: source_url as Non-Nullable
**Decision:** Every grant record MUST have a `source_url`. No URL = no grant.
**Rationale:** Trust is the product. A grant without a verifiable source URL is indistinguishable from hallucination. Weekly verification job keeps links fresh.
**Status:** Accepted.

### ADR-008: Multi-Skill Plugin Registry
**Decision:** Skills register in a `skills` table + runtime config. Conversation Orchestrator loads active skill context into system prompt.
**Rationale:** Prevents hard-coding skill logic in the orchestrator. New skills (investor matching, competitor tracking) can be added without deploying new code. The founder profile is general-purpose and shared.
**Status:** Accepted. v1 ships with one skill (grants) but the registry is built.

---

## 11. Out of Scope for HLD → LLD

The following will be detailed in the LLD (separate document):
- Exact database schema (tables, indexes, constraints, soft deletes, 14-state lifecycle table)
- API request/response schemas in OpenAPI 3.0 (auth endpoints, lifecycle endpoints, source_url requirements)
- LLM prompt templates and guardrail code
- Grant data normalization schema with source_url enforcement
- Alert message templates and delivery retry logic
- Observability dashboard configuration
- Auth state machine (anonymous → signup → merge) in detail

---

## 12. Next Steps

1. **Floyd review:** Frontend data needs, chat widget SSE contract, Clerk integration points, auth flow UX.
2. **Jason review:** API surface area, matching engine SQL, profile extraction logic, auth merge transaction safety.
3. **Arceus approval:** Sign off on tech stack (Supabase + FastAPI + Next.js) and hosting budget.
4. **Post-approval:** Produce LLD + DB schema + OpenAPI contract.

---

*HLD by Aurthur | Pending Floyd + Jason review → Arceus gate.*
