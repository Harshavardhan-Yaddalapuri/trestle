# Trestle Matching MVP — High-Level Design (HLD)

**Version:** 1.0 (Tuesday Demo MVP)  
**Date:** 2026-05-22  
**Stage:** SDLC Stage 2 — System Design Complete  

---

## 1. Purpose & Scope

### 1.1 Purpose
Design the grant and investment opportunity matching module for the Trestle Tuesday-demo MVP.
The system connects founder profiles with relevant financial opportunities using a deterministic, rule-based eligibility engine.

### 1.2 In Scope (MVP)
- Profile intake (≤ 8 fields)
- Rule-based eligibility matching
- Grant and investment opportunity data store
- Match API (JSON REST)
- Notification proof-of-concept
- Simple web dashboard or CLI

### 1.3 Out of Scope (Post-MVP)
- Machine learning recommendation engine
- Real-time external API integrations (initially static CSV/JSON seed data)
- User authentication and authorization
- Payment processing

---

## 2. System Architecture

### 2.1 Component Diagram (ASCII)

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                           Trestle Matching MVP                             │
│                              (Tuesday Demo)                                │
├────────────────────────────────────────────────────────────────────────────┤
│  [Client Layer]         [Service Layer]            [Data Layer]            │
│  ┌──────────────┐      ┌──────────────┐       ┌──────────────────┐       │
│  │  Web         │      │  Match API   │       │ Profile DB        │       │
│  │  Dashboard   │──────│  (FastAPI)   │───────│  (PostgreSQL/     │       │
│  │  /CLI        │      │              │       │   SQLite)         │       │
│  └──────────────┘      └──────┬───────┘       └──────────────────┘       │
│                               │                                             │
│                         ┌─────┴──────┐      ┌──────────────┐              │
│                         │ Eligibility│      │ Grant/Inv.   │              │
│                         │ Engine     │──────│ Data Store   │              │
│                         │ (Rules)    │      │ (Seed JSON + │              │
│                         │            │      │  SQL tables) │              │
│                         └─────┬──────┘      └──────────────┘              │
│                               │                                             │
│                         ┌─────┴──────┐                                     │
│                         │ Notification│                                     │
│                         │ PoC (Email│                                     │
│                         │ /Log)      │                                     │
│                         └────────────┘                                     │
└────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Descriptions

| Component | Responsibility | MVP Notes |
|-----------|---------------|-----------|
| **Web Dashboard / CLI** | Intake profile, display matches | Single HTML page (vanilla JS) or Python CLI. No auth required. Streamlit acceptable for speed. |
| **Match API** | Receives `GET /matches`, orchestrates engine | Stateless FastAPI service. Calls Profile Service and Eligibility Engine. |
| **Profile Service** | CRUD for founder profiles | Simple table; `POST /profiles` for upsert. |
| **Eligibility Engine** | Apply deterministic rule set against profiles and opportunities | Pure Python functions. No ML. Returns ranked matches with rationale strings. |
| **Grant/Investment Data Store** | Static seed data: NIH, SBIR, Grants.gov + 2–3 medtech VC samples | JSON/CSV seeds loaded into SQL tables at startup. |
| **Notification PoC** | Sends match alert (email or log) | For demo, logs to console. Post-MVP: SendGrid/AWS SES. |

---

## 3. Data Flow

### 3.1 Happy Path: Match a Profile

```text
1. Founder inputs profile via Dashboard/CLI
        ↓
2. POST /profiles → Profile Service → DB (upsert)
        ↓
3. Founder clicks / enters "Find Opportunities"
        ↓
4. GET /matches?profile_id=123 → Match API
        ↓
5. Match API fetches profile + active opportunities
        ↓
6. Eligibility Engine evaluates all applicable rules
        ↓
7. Returns ≤5 ranked matches with rationale + freshness_timestamp
        ↓
8. Dashboard/CLI renders results to founder
        ↓
9. Notification PoC: logs alert to console (email draft in post-MVP)
```

### 3.2 Data Freshness Flow

All data stores include `updated_at` and `source_url`.
Every match response embeds `freshness_timestamp` (max of profile + opportunity + rule last-updated times).
Post-MVP: Nightly scheduled fetcher service to refresh external grant/VC data.

---

## 4. Failure Modes & Degradation Strategy

| Failure Scenario | System Impact | Degradation / Mitigation |
|-----------------|-------------|--------------------------|
| **Stale / No Fresh Data** | Matches may be outdated | Display `freshness_timestamp` on every match result. Allow explicit "refresh" action that re-runs rules. If data > 30 days old, show warning banner. |
| **Eligibility Engine Unavailable** | `GET /matches` returns 500 | Return cached last matches for profile with `degraded: true` flag and warning banner. Degrade to static list view (all active opportunities). |
| **Database Slow / Unreachable** | API latency > 2s or timeout | Serve from lightweight in-memory cache (JSON fallback). Show "try again later" with static seed data. |
| **Notification PoC Fails** | No email/log sent | Gracefully skip (no exception). Log failure. Never block match API response. |
| **Profile Missing Required Fields** | Cannot run eligibility | API returns `400` with exact validation error. Dashboard/CLI highlights missing fields inline. |
| **Seed Data Corrupted** | Zero opportunities to match | Fallback to hardcoded minimal JSON grants/investments baked into binary/image. Log critical alert. |

---

## 5. Performance Targets

| Target | Metric | Approach |
|--------|--------|----------|
| Match query latency | `< 2 seconds` | Deterministic rules (no model load time); indexed DB queries; only query `is_active = true` opportunities. |
| Profile CRUD | `< 1 second` | Single-row upserts by unique `profile_id`. |
| Result cardinality | `≤ 5 matches` | Hard limit enforced by Match API; simplest (highest-confidence) matches first. |

---

## 6. Technology Stack (MVP)

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| API Server | Python (FastAPI) | Fast to prototype; built-in request validation; auto-generated OpenAPI docs; async support. |
| Database | SQLite (local dev) / PostgreSQL (deployed) | Minimal setup; full ACID SQL; trivial migration to PostgreSQL later. |
| Frontend | Single HTML + Vanilla JS or Streamlit | Zero build step; fastest path to Tuesday demo. |
| Rules Engine | Python functions (hardcoded logic) | Deterministic, auditable, fast to modify during demo prep. |
| Data Seeding | JSON/CSV files loaded at startup | No external API dependencies for MVP. |
| Containerization | Docker (optional post-MVP) | For now, run locally or on Render free tier. |

---

## 7. Deployment Sketch (MVP)

```yaml
# MVP — Single lightweight unit
┌──────────────────────────────────┐
│  Python App (FastAPI)            │
│  ┌──────────┐  ┌──────────────┐ │
│  │  SQLite  │  │ Seed JSON    │ │
│  │  DB      │  │ Data files   │ │
│  └──────────┘  └──────────────┘ │
│  ┌────────────────────────────┐ │
│  │  Alert/Banner Logic        │ │
│  │  (data freshness warning)  │ │
│  └────────────────────────────┘ │
└──────────────────────────────────┘
         ↓
    Localhost / Render / Heroku
```

---

## 8. Diagram: Request Lifecycle (Match Query)

```text
┌─────────┐      ┌──────────┐      ┌──────────────┐      ┌──────────────┐
│ Client  │──────│ FastAPI  │──────│ Profile Svc  │──────│   Profiles   │
│ (Web/   │      │  Router  │      │              │      │   DB Table   │
│ CLI)    │      │          │      └──────┬───────┘      └──────────────┘
└─────────┘      └────┬─────┘             │
                     │                   │
                     │   ┌──────────────┐│      ┌──────────────────────┐
                     │   │ Eligibility  ││      │ Grants / Investments │
                     └───│   Engine     │├──────│      DB Tables       │
                         │ (Rules)      ││      └──────────────────────┘
                         └──────┬───────┘│
                                │        │
                         ┌──────┴──────┐ │
                         │  Matches    │ │
                         │  (≤ 5)      │ │
                         └─────────────┘ │
                                         │
                                ┌────────┴────┐
                                │ Notification│
                                │ PoC (log)   │
                                └─────────────┘
```

---

*End of HLD*
