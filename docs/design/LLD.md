# Trestle Matching MVP — Low-Level Design (LLD)

**Version:** 1.0 (Tuesday Demo MVP)  
**Date:** 2026-05-22  
**Stage:** SDLC Stage 2 — Low-Level Design  

---

## 1. Database Schema (ERD)

### 1.1 Logical Entity Overview

```
┌────────────────┐     ┌──────────────────────────┐     ┌──────────────────┐
│    profiles    │     │ eligibility_rules        │     │     matches      │
├────────────────┤     ├──────────────────────────┤     ├──────────────────┤
│ id (PK)        │     │ id (PK)                  │     │ id (PK)          │
│ company_name   │     │ name                     │     │ profile_id (FK)  │
│ industry       │◄────│ description              │     │ opportunity_id   │
│ stage          │     │ rule_type                │     │ opportunity_type │
│ funding_need   │     │ field_name               │     │ confidence_score │
│ geographic_pref│     │ operator                 │     │ rationale        │
│ ...            │     │ value_str / value_num    │     │ created_at       │
│                │     │ is_active                │     └──────────────────┘
│                │     │ priority                 │
│                │     │                          │     ┌──────────────────┐
│                │     └──────────────────────────┘     │ grants           │
│                │                                       ├──────────────────┤
│                │                                       │ id (PK)          │
│                │                                       │ title            │
│                │                                       │ source (NIH/etc) │
│                │                                       │ funding_range    │
│                │                                       │ eligibility_criteria...
│                │                                       │ ...              │
│                │                                       └──────────────────┘
│                │     ┌──────────────────────────┐
│                │     │ investment_opportunities │
│                │     ├──────────────────────────┤
│                │     │ id (PK)                  │
│                │     │ fund_name                │
│                │     │ stage (seed/seriesA)     │
│                │     │ ticket_size_min/max      │
│                │     │ therapeutic_area         │
│                │     │ ...                      │
│                │     └──────────────────────────┘
```

### 1.2 Table Definitions

#### `profiles` — Founder Profile Data

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` / `TEXT` | `PRIMARY KEY` | Unique profile identifier (deterministic UUID from email or auto-gen) |
| `company_name` | `VARCHAR(255)` | `NOT NULL` | Legal / DBA name of the company |
| `industry` | `VARCHAR(100)` | `NOT NULL` | Medtech, biotech, digital health, etc. |
| `stage` | `VARCHAR(50)` | `NOT NULL` | pre-seed, seed, series_a, series_b |
| `funding_raised` | `INTEGER` | `NOT NULL DEFAULT 0, CHECK >= 0` | **Total prior funding raised (USD).** Core eligibility filter — many grants reject if raised > threshold |
| `funding_need` | `INTEGER` | `NOT NULL, CHECK >= 0` | Approx. dollar amount (USD) sought |
| `years_in_operation` | `INTEGER` | `NOT NULL DEFAULT 0, CHECK >= 0` | **Years since founding/incorporation.** Core eligibility filter — many grants have max-age limits |
| `accelerator_affiliation` | `VARCHAR(200)` | `NULL` | Accelerator name (e.g., Y Combinator, Techstars). Some grants require accelerator backing |
| `therapeutic_area` | `VARCHAR(200)` | `NOT NULL` | Cardiovascular, oncology, orthopedics, etc. |
| `geographic_pref` | `VARCHAR(200)` | `NOT NULL` | Preferred region (US, EU, global, specific state) |
| `regulatory_pathway` | `VARCHAR(200)` | `NULL` | 510(k), PMA, De Novo, CE, etc. |
| `employees` | `INTEGER` | `NULL, CHECK >= 0` | Rough headcount (used for SBIR eligibility) |
| `created_at` | `TIMESTAMP` | `DEFAULT now()` | Record creation time |
| `updated_at` | `TIMESTAMP` | `DEFAULT now()` | Last update time (triggers re-evaluation if changed ≥ 1 field) |

**Profile count:** ≤ 8 fields total (6 required + 2 optional, plus timestamps, `id`). The 6 required were chosen to directly enable the two core eligibility filters the customer demanded (prior funding raised + company age) plus stage, industry, therapeutic area, and geographic preference. `accelerator_affiliation`, `regulatory_pathway`, and `employees` are optional.

---

#### `grants` — Grant Opportunities (Seed Data)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` / `TEXT` | `PRIMARY KEY` | Unique grant identifier |
| `title` | `TEXT` | `NOT NULL` | Human-readable program name |
| `source` | `VARCHAR(50)` | `NOT NULL, INDEX` | NIH, SBIR, Grants.gov, etc. |
| `source_url` | `VARCHAR(500)` | `NULL` | Link to canonical listing |
| `funding_min` | `INTEGER` | `NULL, CHECK >= 0` | Lower bound of award |
| `funding_max` | `INTEGER` | `NULL, CHECK >= 0` | Upper bound of award |
| `deadline` | `DATE` | `NULL` | Application deadline |
| `industry_focus` | `VARCHAR(200)` | `NULL` | Biotech, medtech, general, etc. |
| `stage_eligible` | `VARCHAR(200)` | `NULL` | Comma-separated or JSON array of stages |
| `therapeutic_focus` | `VARCHAR(300)` | `NULL` | Specific disease categories |
| `qualifying_criteria` | `TEXT` | `NULL` | Human-readable requirement text |
| `is_active` | `BOOLEAN` | `NOT NULL DEFAULT true, INDEX` | Whether this opportunity is open and current |
| `created_at` | `TIMESTAMP` | `DEFAULT now()` | Seed creation time |
| `updated_at` | `TIMESTAMP` | `DEFAULT now()` | Last data refresh (for `freshness_timestamp` calc) |

---

#### `investment_opportunities` — Seed/Series A VC Opportunities

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` / `TEXT` | `PRIMARY KEY` | Unique opportunity identifier |
| `fund_name` | `VARCHAR(255)` | `NOT NULL` | e.g., General Catalyst, Bessemer Venture Partners |
| `fund_type` | `VARCHAR(50)` | `NOT NULL` | VC, corporate VC, angel group |
| `ticket_min` | `INTEGER` | `NULL` | Minimum investment size (USD) |
| `ticket_max` | `INTEGER` | `NULL` | Maximum investment size (USD) |
| `preferred_stage` | `VARCHAR(200)` | `NULL` | seed, series_a, series_b |
| `industry_focus` | `VARCHAR(200)` | `NULL` | Comma-separated or JSON array |
| `therapeutic_focus` | `VARCHAR(300)` | `NULL` | Comma-separated or JSON array |
| `geographic_focus` | `VARCHAR(200)` | `NULL` | US, EU, global, specific states |
| `regulatory_focus` | `VARCHAR(200)` | `NULL` | 510(k) friendly, PMA experience |
| `lead_investor` | `BOOLEAN` | `DEFAULT false` | Willing to lead rounds |
| `is_active` | `BOOLEAN` | `NOT NULL DEFAULT true, INDEX` | Currently open/investing |
| `source_url` | `VARCHAR(500)` | `NULL` | Link to fund page / sample term sheet |
| `created_at` | `TIMESTAMP` | `DEFAULT now()` | Seed creation time |
| `updated_at` | `TIMESTAMP` | `DEFAULT now()` | Last data refresh |

---

#### `eligibility_rules` — Deterministic Matching Rules

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `INTEGER` | `PRIMARY KEY` | Auto-increment rule ID |
| `name` | `VARCHAR(200)` | `NOT NULL` | Human-readable rule name |
| `description` | `TEXT` | `NULL` | Notes on intent |
| `rule_type` | `VARCHAR(50)` | `NOT NULL, INDEX` | `grant` or `investment` (which table it targets) |
| `field_name` | `VARCHAR(100)` | `NOT NULL` | Which DB column of grant/investment to check |
| `operator` | `VARCHAR(20)` | `NOT NULL, CHECK IN(...)` | `eq`, `ne`, `contains`, `gte`, `lte`, `in`, `between` |
| `value_str` | `VARCHAR(500)` | `NULL` | String/match value (e.g., 'medtech') |
| `value_num` | `INTEGER` | `NULL` | Numeric/match value (e.g., `5000000`) |
| `points` | `INTEGER` | `NOT NULL DEFAULT 1` | Weight/score attributed if rule passes |
| `is_active` | `BOOLEAN` | `NOT NULL DEFAULT true, INDEX` | Is this rule currently applied? |
| `priority` | `INTEGER` | `NOT NULL DEFAULT 100` | Lower = applied first in tie-break |
| `logic_group` | `VARCHAR(100)` | `NULL` | Groups rules into AND/OR blocks |
| `created_at` | `TIMESTAMP` | `DEFAULT now()` | |
| `updated_at` | `TIMESTAMP` | `DEFAULT now()` | |

---

#### `matches` — Computed Match Results

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `INTEGER` | `PRIMARY KEY, AUTO INCREMENT` | Result row identifier |
| `profile_id` | `TEXT` | `NOT NULL, INDEX` |
| `opportunity_id` | `TEXT` | `NOT NULL` | FK to `grants.id` or `investment_opportunities.id` |
| `opportunity_type` | `VARCHAR(50)` | `NOT NULL, CHECK IN('grant','investment')` | Denorm for fast filtering |
| `confidence_score` | `INTEGER` | `NOT NULL` | Sum of all passing `eligibility_rules.points` |
| `rationale` | `TEXT` | `NOT NULL` | Human-readable sentence explaining *why* matched (e.g., "industry=medtech AND stage=seed AND funding_need within ticket range") |
| `freshness_timestamp` | `TIMESTAMP` | `NOT NULL` | `MAX(profile.updated_at, opportunity.updated_at, rule.updated_at)` |
| `created_at` | `TIMESTAMP` | `DEFAULT now()` | When match was computed |
| `expires_at` | `TIMESTAMP` | `NULL` | When to recompute (e.g., 24 hours later) |

---

## 2. Indexes Required for `< 2s` Match Query

| Index Name | Table(s) | Columns | Rationale |
|------------|----------|---------|-----------|
| `idx_grants_active` | `grants` | `is_active` | Filter out expired listings; typically reduces scan from full table to tiny subset |
| `idx_grants_source` | `grants` | `source` | Admin `GET /grants` and category filters |
| `idx_investments_active` | `investment_opportunities` | `is_active` | Same reason as grants |
| `idx_investments_stage` | `investment_opportunities` | `preferred_stage` | Used by eligibility engine common filter |
| `idx_matches_profile` | `matches` | `profile_id` | Fetch prior matches for caching/fallback fast |
| `idx_matches_freshness` | `matches` | `freshness_timestamp` | Invalidate old cached match results during demo testing |
| `idx_rules_type_active` | `eligibility_rules` | `rule_type, is_active` | Load only rules relevant to the opportunity being checked |
| `idx_profiles_updated` | `profiles` | `updated_at` | Help identify whether cached match is stale |

**Additional combined indexes (if needed after profiling):**
- `idx_grants_active_industry` (`is_active`, `industry_focus`) — for common target-side filtering.
- `idx_inv_ticket` (`ticket_min`, `ticket_max`) — for numeric range checks (see implementation note below).

---

## 3. SQL DDL (MVP-compatible; works in both PostgreSQL and SQLite)

```sql
-- ============================================
-- profiles
-- ============================================
CREATE TABLE profiles (
    id TEXT PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    industry VARCHAR(100) NOT NULL,
    stage VARCHAR(50) NOT NULL,
    funding_raised INTEGER NOT NULL DEFAULT 0 CHECK (funding_raised >= 0),
    funding_need INTEGER NOT NULL CHECK (funding_need >= 0),
    years_in_operation INTEGER NOT NULL DEFAULT 0 CHECK (years_in_operation >= 0),
    accelerator_affiliation VARCHAR(200),
    therapeutic_area VARCHAR(200) NOT NULL,
    geographic_pref VARCHAR(200) NOT NULL,
    regulatory_pathway VARCHAR(200),
    employees INTEGER CHECK (employees >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- grants
-- ============================================
CREATE TABLE grants (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source VARCHAR(50) NOT NULL,
    source_url VARCHAR(500),
    funding_min INTEGER CHECK (funding_min >= 0),
    funding_max INTEGER CHECK (funding_max >= 0),
    deadline DATE,
    industry_focus VARCHAR(200),
    stage_eligible VARCHAR(200),
    therapeutic_focus VARCHAR(300),
    qualifying_criteria TEXT,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- investment_opportunities
-- ============================================
CREATE TABLE investment_opportunities (
    id TEXT PRIMARY KEY,
    fund_name VARCHAR(255) NOT NULL,
    fund_type VARCHAR(50) NOT NULL,
    ticket_min INTEGER CHECK (ticket_min >= 0),
    ticket_max INTEGER CHECK (ticket_max >= 0),
    preferred_stage VARCHAR(200),
    industry_focus VARCHAR(200),
    therapeutic_focus VARCHAR(300),
    geographic_focus VARCHAR(200),
    regulatory_focus VARCHAR(200),
    lead_investor BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    source_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- eligibility_rules
-- ============================================
CREATE TABLE eligibility_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    rule_type VARCHAR(50) NOT NULL CHECK (rule_type IN ('grant', 'investment')),
    field_name VARCHAR(100) NOT NULL,
    operator VARCHAR(20) NOT NULL,
    value_str VARCHAR(500),
    value_num INTEGER,
    points INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    priority INTEGER NOT NULL DEFAULT 100,
    logic_group VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- matches
-- ============================================
CREATE TABLE matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL REFERENCES profiles(id),
    opportunity_id TEXT NOT NULL,
    opportunity_type VARCHAR(50) NOT NULL CHECK (opportunity_type IN ('grant', 'investment')),
    confidence_score INTEGER NOT NULL,
    rationale TEXT NOT NULL,
    freshness_timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- ============================================
-- Indexes
-- ============================================
CREATE INDEX idx_grants_active ON grants(is_active);
CREATE INDEX idx_grants_source ON grants(source);
CREATE INDEX idx_investments_active ON investment_opportunities(is_active);
CREATE INDEX idx_investments_stage ON investment_opportunities(preferred_stage);
CREATE INDEX idx_rules_type_active ON eligibility_rules(rule_type, is_active);
CREATE INDEX idx_matches_profile ON matches(profile_id);
CREATE INDEX idx_matches_freshness ON matches(freshness_timestamp);
CREATE INDEX idx_profiles_updated ON profiles(updated_at);
```

> **Note:** `AUTOINCREMENT` shown as SQLite syntax. In PostgreSQL, use `SERIAL` or `GENERATED ALWAYS AS IDENTITY`. `CHECK (boolean)` and `BOOLEAN` type differ slightly by dialect; SQLite accepts `1`/`0` as booleans.

---

## 4. Implementation Notes

### 4.1 Why PostgreSQL in Production, SQLite in Dev/MVP Phase

| Aspect | SQLite (Dev / Local) | PostgreSQL (Deployed / Tuesday Demo Backup Plan) |
|--------|---------------------|--------------------------------------------------|
| **Setup** | Zero config, single file | Requires running server, but trivial on Render/Neon/Railway free tier |
| **Indent, Team/Presenter Laptop** | Can't do `pip install` and run from one file | Can fallback to the exact same SQL via Postgres |
| **Performance** | Fine for hundreds of rows | Scales to thousands of grants/opportunities per year |
| **Features** | No `EXPLAIN ANALYZE` verbosity we need for optimization, no JSONB column type if we later shift structured arrays | Full `CHECK` constraints, JSONB for flexible stage arrays, CTEs for complex rule logic |
| **Migration Path** | Trivial: same DDL mostly works, dump-and-restore | Long-term native target |
| **MVP Decision** | **Use SQLite** if presenting locally from a laptop without internet. **Use PostgreSQL** if deploying to a cloud free tier for shared URL demo. |

### 4.2 Deterministic Rule Engine Implementation (Python)

```python
# Pseudo-code — to be implemented in Match API layer

def evaluate_profile_against_opportunity(profile_dict, opp_dict, rules):
    """
    Returns: (matches_opp, score, rationale_items)
    """
    score = 0
    rationale = []
    for rule in rules:
        # Skip inactive rules already filtered, but assert:
        if not rule["is_active"]:
            continue
        opp_field = opp_dict.get(rule["field_name"])
        prof_field = profile_dict.get(rule["field_name"])
        if apply_operator(rule["operator"], prof_field, opp_field, rule["value_str"], rule["value_num"]):
            score += rule["points"]
            rationale.append(rule["description"])
    matched = score >= SCORE_THRESHOLD  # e.g., threshold = 2 (tunable in admin panel)
    return matched, score, rationale
```

### 4.3 Data Freshness Computed for Every Match

```sql
-- freshness_timestamp per match response computed as:
SELECT MAX(
    p.updated_at,
    g.updated_at,       -- or inv.updated_at
    (SELECT MAX(updated_at) FROM eligibility_rules WHERE is_active = TRUE)
) AS freshness_timestamp
```

If `freshness_timestamp` is older than e.g. **48 hours**, the UI shows a yellow banner:  
> "Match results may be stale; data last updated on YYYY-MM-DD."

---

## 5. Security & Data Integrity (MVP)

| Concern | Mitigation in MVP |
|--------|-----------------|
| SQL Injection | Use ORM (SQLAlchemy) or parameterized queries exclusively |
| Missing / malformed profile | API-level Pydantic validators reject bad payloads with `422` before DB touch |
| Rule engine crash by malformed data | `try/except` around rule evaluation; if crash → that opportunity skipped (never fails entire API) |
| Secrets (email API key) | Not used in MVP; notification is console-only. Post-MVP: env vars, never committed |

---

*End of LLD*
