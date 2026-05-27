# Trestle Product Backlog — GitHub Issue Map

**Owner:** Sam (Product)  
**Status:** Draft — Pending Arceus approval  
**Date:** May 22, 2026  
**Derived from:** PRD t_7b4805cd, Roadmap t_06a17759, User Flow t_5057144a  
**Milestones:** V0 Demo (Jun 12) → V1 Beta (Jul 24) → V2 Scale (Sep 18)

---

## Legend

| Field | Meaning |
|-------|---------|
| **Priority** | P0 (MVP/demo blocker), P1 (Beta blocker), P2 (Post-beta / nice-to-have) |
| **Estimate** | S (1–3 days), M (1–2 weeks), L (3–6 weeks) |
| **Labels** | Area tags for routing (e.g., `frontend`, `backend`, `agent`) |
| **Depends on** | Other issue IDs that must close first |
| **Milestone** | V0 / V1 / V2 target |

---

## 1. Landing Page + Auth

> PRD §4 Solution / Roadmap V0 §Landing page + auth

| # | Title | Description | Priority | Estimate | Labels | Depends on | Milestone |
|---|-------|-------------|----------|----------|--------|-----------|-------------|
| 1.1 | Landing page with chat CTA | Single-page landing with "Talk to Trestle" CTA, one-liner value prop, trust signals. No pricing, no blog. Plain HTML/Tailwind. **Goal: zero-friction entry.** | P0 | S | `frontend`, `ui`, `v0` | — | V0 |
| 1.2 | Google OAuth login | OAuth 2.0 via Google. Users can optionally auth after first message. **Goal: no sign-up wall before first chat.** | P0 | S | `backend`, `auth`, `api`, `v0` | — | V0 |
| 1.3 | Email/password auth fallback | Magic-link or password login for users without Google workspace. | P1 | S | `backend`, `auth`, `api`, `v1` | 1.2 | V1 |
| 1.4 | Post-auth account profile page | Minimal "Your Profile" screen showing extracted company data from chat sessions. | P1 | M | `frontend`, `ui`, `v1` | 1.2 | V1 |
| 1.5 | Passwordless / email-link onboarding | Explore magic-link-only auth to reduce friction further. | P2 | S | `backend`, `auth`, `v2` | — | V2 |
| 1.6 | Accelerator self-serve signup portal | White-label onboarding for Maurinne-class gatekeepers to spin up a branded Trestle instance for their cohort. **Scope guard: NOT a full multi-tenant SaaS rebuild.** | P2 | L | `frontend`, `backend`, `auth`, `v2` | 1.4 | V2 |
| 1.7 | Terms of service + privacy policy pages | Required before any data collection. Covers: no PHI, stage/company metadata only. | P0 | S | `frontend`, `ui`, `v0` | — | V0 |

---

## 2. Conversational Agent Interface

> PRD §4 Solution / User Flow all 6 Flows

| # | Title | Description | Priority | Estimate | Labels | Depends on | Milestone |
|---|-------|-------------|----------|----------|--------|-----------|-------------|
| 2.1 | Chat widget UI (web) | Persistent bottom-right chat widget. Message bubbles, typing indicator, scroll history. Plain React + Tailwind. **Not a dashboard.** | P0 | S | `frontend`, `ui`, `v0` | 1.1 | V0 |
| 2.2 | Agent message rendering | Bold headings, numbered lists, links. Support for grant cards (title, deadline, amount, confidence, buttons). | P0 | S | `frontend`, `ui`, `v0` | 2.1 | V0 |
| 2.3 | "Track this grant" button | One-click add-to-watchlist per grant card. Persists to session memory. | P0 | S | `frontend`, `backend`, `v0` | 2.2 | V0 |
| 2.4 | Grant card component | Reusable card: title, agency, deadline, ~amount, confidence badge, 2 CTAs ("Track", "Tell me more"). Max 5 per response. | P0 | S | `frontend`, `ui`, `v0` | 2.2 | V0 |
| 2.5 | Deep-dive grant detail view | Expandable/scrollable view for Flow 5: eligibility checklist, deadlines, budget tips, red flags, official links, next-step CTAs. | P1 | M | `frontend`, `ui`, `v1` | 2.4 | V1 |
| 2.6 | Alert/notification toast UI | In-app toast + email template for proactive alerts (Flow 4). Weekly digest as default. | P1 | M | `frontend`, `ui`, `v1` | 2.1 | V1 |
| 2.7 | Slack bridge (read-only + alerts first) | Post proactive alerts to a configured Slack channel. Full conversational parity only if demand proves. | P2 | M | `backend`, `integration`, `v2` | 2.6 | V2 |
| 2.8 | Telegram bridge | Bot that mirrors alert flow and optionally responds to basic queries. | P2 | M | `backend`, `integration`, `v2` | 2.6 | V2 |
| 2.9 | Voice / audio input | Allow founders to dictate responses (mobile-friendly). | P2 | L | `frontend`, `agent`, `v2` | 2.1 | V2 |

---

## 3. Eligibility Matching Engine

> PRD §4 Solution / Roadmap V1 §Full eligibility engine

| # | Title | Description | Priority | Estimate | Labels | Depends on | Milestone |
|---|-------|-------------|----------|----------|--------|-----------|-------------|
| 3.1 | LLM prompt chain for Flows 1–3 | Prompt engineering for First Contact, Discovery Dialogue, Eligibility Matching. OpenAI/Anthropic API. No fine-tuning in MVP. **Goal: ≤12 avg turns to full profile.** | P0 | M | `agent`, `api`, `v0` | — | V0 |
| 3.2 | Hard reject eligibility filter | Rules engine that hard-rejects grants on disqualifying criteria (location, company stage, already-raised cap, team size >500). | P1 | M | `backend`, `agent`, `v1` | 3.1, 3.5 | V1 |
| 3.3 | Soft flag + confidence scoring | Partial match detection: flags grants that COULD apply with reframing or minor changes. Labels confidence (strong / partial / informational). | P1 | M | `backend`, `agent`, `v1` | 3.2 | V1 |
| 3.4 | Medtech-native question variants | Vertical-specific prompts (Q-Sub, predicate device, IDE, clinical endpoints, 510(k) vs PMA vs De Novo). | P0 | S | `agent`, `v0` | 3.1 | V0 |
| 3.5 | Founder profile schema + extraction | JSON schema for user profile (company, stage, industry, location, funding, team size, regulatory status). Extracted via conversation, not form. | P0 | M | `backend`, `api`, `v0` | — | V0 |
| 3.6 | Profile update/reevaluation logic | When user signals a change ("we just hit 500 employees"), agent re-runs matching and explains what opened/closed. | P1 | M | `backend`, `agent`, `v1` | 3.2 | V1 |
| 3.7 | Multi-industry prompt variants | Vertical-specific prompts for SaaS, climate, fintech, hardware. **Scope guard: one new vertical per month max.** | P2 | L | `agent`, `v2` | 3.4 | V2 |
| 3.8 | Investor matching engine (Grant→Venture bridge) | Match post-grant founders to patient-capital funds / VCs. Warm-intro only. Data from public sources. | P2 | L | `backend`, `agent`, `v2` | 3.6 | V2 |

---

## 4. Grant Data Pipeline

> PRD §4 Solution / Roadmap V0 §Seeded grant database / V1 §Live data ingest

| # | Title | Description | Priority | Estimate | Labels | Depends on | Milestone |
|---|-------|-------------|----------|----------|--------|-----------|-------------|
| 4.1 | Seeded grant database (50–75 grants) | Manual curation of NIH SBIR Phase I/II, NSF SBIR, 3–5 state programs, 2–3 private foundations. Stored as JSON/CSV. **Quality > quantity.** | P0 | S | `data`, `backend`, `v0` | — | V0 |
| 4.2 | Grant schema definition | Standardized fields: title, agency, amount, deadline, eligibility rules (hard/soft), industry tags, location restrictions, stage requirements, source URL. | P0 | S | `data`, `backend`, `v0` | — | V0 |
| 4.3 | NIH SBIR live data ingest (subset) | Automated pull from NIH SBIR API or Grants.gov bulk XML. Updates 2×/week. **Scope guard: NIH only, no other sources yet.** | P1 | M | `data`, `pipeline`, `backend`, `v1` | 4.2 | V1 |
| 4.4 | Data freshness monitoring | Track avg age of listed grants. Alert if >14 days. Built into analytics dashboard. | P1 | S | `data`, `backend`, `v1` | 4.3 | V1 |
| 4.5 | State-level grant ingest (first 10 states) | Manual curation of state-level programs. Prioritize by user request volume. **No scraping if API exists.** | P2 | L | `data`, `pipeline`, `v2` | 4.3 | V2 |
| 4.6 | UK/EU grant ingest (Innovate UK, Horizon) | Requires API or scraper access. Low priority unless UK/EU founder demand proves. | P2 | L | `data`, `pipeline`, `v2` | 4.5 | V2 |
| 4.7 | Investor database for matching | Public data on medtech/healthcare VCs, patient-capital funds (SNIB, Redalpine). | P2 | M | `data`, `backend`, `v2` | 4.2 | V2 |
| 4.8 | Grant duplication detection | Avoid showing same grant from multiple sources. Match on agency + program + cycle. | P1 | S | `backend`, `data`, `v1` | 4.3 | V1 |

---

## 5. Alert / Notification System

> PRD §4 Solution / User Flow Flow 4 / Roadmap V1 §Proactive alerts

| # | Title | Description | Priority | Estimate | Labels | Depends on | Milestone |
|---|-------|-------------|----------|----------|--------|-----------|-------------|
| 5.1 | Proactive alert trigger logic | Detect: new grant matches user profile, deadline approaching (≤7 days), stage change detected in conversation, dismissed grant becomes newly eligible. | P1 | M | `backend`, `agent`, `v1` | 3.2, 3.5 | V1 |
| 5.2 | Weekly digest email | Default delivery: weekly summary of new matches + approaching deadlines. One-click to full chat. | P1 | M | `backend`, `frontend`, `v1` | 5.1 | V1 |
| 5.3 | Real-time alert opt-in | Users can opt into real-time notifications (in-app toast + email) for specific grant programs or deadlines. | P1 | S | `backend`, `frontend`, `v1` | 5.1 | V1 |
| 5.4 | Re-engagement nudge | "Still looking for grants?" after 30 days inactivity. | P1 | S | `backend`, `agent`, `v1` | 5.1 | V1 |
| 5.5 | Alert usefulness rating | In-app "was this useful?" vote on every alert. Feeds into North Star metric. | P1 | S | `frontend`, `backend`, `v1` | 5.2 | V1 |
| 5.6 | SMS alert delivery | Text notifications for deadline reminders. Requires phone number collection (opt-in). | P2 | S | `backend`, `v2` | 5.3 | V2 |
| 5.7 | Accelerator cohort alert routing | Gatekeepers like Maurinne can broadcast alerts to their entire cohort. | P2 | M | `backend`, `v2` | 5.2, 1.6 | V2 |

---

## 6. Session Memory + Persistence

> User Flow §Session Memory Schema / PRD §4 Solution

| # | Title | Description | Priority | Estimate | Labels | Depends on | Milestone |
|---|-------|-------------|----------|----------|--------|-----------|-------------|
| 6.1 | In-session memory (localStorage) | JSON blob storing company profile, grants applied/dismissed/tracking, conversation summary. Survives page refresh. | P0 | S | `frontend`, `v0` | — | V0 |
| 6.2 | Backend session persistence | Postgres table for user profile + session history. Enables cross-device continuity. | P1 | M | `backend`, `v1` | 6.1, 1.2 | V1 |
| 6.3 | Cross-session memory (Flow 6) | Agent greets returning users with context ("Last time you filed your Q-Sub..."). Dismissals feed back to prevent repeats. | P1 | M | `backend`, `agent`, `v1` | 6.2 | V1 |
| 6.4 | Dismissal feedback loop | When user dismisses a grant, capture reason. Update profile/recommendation model. | P1 | S | `backend`, `agent`, `v1` | 6.3 | V1 |
| 6.5 | Team-level shared memory | Multi-user company accounts see shared grant pipeline + dismissals. | P2 | M | `backend`, `v2` | 6.2 | V2 |
| 6.6 | Memory export / data portability | GDPR compliance + user trust: export all stored data as JSON. | P2 | S | `backend`, `v2` | 6.2 | V2 |

---

## 7. Infrastructure + DevOps

> Roadmap all milestones

| # | Title | Description | Priority | Estimate | Labels | Depends on | Milestone |
|---|-------|-------------|----------|----------|--------|-----------|-------------|
| 7.1 | Project scaffolding | FastAPI backend + Next.js frontend + Postgres + LLM API client. Docker Compose local. | P0 | S | `infra`, `v0` | — | V0 |
| 7.2 | Postgres schema (users, sessions, grants) | Core tables: users, sessions, grants, tracked_grants, dismissals. Lightweight. No over-engineering. | P0 | M | `backend`, `infra`, `v0` | 7.1 | V0 |
| 7.3 | LLM API integration (OpenAI/Anthropic) | Chat completions API with structured JSON output (for profile extraction + grant matching). | P0 | S | `backend`, `agent`, `api`, `v0` | 7.1 | V0 |
| 7.4 | CI/CD pipeline | GitHub Actions: lint, test, build, deploy to staging. | P0 | S | `infra`, `v0` | 7.1 | V0 |
| 7.5 | Staging environment | Heroku / Railway / Fly.io staging deploy. Auto-deploy on PR merge to `develop`. | P0 | S | `infra`, `v0` | 7.4 | V0 |
| 7.6 | Production environment | Same platform, production branch, env vars for LLM keys, DB credentials. | P0 | S | `infra`, `v0` | 7.5 | V0 |
| 7.7 | Background job scheduler (cron) | Celery/APScheduler for: data ingest 2×/week, alert digests, re-engagement nudges. | P1 | M | `infra`, `backend`, `v1` | 7.1 | V1 |
| 7.8 | Analytics event pipeline | PostHog or Segment integration. Track: relevance rate, turn count, time-to-value, alert votes, session frequency. | P1 | M | `infra`, `v1` | 7.5 | V1 |
| 7.9 | Error logging + monitoring | Sentry for exception tracking. PagerDuty/Opsgenie for on-call. | P1 | S | `infra`, `v1` | 7.6 | V1 |
| 7.10 | Multi-tenant schema (lightweight) | For accelerator self-serve: tenant_id on users, grants, sessions. NOT a full SaaS RBAC rebuild. | P2 | M | `backend`, `infra`, `v2` | 7.2 | V2 |
| 7.11 | Rate limiting + abuse prevention | Per-user and per-IP rate limits on LLM API calls. | P1 | S | `backend`, `infra`, `v1` | 7.3 | V1 |
| 7.12 | Secrets management | Vault / Doppler / 1Password Secrets for API keys, DB passwords. | P1 | S | `infra`, `v1` | 7.6 | V1 |

---

## 8. Testing + QA

> PRD §5 Success Criteria / Roadmap §Kill / Pivot Triggers

| # | Title | Description | Priority | Estimate | Labels | Depends on | Milestone |
|---|-------|-------------|----------|----------|--------|-----------|-------------|
| 8.1 | Unit tests for eligibility engine | Test hard reject, soft flag, confidence scoring with known-good and known-bad profiles. | P0 | M | `qa`, `backend`, `v0` | 3.1 | V0 |
| 8.2 | Chat flow integration tests | Simulate full sessions: landing → chat → profile extraction → grant match → track. Assert on turn count, time-to-value. | P0 | M | `qa`, `frontend`, `v0` | 2.1, 3.1 | V0 |
| 8.3 | LLM prompt evaluation harness | A/B test prompts against a fixed set of 20 founder scenarios. Measure extraction accuracy + grant relevance. | P0 | S | `qa`, `agent`, `v0` | 3.1 | V0 |
| 8.4 | End-to-end demo script | Automated Playwright/Cypress script that runs the exact demo path for Maurinne. Fails = demo blocked. | P0 | S | `qa`, `frontend`, `v0` | 2.1, 3.1 | V0 |
| 8.5 | Relevance acceptance tracking | Log every "thumbs down / not for me" on recommended grants. Dashboard: % dismissed by week. | P0 | S | `qa`, `backend`, `v1` | 7.8 | V1 |
| 8.6 | Alert usefulness tracking | Log vote on every alert. Target ≥60% "useful." Kill trigger if <50% for 2 weeks. | P1 | S | `qa`, `backend`, `v1` | 5.5 | V1 |
| 8.7 | Performance testing (LLM latency) | <2s average response time for chat messages. <5s for grant matching. | P1 | S | `qa`, `backend`, `v1` | 7.3 | V1 |
| 8.8 | Security scan | OWASP ZAP or similar on staging. No SQL injection, XSS, or auth bypass. | P1 | S | `qa`, `infra`, `v1` | 7.5 | V1 |
| 8.9 | Accessibility audit (WCAG 2.1 AA) | Chat widget and landing page pass a11y checks. | P1 | S | `qa`, `frontend`, `v1` | 1.1 | V1 |
| 8.10 | Load testing | 100 concurrent chat sessions without degradation. | P2 | S | `qa`, `infra`, `v2` | 7.6 | V2 |

---

## 9. Analytics + Dashboard (Internal)

> Roadmap V1 §Analytics dashboard

| # | Title | Description | Priority | Estimate | Labels | Depends on | Milestone |
|---|-------|-------------|----------|----------|--------|-----------|-------------|
| 9.1 | Relevance rate chart | % of presented grants accepted by users. Weekly trend. Kill line at 50%. | P1 | M | `frontend`, `backend`, `v1` | 8.5 | V1 |
| 9.2 | Turn count + time-to-value dashboard | Average conversational turns before full profile. Average seconds from landing to first grant rec. | P1 | S | `frontend`, `backend`, `v1` | 7.8 | V1 |
| 9.3 | Active sessions per user / month | DAU/MAU. Target ≥2 sessions/user/mo by end of V1. | P1 | S | `frontend`, `backend`, `v1` | 7.8 | V1 |
| 9.4 | Grant data freshness dashboard | Avg age of listed grants. Alert if >14 days. | P1 | S | `frontend`, `backend`, `v1` | 4.4 | V1 |
| 9.5 | Alert usefulness scoreboard | % "useful" votes per alert type. | P1 | S | `frontend`, `backend`, `v1` | 8.6 | V1 |
| 9.6 | Founder persona distribution | % Academic, Clinical, Grant-to-Venture. Helps prioritize feature verticals. | P2 | S | `frontend`, `backend`, `v2` | 7.8 | V2 |

---

## 10. Documentation + Operations

| # | Title | Description | Priority | Estimate | Labels | Depends on | Milestone |
|---|-------|-------------|----------|----------|--------|-----------|-------------|
| 10.1 | Runbook: demo day checklist | Step-by-step for Maurinne's live trial. Who does what, fallback plans, known issues. | P0 | S | `ops`, `v0` | — | V0 |
| 10.2 | API documentation | OpenAPI spec for backend endpoints. For frontend handoff + future integrations. | P1 | S | `docs`, `backend`, `v1` | 7.1 | V1 |
| 10.3 | Internal onboarding guide | How to add new grants to the seed DB, update prompts, interpret analytics. | P1 | S | `docs`, `ops`, `v1` | 4.1 | V1 |
| 10.4 | Privacy policy + data handling SOP | What data is stored, retention policy, how to handle user export/deletion requests. | P1 | S | `ops`, `v1` | 6.2 | V1 |

---

## Summary by Milestone

| Milestone | Target Date | Total Items | P0 | P1 | P2 |
|-----------|-------------|-------------|----|----|----|
| V0 Demo | Jun 12, 2026 | 14 | 14 | 0 | 0 |
| V1 Beta | Jul 24, 2026 | 28 | 0 | 23 | 5 |
| V2 Scale | Sep 18, 2026 | 29 | 0 | 0 | 29 |
| **Grand Total** | — | **71** | **14** | **23** | **34** |

---

## Immediate Next Steps

1. **Arceus approves this backlog.**
2. **Sam converts V0 P0 items to GitHub issues** with labels, assignees (Floyd, Jason, Aurthur), and `v0-demo` milestone.
3. **Feasibility debate:** Sam pings Aurthur, Floyd, Jason on the 14 V0 items. Any item they reject gets cut or descoped.
4. **No code until issue map is locked.** Every V0 item gets an issue number before a branch is created.

---

*Backlog by Sam | Derived from PRD t_7b4805cd, Roadmap t_06a17759, User Flow t_5057144a*
