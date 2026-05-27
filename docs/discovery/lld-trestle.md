# Trestle - Low-Level Design (LLD) v2

**Owner:** Aurthur (Architecture)  
**Status:** Draft - pending Floyd + Jason review, then Arceus approval  
**Date:** May 23, 2026  
**Version:** 0.2  
**Parent HLD:** `/Users/harshavardhan/trestle/docs/discovery/hld-trestle.md`

---

## 1. Tech Stack Decision & Docker Strategy

### 1.1 Full Stack

| Layer | Technology | Version | Justification |
|-------|-----------|---------|---------------|
| **Frontend** | Next.js (App Router) | 15.x | SSR/SSG for landing SEO. React Server Components reduce client JS. Vercel native. |
| **Frontend UI** | Tailwind CSS + shadcn/ui | 3.x | Rapid component assembly. Accessible primitives. No design-system build from scratch. |
| **Backend** | FastAPI | 0.115+ | Python ecosystem for NLP/ML. Native async. Auto OpenAPI generation. Pydantic v2. |
| **Database** | PostgreSQL (Supabase) | 15.x | JSONB for flexible grant rules and founder profile. Row-level security. Built-in auth helpers. Free tier. |
| **Cache + Queue** | Redis (Upstash or self-hosted) | 7.x | Session cache, match cache, Celery broker + backend. |
| **Auth** | Clerk | 2025-05 | JWT sessions, OAuth, magic link, role-based. First-class Next.js SDK. |
| **LLM** | OpenAI GPT-4o / Anthropic Claude Haiku | API | GPT-4o for orchestrator. Haiku/4o-mini for intent classification. |
| **Task Queue** | Celery + Redis | 5.x | Python-native. Beat scheduler for alerts and proactive nudges. |
| **ORM / Migrations** | SQLAlchemy 2.0 + Alembic | 2.0+ | Async support. Type-annotated. Alembic for versioned migrations. |
| **Validation** | Pydantic v2 | 2.x | API schemas, LLM structured output, DB DTOs. One model library everywhere. |
| **Hosting (MVP)** | Vercel (frontend) + Render/Railway (backend) | - | <$100/mo. No AWS until revenue. Docker deployable to both. |
| **Realtime** | Supabase Realtime | - | In-app alert push. RLS-protected channels. |
| **Object Storage** | Supabase Storage (S3-compatible) | - | Document exports, grant attachments. No local disk state. |
| **Email** | Resend | - | Simple API. Good deliverability. Free tier 100/day. Magic links + proactive alerts. |
| **Observability** | Logfire (Pydantic) or Sentry | - | Error tracking. Performance tracing. |

### 1.2 Docker Strategy

Local dev and single-node production both use Docker Compose. No Kubernetes until >3 services need independent scaling.

**`docker-compose.yml` services:**

| Service | Image | Ports | Purpose |
|---------|-------|-------|---------|
| `db` | `postgres:15-alpine` | `5432` | PostgreSQL with init scripts |
| `redis` | `redis:7-alpine` | `6379` | Cache + Celery broker |
| `api` | `trestle/api:latest` | `8000` | FastAPI monolith |
| `worker` | `trestle/api:latest` | - | Celery workers (same image, `celery worker` cmd) |
| `beat` | `trestle/api:latest` | - | Celery beat scheduler |
| `web` | `trestle/web:latest` | `3000` | Next.js dev server (local) or static served by nginx (prod) |

**`Dockerfile.api` (multi-stage):**
- Stage 1: `python:3.12-slim` -> install deps via `uv` or `pip`
- Stage 2: copy source, run `uvicorn`
- Image size target: <300MB

**`Dockerfile.web`:**
- `node:20-alpine` -> `npm ci` -> `next build` -> `next start` (or static export to nginx)

**Environment:**
- `.env` for local secrets (gitignored)
- `.env.example` committed with dummy values
- Production secrets injected via Render/Railway environment panels (never in image)

---

## 2. Database Schema

### 2.1 Schema Design Principles

1. **Soft deletes everywhere.** Every table has `deleted_at timestamptz`. Queries filter `WHERE deleted_at IS NULL`.
2. **JSONB for evolving data.** Grant eligibility rules and user profiles change frequently. JSONB with GIN indexes beats schema migrations every week.
3. **Clerk owns identity.** `users.clerk_id` is the source of truth. We store enriched profile data; credentials never touch our DB.
4. **Audit trail.** All mutations to `profiles`, `grant_lifecycle`, `grants_dismissed` logged in `audit_logs`.
5. **Idempotency keys.** Chat messages, alert deliveries, and lifecycle transitions carry `idempotency_key` to prevent duplicate processing on retries.
6. **source_url is non-nullable on grants.** No URL = no grant. Period.
7. **General-purpose founder profile.** The `profiles` table is not grant-specific. All future skills read from and write to the same profile.

---

### 2.2 Table Definitions

#### `users`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK, default gen_random_uuid() | Internal UUID |
| `clerk_id` | `text` | UNIQUE, NOT NULL | Clerk user ID |
| `email` | `text` | UNIQUE, NOT NULL | From Clerk webhook |
| `name` | `text` | nullable | First name from Clerk or user input |
| `role` | `text` | NOT NULL, default 'founder' | `founder`, `admin` |
| `email_verified` | `boolean` | NOT NULL, default false | Required for email alerts |
| `created_at` | `timestamptz` | default now() | |
| `updated_at` | `timestamptz` | default now() | |
| `deleted_at` | `timestamptz` | nullable | soft delete |

**Indexes:**
- `users_clerk_id_idx` UNIQUE ON `clerk_id`
- `users_email_idx` UNIQUE ON `email`

---

#### `anonymous_sessions`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | Session token (UUID v4) |
| `ip_address` | `inet` | nullable | For rate limiting |
| `user_agent` | `text` | nullable | |
| `fingerprint` | `text` | nullable | Device fingerprint hash |
| `profile_snapshot` | `jsonb` | default '{}' | Extracted profile fragments during anonymous session |
| `converted_user_id` | `uuid` | FK -> users.id, nullable | Set when Clerk auth links |
| `merged_at` | `timestamptz` | nullable | When session data was merged to user |
| `expires_at` | `timestamptz` | NOT NULL | now() + 30 days |
| `created_at` | `timestamptz` | default now() | |
| `deleted_at` | `timestamptz` | nullable | |

**Indexes:**
- `anon_sessions_expires_idx` ON `expires_at`
- `anon_sessions_converted_idx` ON `converted_user_id`
- `anon_sessions_fingerprint_idx` ON `fingerprint`

---

#### `profiles` (General-Purpose Founder Profile)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `user_id` | `uuid` | FK -> users.id, NOT NULL, UNIQUE | One profile per user |
| **Company basics** | | | |
| `company_name` | `text` | nullable | |
| `incorporation_type` | `text` | nullable | `delaware_c_corp`, `llc`, `other` |
| `incorporation_country` | `text` | nullable | default 'US' |
| `location_city` | `text` | nullable | |
| `location_state` | `text` | nullable | |
| `location_country` | `text` | nullable | default 'US' |
| `team_size` | `int` | nullable | |
| `team_roles` | `text[]` | default '{}' | e.g. `{'founder', 'scientist', 'engineer'}` |
| **Product & regulatory** | | | |
| `industry_tags` | `text[]` | default '{}' | e.g. `{'medical-device', 'ai-software'}` |
| `product_type` | `text` | nullable | `device`, `drug`, `diagnostic`, `software`, `other` |
| `therapeutic_area` | `text` | nullable | e.g. `neurostimulation`, `oncology` |
| `data_status` | `text` | nullable | `benchtop`, `glp`, `clinical`, `fda_cleared` |
| `regulatory_pathway` | `text` | nullable | `510k`, `pma`, `denovo`, `de-novo`, `exempt`, `ce_mark` |
| **Financials** | | | |
| `monthly_burn_usd` | `bigint` | nullable | |
| `runway_months` | `int` | nullable | |
| `last_raise_amount_usd` | `bigint` | nullable | |
| `last_raise_date` | `date` | nullable | |
| `capital_need_12m_usd` | `bigint` | nullable | |
| **Eligibility signals** | | | |
| `company_age_months` | `int` | nullable | |
| `revenue_usd` | `bigint` | nullable | |
| `has_ip_license` | `boolean` | nullable | University IP exclusive license |
| `prior_sbir_awards` | `int` | nullable | default 0 |
| `sbir_eligible` | `boolean` | nullable | |
| **Preferences** | | | |
| `minimum_grant_size_usd` | `bigint` | nullable | default 300000 |
| `geographic_scope` | `text` | nullable | `us_only`, `uk`, `eu`, `multi_region` |
| `alert_frequency` | `text` | nullable | `daily`, `weekly`, `never` |
| `auth_decline_count` | `int` | NOT NULL, default 0 | Track signup prompt refusals |
| `no_auth` | `boolean` | NOT NULL, default false | Stop prompting after 3 declines |
| **Metadata** | | | |
| `profile_json` | `jsonb` | default '{}' | Catch-all for fields not yet promoted |
| `completeness_score` | `numeric(3,2)` | default 0.0 | 0.0-1.0 |
| `created_at` | `timestamptz` | default now() | |
| `updated_at` | `timestamptz` | default now() | |
| `deleted_at` | `timestamptz` | nullable | |

**Indexes:**
- `profiles_user_id_idx` UNIQUE ON `user_id`
- `profiles_stage_idx` ON `stage`
- `profiles_regulatory_idx` ON `regulatory_pathway`
- `profiles_completeness_idx` ON `completeness_score`
- `profiles_profile_json_gin_idx` GIN ON `profile_json`

---

#### `skills` (Multi-Skill Plugin Registry)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `slug` | `text` | NOT NULL, UNIQUE | `grants`, `competitor_tracking`, `investor_matching`, `regulatory_planning`, `team_hiring`, `lab_access`, `legal_ip` |
| `name` | `text` | NOT NULL | Display name |
| `description` | `text` | nullable | |
| `status` | `text` | NOT NULL, default 'draft' | `draft`, `beta`, `live`, `deprecated` |
| `required_profile_fields` | `text[]` | default '{}' | Fields this skill needs from profile |
| `config_json` | `jsonb` | default '{}' | Skill-specific runtime config |
| `created_at` | `timestamptz` | default now() | |
| `updated_at` | `timestamptz` | default now() | |
| `deleted_at` | `timestamptz` | nullable | |

**Indexes:**
- `skills_slug_idx` UNIQUE ON `slug`
- `skills_status_idx` ON `status`

---

#### `user_skills` (User's enabled skills)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `user_id` | `uuid` | FK -> users.id, NOT NULL | |
| `skill_id` | `uuid` | FK -> skills.id, NOT NULL | |
| `enabled_at` | `timestamptz` | default now() | |
| `created_at` | `timestamptz` | default now() | |
| `deleted_at` | `timestamptz` | nullable | |

**Constraints:**
- UNIQUE(`user_id`, `skill_id`) WHERE `deleted_at IS NULL`

---

#### `conversations`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `user_id` | `uuid` | FK -> users.id, nullable | null for anonymous sessions |
| `anonymous_session_id` | `uuid` | FK -> anonymous_sessions.id, nullable | |
| `active_skill_id` | `uuid` | FK -> skills.id, nullable | Currently active skill context |
| `status` | `text` | NOT NULL, default 'active' | `active`, `closed`, `transferred` |
| `turn_count` | `int` | default 0 | Incremented per user message |
| `first_value_at` | `timestamptz` | nullable | When first grant was recommended |
| `created_at` | `timestamptz` | default now() | |
| `updated_at` | `timestamptz` | default now() | |
| `deleted_at` | `timestamptz` | nullable | |

**Constraints:**
- Exactly one of `user_id` or `anonymous_session_id` must be non-null.

**Indexes:**
- `conversations_user_id_created_idx` ON `user_id, created_at DESC`
- `conversations_anon_session_idx` ON `anonymous_session_id`

---

#### `messages`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `conversation_id` | `uuid` | FK -> conversations.id, NOT NULL | |
| `role` | `text` | NOT NULL | `user`, `assistant`, `system`, `tool` |
| `content` | `text` | NOT NULL | Plain text or structured JSON string |
| `intent` | `text` | nullable | `greet`, `discover`, `match_request`, `deep_dive`, `grant_question`, `dismiss`, `edge_case`, `vague`, `unknown`, `skill_switch`, `profile_update`, `lifecycle_action` |
| `tokens_used` | `int` | nullable | LLM token count |
| `latency_ms` | `int` | nullable | Time from request to first token |
| `idempotency_key` | `text` | nullable | For retry deduplication |
| `created_at` | `timestamptz` | default now() | |
| `deleted_at` | `timestamptz` | nullable | |

**Indexes:**
- `messages_conversation_created_idx` ON `conversation_id, created_at DESC`
- `messages_intent_idx` ON `intent`
- `messages_idempotency_idx` UNIQUE ON `idempotency_key` WHERE `idempotency_key IS NOT NULL`

---

#### `grants`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `source` | `text` | NOT NULL | `nih_sbir`, `nsf_sbir`, `grants_gov`, `state_ca`, `private_foundation`, etc. |
| `source_id` | `text` | nullable | External identifier |
| `name` | `text` | NOT NULL | |
| `description` | `text` | nullable | |
| `amount_min_usd` | `bigint` | nullable | |
| `amount_max_usd` | `bigint` | nullable | |
| `deadline` | `date` | nullable | Application deadline |
| `status` | `text` | NOT NULL, default 'open' | `open`, `closed`, `rolling`, `upcoming` |
| `eligibility_rules` | `jsonb` | NOT NULL, default '{}' | Hard constraints |
| `tags` | `text[]` | default '{}' | e.g. `{'medical-device', 'ai', 'phase-1'}` |
| **source_url (MANDATORY)** | | | |
| `source_url` | `text` | **NOT NULL** | Official program URL. No URL = no grant. |
| `url_last_verified` | `timestamptz` | nullable | Last HEAD check timestamp |
| `url_is_live` | `boolean` | NOT NULL, default true | False = suppressed from matches |
| `url_status_code` | `int` | nullable | HTTP status from last check |
| `metadata_json` | `jsonb` | default '{}' | Source-specific fields |
| `last_synced_at` | `timestamptz` | nullable | |
| `created_at` | `timestamptz` | default now() | |
| `updated_at` | `timestamptz` | default now() | |
| `deleted_at` | `timestamptz` | nullable | |

**Indexes:**
- `grants_source_source_id_idx` UNIQUE ON `source, source_id` WHERE `source_id IS NOT NULL`
- `grants_deadline_idx` ON `deadline`
- `grants_status_idx` ON `status`
- `grants_url_live_idx` ON `url_is_live` WHERE `url_is_live = true`
- `grants_eligibility_gin_idx` GIN ON `eligibility_rules`
- `grants_tags_gin_idx` GIN ON `tags`
- `grants_name_trgm_idx` GIN ON `name` USING `gin_trgm_ops` (requires `pg_trgm` extension)

---

#### `grant_lifecycle` (14-State State Machine)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `user_id` | `uuid` | FK -> users.id, NOT NULL | |
| `grant_id` | `uuid` | FK -> grants.id, NOT NULL | |
| `status` | `text` | NOT NULL | **14 states** (see below) |
| `previous_status` | `text` | nullable | For transition tracking |
| `attempt_number` | `int` | NOT NULL, default 1 | For reapplications |
| `saved_at` | `timestamptz` | nullable | |
| `interested_at` | `timestamptz` | nullable | |
| `started_at` | `timestamptz` | nullable | |
| `applied_at` | `timestamptz` | nullable | |
| `submitted_at` | `timestamptz` | nullable | |
| `under_review_at` | `timestamptz` | nullable | |
| `accepted_at` | `timestamptz` | nullable | |
| `awarded_at` | `timestamptz` | nullable | |
| `rejected_at` | `timestamptz` | nullable | |
| `reconsidering_at` | `timestamptz` | nullable | |
| `dismissed_at` | `timestamptz` | nullable | |
| `abandoned_at` | `timestamptz` | nullable | |
| `archived_at` | `timestamptz` | nullable | |
| `expected_decision_date` | `date` | nullable | Computed from grant metadata |
| `award_amount_usd` | `bigint` | nullable | |
| `award_terms` | `text` | nullable | |
| `rejection_reason` | `text` | nullable | |
| `feedback_notes` | `text` | nullable | |
| `dismissal_reason` | `text` | nullable | `not_enough_money`, `wrong_category`, `deadline_too_soon`, `already_applied`, `unspecified` |
| `notes` | `text` | nullable | User notes |
| `created_at` | `timestamptz` | default now() | |
| `updated_at` | `timestamptz` | default now() | |
| `deleted_at` | `timestamptz` | nullable | |

**14 States:**
1. `discovered` — Auto (matching result)
2. `saved` — User action
3. `interested` — User said "tell me more"
4. `started` — User began prep
5. `applied` — User submitted application
6. `submitted` — Agent confirmed submission
7. `under_review` — Time-based (~30 days post submitted)
8. `accepted` — User notified of acceptance
9. `awarded` — Funds received
10. `rejected` — User received rejection
11. `reconsidering` — User wants to reapply
12. `dismissed` — User explicitly declined
13. `abandoned` — No activity 90+ days
14. `archived` — Lifecycle fully closed

**Constraints:**
- UNIQUE(`user_id`, `grant_id`, `attempt_number`) WHERE `deleted_at IS NULL`

**Indexes:**
- `lifecycle_user_grant_attempt_idx` UNIQUE partial (see constraint)
- `lifecycle_user_status_idx` ON `user_id, status`
- `lifecycle_grant_status_idx` ON `grant_id, status`
- `lifecycle_deadline_idx` ON `expected_decision_date`

---

#### `grant_lifecycle_transitions` (Audit log for every state change)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `lifecycle_id` | `uuid` | FK -> grant_lifecycle.id, NOT NULL | |
| `from_status` | `text` | NOT NULL | |
| `to_status` | `text` | NOT NULL | |
| `trigger_type` | `text` | NOT NULL | `user_action`, `agent_inference`, `time_based`, `auto` |
| `trigger_detail` | `text` | nullable | e.g. "User said 'I submitted it'" |
| `conversation_id` | `uuid` | FK -> conversations.id, nullable | Context |
| `created_at` | `timestamptz` | default now() | |

**Indexes:**
- `transitions_lifecycle_idx` ON `lifecycle_id, created_at DESC`

---

#### `grants_dismissed`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `user_id` | `uuid` | FK -> users.id, NOT NULL | |
| `grant_id` | `uuid` | FK -> grants.id, NOT NULL | |
| `reason` | `text` | nullable | `not_enough_money`, `wrong_category`, `deadline_too_soon`, `already_applied`, `unspecified` |
| `custom_reason` | `text` | nullable | |
| `conversation_id` | `uuid` | FK -> conversations.id, nullable | Context |
| `created_at` | `timestamptz` | default now() | |
| `deleted_at` | `timestamptz` | nullable | |

**Constraints:**
- UNIQUE(`user_id`, `grant_id`) WHERE `deleted_at IS NULL`

**Indexes:**
- `dismissed_user_grant_idx` UNIQUE partial
- `dismissed_user_reason_idx` ON `user_id, reason`

---

#### `alerts`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `user_id` | `uuid` | FK -> users.id, NOT NULL | |
| `grant_id` | `uuid` | FK -> grants.id, nullable | null for generic re-engagement |
| `lifecycle_id` | `uuid` | FK -> grant_lifecycle.id, nullable | For lifecycle nudges |
| `alert_type` | `text` | NOT NULL | `new_grant_match`, `deadline_approaching`, `deadline_imminent`, `deadline_passed`, `review_halfway`, `decision_expected`, `decision_overdue`, `reconsideration_window`, `no_activity`, `grant_updated`, `profile_change_unlock`, `re_engagement` |
| `message_preview` | `text` | NOT NULL | Pre-generated message summary |
| `rich_payload` | `jsonb` | default '{}' | Full structured alert data |
| `status` | `text` | NOT NULL, default 'pending' | `pending`, `sent`, `dismissed`, `acted` |
| `dismissed_reason` | `text` | nullable | |
| `scheduled_at` | `timestamptz` | nullable | Future delivery |
| `sent_at` | `timestamptz` | nullable | |
| `created_at` | `timestamptz` | default now() | |
| `updated_at` | `timestamptz` | default now() | |
| `deleted_at` | `timestamptz` | nullable | |

**Indexes:**
- `alerts_user_status_idx` ON `user_id, status, created_at DESC`
- `alerts_scheduled_idx` ON `scheduled_at` WHERE `status = 'pending'`
- `alerts_type_idx` ON `alert_type`
- `alerts_lifecycle_idx` ON `lifecycle_id`

---

#### `alert_deliveries`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `alert_id` | `uuid` | FK -> alerts.id, NOT NULL | |
| `channel` | `text` | NOT NULL | `in_app`, `email`, `telegram` |
| `status` | `text` | NOT NULL, default 'queued' | `queued`, `sent`, `failed`, `bounced` |
| `external_id` | `text` | nullable | Resend message ID, etc. |
| `error_message` | `text` | nullable | |
| `idempotency_key` | `text` | NOT NULL | |
| `created_at` | `timestamptz` | default now() | |
| `updated_at` | `timestamptz` | default now() | |

**Indexes:**
- `deliveries_alert_channel_idx` ON `alert_id, channel`
- `deliveries_idempotency_idx` UNIQUE ON `idempotency_key`

---

#### `data_source_syncs`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `source` | `text` | NOT NULL | e.g. `nih_sbir` |
| `status` | `text` | NOT NULL | `running`, `success`, `failed`, `degraded` |
| `records_fetched` | `int` | default 0 | |
| `records_upserted` | `int` | default 0 | |
| `records_skipped_no_url` | `int` | default 0 | source_url was null → skipped |
| `error_message` | `text` | nullable | |
| `started_at` | `timestamptz` | NOT NULL | |
| `completed_at` | `timestamptz` | nullable | |
| `created_at` | `timestamptz` | default now() | |

**Indexes:**
- `syncs_source_started_idx` ON `source, started_at DESC`

---

#### `url_verification_logs`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `grant_id` | `uuid` | FK -> grants.id, NOT NULL | |
| `url` | `text` | NOT NULL | |
| `status_code` | `int` | nullable | |
| `is_live` | `boolean` | NOT NULL | |
| `checked_at` | `timestamptz` | NOT NULL | |
| `error_message` | `text` | nullable | |

**Indexes:**
- `url_logs_grant_idx` ON `grant_id, checked_at DESC`

---

#### `audit_logs`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `uuid` | PK | |
| `user_id` | `uuid` | FK -> users.id, nullable | |
| `table_name` | `text` | NOT NULL | `profiles`, `grant_lifecycle`, `grants_dismissed` |
| `record_id` | `uuid` | NOT NULL | PK of affected row |
| `action` | `text` | NOT NULL | `create`, `update`, `delete` |
| `old_values` | `jsonb` | nullable | Previous state |
| `new_values` | `jsonb` | nullable | New state |
| `ip_address` | `inet` | nullable | |
| `created_at` | `timestamptz` | default now() | |

**Indexes:**
- `audit_user_idx` ON `user_id, created_at DESC`
- `audit_table_record_idx` ON `table_name, record_id`

---

### 2.3 Data Retention

| Table | Retention | Action |
|-------|-----------|--------|
| `messages` | 2 years | Auto-archive to Supabase Storage after 2 years |
| `conversations` | 2 years | Soft delete; hard delete after 2 years |
| `anonymous_sessions` | 30 days after expiry | Hard delete |
| `audit_logs` | 1 year | Export to Storage, then hard delete |
| `alert_deliveries` | 90 days | Hard delete |
| `data_source_syncs` | 90 days | Hard delete |
| `url_verification_logs` | 90 days | Hard delete |
| `grant_lifecycle_transitions` | 2 years | Soft delete; hard delete after 2 years |

---

## 3. Auth System

### 3.1 Philosophy: Value-First, Delayed Auth

Trestle does **not** block the chat with a signup wall. The user gets value (first grant match) before we ask for an email. Auth exists to make the agent *better* — not to gatekeep.

### 3.2 Anonymous First Session

**What Persists (Anonymous)**

| Layer | Data | TTL / Scope |
|-------|------|-------------|
| Server | `anon_session_id` (signed cookie, UUIDv4) | 30 days, HttpOnly, Secure, SameSite=Lax |
| Server | Conversation transcript (linked to `anon_session_id`) | 30 days |
| Server | Extracted profile fragments (industry, stage, location, etc.) | 30 days |
| Client | `trestle_profile` (localStorage, same fields) | Until browser cache cleared |
| Client | Dismissed grants list (localStorage) | Until browser cache cleared |
| Client | Tracked grants list (localStorage) | Until browser cache cleared |

**Agent Behavior During Anonymous Session**
- Agent introduces itself normally. No mention of accounts until value delivered.
- After first match is shown, agent says:
  > "Want me to remember this and alert you when deadlines approach? Create a free account — takes 10 seconds."
- If user continues without signup, agent continues. No nagging. Ask again at 3rd session or 7 days.

### 3.3 Signup Triggers

**Primary Trigger: Post-First-Match**
- After agent displays first grant match AND user interacts with it (clicks "Tell me more", "Track this", or types a follow-up question).

**Secondary Triggers**

| Trigger | Condition | Agent Script |
|---------|-----------|--------------|
| "Save this" intent | User says "save this grant" or clicks bookmark icon | "I'll save it here for now, but if you leave and come back, I won't remember. Want to create an account so I don't forget?" |
| Session #3 | Anonymous user returns for 3rd distinct session | "You're back — nice. I've helped you find {n} grants so far. Create an account and I can keep track across devices." |
| Proactive alert mention | User asks "can you remind me?" | "I can, but I need an email to send reminders to. Sign up — it's free." |
| "Will you remember this?" | User explicitly asks | "If you create an account, yes. Otherwise, I can only remember this session." |

**Anti-Patterns (We Do NOT Do These)**
- [ ] Popup modal on landing
- [ ] "Sign up to chat" before first message
- [ ] Nagging every message after first match
- [ ] Requiring signup to see grant details

### 3.4 Signup Methods

**Supported Methods (v1)**

| Method | Effort | Trade-off | Recovery Path |
|--------|--------|-----------|---------------|
| **Google OAuth** | 1-click | Fastest, no password fatigue | Google account recovery |
| **Magic Link (email)** | 2 clicks (enter email → click link) | No password to forget | Resend link |
| **Email + Password** | Email + password + confirm | Full control, works for non-Google users | Password reset email |

**Recommended Default: Magic link.** No password to forget. One less field. One less decision.

Google OAuth is presented as the prominent alternative. Email+password is available as "More options".

### 3.5 Signup Flow (Magic Link — Default)

```
[User clicks "Create account" in chat]
       |
       v
[Inline email input in chat widget] ----(type email, submit)---->
       |
       v
[Backend sends magic link email via Resend]
[Agent says: "Check your email — I sent you a link. Click it and you're in."]
       |
       v
[User clicks link /user-auth/verify?token=xyz]
       |
       v
[Backend validates token, creates user row, issues Clerk JWT]
[Redirects back to chat with ?auth=success]
       |
       v
[Frontend detects ?auth=success, refreshes token, calls POST /api/v1/auth/merge-session]
       |
       v
[Agent: "You're all set. I moved everything from this conversation over to your account."]
```

### 3.6 Signup Flow (Google OAuth)

```
[User clicks "Continue with Google" in chat widget]
       |
       v
[Clerk popup → Google OAuth consent]
       |
       v
[Callback to /user-auth/callback?clerk_token=...]
[Backend creates/updates user, issues JWT]
       |
       v
[POST /api/v1/auth/merge-session with anon_session_id cookie]
       |
       v
[Agent: "Welcome, {first_name}. I saved your conversation."]
```

### 3.7 Signup Flow (Email + Password)

```
[User expands "More options" → Email + Password]
       |
       v
[Inline form: email, password, confirm password]
       |
       v
[Backend: validate email uniqueness, hash password (Argon2id), create user]
       |
       v
[Send verification email via Resend]
[Agent: "Account created. Check your email to verify — until then, you can keep chatting, but I can't send alerts."]
       |
       v
[User verifies email → POST /api/v1/auth/verify-email]
[Backend: mark email_verified = true, enable alerts]
```

### 3.8 Return User Experience

**Detection (6-layer fallback chain):**
1. Valid JWT in `Authorization` header
2. Clerk session cookie (auto-refresh if expired)
3. `trestle_user_id` in localStorage → validate against server
4. Device fingerprint + `anon_session_id` cookie → anonymous return
5. Telegram `user_id` (if bot channel)
6. Fresh anonymous session (no history)

**Welcome Back Scripts**

If new grants matching their profile were added since last visit:
> "Welcome back, {first_name}. {n} new grants match your profile since {last_visit_date}. Want to see them?"

If no new grants, but tracked grant deadline is approaching:
> "Welcome back, {first_name}. Reminder: your {grant_name} application is due in {n} days. Need anything?"

If no new grants, no approaching deadlines:
> "Welcome back, {first_name}. Anything new with the company? I can re-run your matches if something changed."

### 3.9 Session Merge: Anonymous → Authenticated

**Critical Rule:** When a user signs up, **all anonymous session data must migrate** to their authenticated account. No data loss.

**Data to Merge**

| Source (anon_session_id) | Target (user_id) | Conflict Resolution |
|--------------------------|------------------|---------------------|
| Conversation transcripts | Append to user's conversation history | Chronological merge |
| Extracted profile | Merge into user profile | Most recent wins per field; if auth profile has field, keep it; if empty, use anon |
| Dismissed grants | Merge into user's dismissed_grants | Deduplicate on grant_id |
| Tracked grants | Merge into user's grant_lifecycle | Deduplicate on grant_id + attempt_number; if conflict on status, most recent wins |
| localStorage `trestle_profile` | Sync to server profile; then clear localStorage | Server state is now source of truth |

**Merge API:**
```
POST /api/v1/auth/merge-session
Headers: Authorization: Bearer <new_clerk_jwt>
Body: { "anon_session_id": "anon_xxx" }
```

**Backend logic:**
1. Validate JWT → get user_id
2. Look up anon session by anon_session_id
3. If found and not older than 30 days:
   - Merge conversation history (append)
   - Merge profile (field-by-field, auth wins conflicts)
   - Merge dismissed/tracked grants (deduplicate)
   - Delete anon session row OR mark as merged (soft delete for audit)
4. Return: `{ "merged": true, "conversations_migrated": n, "grants_migrated": m }`
5. Invalidate anon_session_id cookie (set expired)

### 3.10 Token Expiry (Session Duration)

| Token Type | TTL | Refresh Behavior |
|------------|-----|------------------|
| Clerk JWT (auth) | 7 days | Auto-refreshed by Clerk SDK if user is active; silent refresh via Clerk's `useAuth` hook |
| Anon session cookie | 30 days | Extended on each API call; expires after 30 days idle |
| Magic link token | 15 minutes | Single-use; user must request new link if expired |
| Password reset token | 1 hour | Single-use |
| Email verification token | 24 hours | Single-use; resend available after 60s cooldown |

### 3.11 Sad Paths (Auth)

**Email Never Verified**
- User CAN: chat, view matches, track grants (stored in DB, but no email alerts)
- User CANNOT: receive email alerts, proactive emails, reset password
- Agent script: "I can track it, but I can't email you reminders until you verify your email."
- Re-verification: button in settings, max 1 resend per 60s, max 5 per day

**Duplicate Email Signup**
- "Looks like you already have an account with that email. Want to log in instead?"
- Show login form with email pre-filled
- Security: Do NOT say "email exists" vs "email doesn't exist" in forgot-password flow. Always say "If an account exists, we sent a reset link."

**Google OAuth Down**
- Frontend detects popup failure after 30s
- Show: "Google login isn't working right now. Try email instead — it'll work the same."
- Log to Sentry

**Cookies Cleared Mid-Conversation**
- Frontend detects mismatch: localStorage profile exists, server says no session
- Agent: "Looks like your session expired. I still have your info here (shows summary). Want me to restore it, or start fresh?"
- If "restore": Frontend sends localStorage profile as initial context; server creates new anon session
- If "start fresh": Clear localStorage, start Flow 1 from scratch

**Magic Link Expired**
- Backend validates token → expired
- Redirect to `/login?expired=true`
- Show: "That link expired. Want me to send a new one?"

**Rate Limited During Signup**

| Endpoint | Limit | Window |
|----------|-------|--------|
| POST /auth/signup | 5 | per IP per hour |
| POST /auth/login | 10 | per IP per hour |
| POST /auth/forgot-password | 3 | per email per hour |
| POST /auth/magic-link | 3 | per email per hour |

- Return 429 with `Retry-After: <seconds>` header
- Frontend: "Too many attempts. Try again in {n} minutes."

---

## 4. Conversation Orchestrator (Stateful Dialogue Management)

The Conversation Orchestrator is **not a simple chatbot**. It is a stateful dialogue management system with:
- Adaptive questioning (Question Engine)
- Multi-skill context switching
- Profile completeness tracking
- Signup trigger detection
- Grant lifecycle state awareness

### 4.1 Question Engine

**Goal:** Extract founder profile NATURALLY through back-and-forth. No form. No interrogation. Ask 1-2 questions at a time, follow the user's lead.

**Rules:**
- Never ask more than 2 questions in a row.
- Infer when possible. If they say "pre-seed," infer stage and team size.
- Allow skipping. "If you don't want to share revenue numbers, that's fine — I can still give you a direction."
- Track completeness score (0-1). When >0.7, agent can offer matching.

**Fields to Extract (from PRD):**

| Field | Why It Matters | How the Agent Learns It |
|-------|---------------|------------------------|
| Company stage | Determines SBIR/STTR phase eligibility | "How far along are you?" |
| Industry | Many grants are industry-specific | "What space are you in?" / inferred from description |
| Location | State/local grants vary wildly | "Where are you based?" |
| Funding raised | Some grants require <$X raised | "Are you bootstrapped or have you raised?" |
| Team size | SBIR caps at 500 employees | "How many people on the team?" |
| Years in business | Some grants need <3 years, others >2 | "How long have you been at this?" |
| Previous grants applied | Avoid duplicates, know what's in flight | "Have you applied to anything before?" |
| Monthly burn | Runway calculation | "What's your current burn?" |
| Regulatory stage | Determines grant pool | "Do you have FDA clearance yet?" |

### 4.2 Agent State Machine (Conversation)

```
[User Input]
    |
    v
[Intent Classifier] → intent + confidence
    |
    v
[Question Engine] (if intent = discover AND profile.completeness < 0.7)
    → decide next question(s)
    → update completeness score
    |
    v
[Skill Router] → load active skill context into prompt
    |
    v
[Context Builder] → assemble full prompt
    |
    v
[LLM Completion] → streaming response
    |
    v
[Output Guardrails]
    → source_url check: every grant MUST have source_url
    → lifecycle detector: did user imply a state change?
    → signup trigger detector: should we prompt for auth?
    |
    v
[Session Writer] → async DB writes
    |
    v
[Stream to Client]
```

### 4.3 Sample Dialogue Flow (Discovery)

```
Agent:  What does your company do?
User:   We're automating medical billing with AI
Agent:  Got it — so healthcare tech. How far along are you?
        Still building, have customers, or scaling?
User:   We have 8 hospital customers, about $200K ARR
Agent:  Nice traction. Are you bootstrapped, or have you raised?
User:   We raised a $500K pre-seed
Agent:  Okay, that rules out a few grants that require <$100K raised,
        but opens up others. Where are you incorporated?
User:   Delaware, but ops are in Austin
Agent:  Texas has some solid state-level programs.
        Let me check what matches your profile.
        [completeness_score now 0.75 → trigger matching]
```

### 4.4 Lifecycle State Detection

The orchestrator monitors conversation text for implicit lifecycle transitions:
- "I submitted it" → APPLIED
- "I got accepted" → ACCEPTED
- "They rejected us" → REJECTED
- "I started working on it" → STARTED
- "I'm done with this one" → DISMISSED

These are confirmed with the user before writing to DB:
- "Just to confirm — you submitted the NIH SBIR application?"
- If user confirms → write `grant_lifecycle` transition

---

## 5. Landing Page Specification

### 5.1 Page Structure

**URL:** `/` (Next.js App Router, SSR)

| Section | Purpose | Hero Content |
|---------|---------|--------------|
| **Navbar** | Brand + nav + auth | Logo "Trestle". Links: Features, How It Works, Pricing (anchor). CTA: "Talk to Trestle". Clerk UserButton if signed in. |
| **Hero** | Hook in 5 seconds | Headline: "Your personal assistant for finding grants, tracking deadlines, and planning your startup's next move." Sub: "Trestle learns your company, asks smart follow-ups, and alerts you when new funding opens. No 80-question forms." Primary CTA: "Start Talking" (opens chat widget). Secondary: "See how it works". |
| **Social Proof** | Trust | 3 founder quotes (anonymized/simulated for MVP). |
| **Features** (3 cards) | Value | 1. Conversational Discovery (not a form). 2. Deep Eligibility Matching (not keyword search). 3. Proactive Alerts + Lifecycle Tracking (not weekly digests). |
| **How It Works** (4 steps) | Clarity | 1. Tell Trestle about your company. 2. It asks 1-2 smart follow-ups. 3. Get 3-5 matched grants with deadlines and source URLs. 4. Get pinged when deadlines approach and track your applications. |
| **Trust Signals** | Medtech credibility | Badges: "No PHI stored", "Grants.gov partner data", "Built for 510(k) to PMA". Mini-FAQ. |
| **Final CTA** | Conversion | "Stop scrolling grant databases. Start a conversation." Button: "Talk to Trestle" (sticky). |
| **Footer** | Legal + links | Copyright, Privacy Policy, Terms, Contact, LinkedIn. |

### 5.2 Component Spec

**Chat Widget (Global Floating):**
- Position: bottom-right, fixed.
- Trigger: circular "T" button (pulse animation on first visit).
- Open state: 400x600px modal, border-radius 16px, shadow-2xl.
- Header: "Trestle" + close + minimize.
- Body: virtualized message list (first 50 messages, auto-scroll).
- Input: single-line textarea (max 1000 chars), submit on Enter (Shift+Enter for newline).
- SSE connection to `/api/v1/chat/stream/{job_id}`.
- Loading state: streaming dots + first token indicator.
- Auth gate: if anonymous, show "Sign in to save your progress" inline (non-blocking).

**Responsive:**
- Mobile: widget goes full-screen overlay on open.
- Tablet: same as desktop but 350px wide.

---

## 6. API Design Principles

1. **REST + SSE hybrid.** Chat streams via SSE. Everything else REST JSON.
2. **Pydantic models** are the single source of truth. FastAPI auto-generates OpenAPI from them.
3. **Idempotency:** All mutating endpoints accept `Idempotency-Key: <uuid>` header. 409 if duplicate.
4. **Pagination:** All list endpoints use cursor-based pagination (`?cursor=<uuid>&limit=20`). Offset banned.
5. **Error envelope:**
   ```json
   {
     "error": {
       "code": "GRANT_NOT_FOUND",
       "message": "Grant not found",
       "detail": { "grant_id": "..." }
     }
   }
   ```
6. **Rate limits:** 60 req/min per IP, 20 chat messages/min per user. 429 with `Retry-After`.

---

## 7. Decision Log -- LLD ADRs

### ADR-006: Docker Compose for Local + Single-Node Production
**Decision:** Use `docker-compose.yml` for local dev and initial production. No Kubernetes.
**Rationale:** Two engineers, monolith, <1K DAU at launch. Compose gives parity between local and prod without k8s complexity.
**Status:** Accepted.

### ADR-007: SQLAlchemy 2.0 + Alembic as ORM/Migration Layer
**Decision:** SQLAlchemy 2.0 with async session + Alembic for migrations.
**Rationale:** Team knows SQLAlchemy. Type-annotated models reduce bugs. Alembic is the standard.
**Status:** Accepted.

### ADR-008: Pydantic v2 for API, Validation, and LLM Structured Output
**Decision:** Pydantic v2 is the single model library for FastAPI request/response schemas, LLM structured output, and DB DTOs.
**Rationale:** One model language across the stack. FastAPI native. `model_dump_json()` for LLM tool calling.
**Status:** Accepted.

### ADR-009: Grant Eligibility Rules Stored as JSONB with GIN Index
**Decision:** Store `eligibility_rules` as JSONB in `grants` table, indexed with GIN.
**Rationale:** Grant rules evolve frequently and vary wildly across sources. JSONB with `@>` containment queries + GIN index gives flexibility with queryable performance.
**Status:** Accepted. Revisit if JSONB query performance degrades.

### ADR-010: Match Results Cached by Profile Hash in Redis
**Decision:** Cache eligibility match results in Redis keyed by `SHA256(profile_snapshot)` with 1-hour TTL.
**Rationale:** Matching is expensive. Many users have similar profiles. Hash-based cache avoids redundant compute.
**Status:** Accepted. TTL tunable based on hit rate.

### ADR-011: source_url as Non-Nullable with Weekly Verification
**Decision:** `grants.source_url` is NOT NULL. Weekly HEAD check job flags broken URLs.
**Rationale:** Trust is the product. A grant without a verifiable source URL is indistinguishable from hallucination. `url_is_live` lets us suppress broken links without deleting data.
**Status:** Accepted.

### ADR-012: 14-State Grant Lifecycle with Transition Audit Table
**Decision:** `grant_lifecycle` table tracks 14 states. `grant_lifecycle_transitions` audits every change.
**Rationale:** The match is the hook, the lifecycle is the product. Full state tracking enables proactive nudges, conversion analytics, and matching algorithm feedback. Audit table enables debugging and compliance.
**Status:** Accepted.

### ADR-013: General-Purpose Founder Profile (Not Grant-Specific)
**Decision:** `profiles` table stores general founder data (company, product, financials, preferences). All skills share it.
**Rationale:** Future skills (investor matching, competitor tracking) read the same profile. No re-onboarding. No schema rewrite per skill.
**Status:** Accepted.

### ADR-014: Skill Plugin Registry
**Decision:** `skills` table + `user_skills` junction enables runtime skill registration.
**Rationale:** Hard-coding skill logic in the orchestrator creates technical debt. A registry lets new skills be added with DB rows + config, not code deploys.
**Status:** Accepted. v1 ships with `grants` skill only.

### ADR-015: Delayed Auth with Session Merge
**Decision:** Anonymous sessions (30-day cookie) with signup triggers at value moments. Full data merge on auth.
**Rationale:** Auth before value = dead. Session merge ensures users don't "start over" when they sign up. This is critical for the ≥20% signup conversion target.
**Status:** Accepted.

---

*LLD by Aurthur | Next: Floyd (frontend) + Jason (backend) review API contract. Then Arceus gate.*
