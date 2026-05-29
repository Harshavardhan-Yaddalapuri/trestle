# Supabase Migration Plan

## 1. Running Migrations

Three equivalent methods:

1. **Supabase Dashboard SQL Editor** (fastest for demo-day)  
   Log in → Project → SQL Editor → New query → paste each migration → Run.

2. **Supabase CLI** (good for team repos with CI later)  
   ```bash
   supabase migrations new 001_add_profile_cols
   # copy SQL into supabase/migrations/####_001_add_profile_cols.sql
   supabase db push
   ```

3. **One-shot `psql`** (if you have direct Postgres connection string)  
   ```bash
   psql "$DATABASE_URL" < migrations/001_add_profile_cols.sql
   ```

> **Recommendation for Tuesday demo:** Use the **Dashboard SQL Editor**—zero onboarding time, no CLI install, and all DDL runs inside the same Supabase project the frontend already points to.

---

## 2. Existing `profiles` Table Changes

In Trestle, the `profiles` table already exists with:
- `id (UUID PK)`, `user_id (UUID FK)`, `name`, `location`, `state`, `stage`, `industry`, `demographics`, `funding_need`, `goals`

New columns to add:

| Column | Type | Constraints | Relevance |
|--------|------|-------------|-----------|
| `company_name` | `VARCHAR(255)` | `NOT NULL` (enforced at API level) | Matching display / auditing |
| `funding_raised` | `INTEGER` | `DEFAULT 0`, `CHECK ≥ 0` | **Core eligibility filter** — many grants reject if raised > threshold |
| `years_in_operation` | `INTEGER` | `DEFAULT 0`, `CHECK ≥ 0` | **Core eligibility filter** — age limits |
| `accelerator_affiliation` | `VARCHAR(200)` | nullable | Some grants require accelerator backing |
| `therapeutic_area` | `VARCHAR(200)` | `NOT NULL` | Grants/VC therapeutic overlap |
| `geographic_pref` | `VARCHAR(200)` | `NOT NULL` | Region eligibility |
| `regulatory_pathway` | `VARCHAR(200)` | nullable | 510(k), PMA, CE |
| `employees` | `INTEGER` | `CHECK ≥ 0`, nullable | SBIR ≤500-employee check |

DDL:

```sql
ALTER TABLE profiles
    ADD COLUMN IF NOT EXISTS company_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS funding_raised INTEGER DEFAULT 0 CHECK (funding_raised >= 0),
    ADD COLUMN IF NOT EXISTS years_in_operation INTEGER DEFAULT 0 CHECK (years_in_operation >= 0),
    ADD COLUMN IF NOT EXISTS accelerator_affiliation VARCHAR(200),
    ADD COLUMN IF NOT EXISTS therapeutic_area VARCHAR(200),
    ADD COLUMN IF NOT EXISTS geographic_pref VARCHAR(200),
    ADD COLUMN IF NOT EXISTS regulatory_pathway VARCHAR(200),
    ADD COLUMN IF NOT EXISTS employees INTEGER CHECK (employees >= 0);

CREATE INDEX IF NOT EXISTS idx_profiles_updated ON profiles(updated_at);
```

> **Note:** Because Supabase `profiles` is already linked to **Row-Level Security (RLS)** policies tied to `auth.uid() ⇔ user_id`, adding columns is non-breaking. No RLS changes needed unless you plan to expose `matches` directly to the client.

---

## 3. New Tables — DDL

### 3.1 `grants`

```sql
CREATE TABLE IF NOT EXISTS grants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_grants_active ON grants(is_active);
CREATE INDEX IF NOT EXISTS idx_grants_source ON grants(source);
CREATE INDEX IF NOT EXISTS idx_grants_active_industry ON grants(is_active, industry_focus);
```

### 3.2 `investment_opportunities`

```sql
CREATE TABLE IF NOT EXISTS investment_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fund_name VARCHAR(255) NOT NULL,
    fund_type VARCHAR(50) NOT NULL,
    ticket_min INTEGER CHECK (ticket_min >= 0),
    ticket_max INTEGER CHECK (ticket_max >= 0),
    preferred_stage VARCHAR(200),
    industry_focus VARCHAR(200),
    therapeutic_focus VARCHAR(300),
    geographic_focus VARCHAR(200),
    regulatory_focus VARCHAR(200),
    lead_investor BOOLEAN DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    source_url VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_investments_active ON investment_opportunities(is_active);
CREATE INDEX IF NOT EXISTS idx_investments_stage ON investment_opportunities(preferred_stage);
```

### 3.3 `eligibility_rules`

```sql
CREATE TABLE IF NOT EXISTS eligibility_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    rule_type VARCHAR(50) NOT NULL CHECK (rule_type IN ('grant', 'investment')),
    field_name VARCHAR(100) NOT NULL,
    operator VARCHAR(20) NOT NULL CHECK (operator IN ('eq', 'ne', 'contains', 'gte', 'lte', 'in', 'between')),
    value_str VARCHAR(500),
    value_num INTEGER,
    points INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT true,
    priority INTEGER NOT NULL DEFAULT 100,
    logic_group VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rules_type_active ON eligibility_rules(rule_type, is_active);
```

### 3.4 `matches` (audit/cache)

```sql
CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    opportunity_id UUID NOT NULL,
    opportunity_type VARCHAR(50) NOT NULL CHECK (opportunity_type IN ('grant', 'investment')),
    confidence_score INTEGER NOT NULL,
    rationale TEXT NOT NULL,
    freshness_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ DEFAULT (now() + interval '24 hours')
);

CREATE INDEX IF NOT EXISTS idx_matches_profile ON matches(profile_id);
CREATE INDEX IF NOT EXISTS idx_matches_freshness ON matches(freshness_timestamp);
```

---

## 4. Migration Rollback Plan (if something goes wrong)

| Step | Undo action |
|------|-------------|
| Bad column added to `profiles` | `ALTER TABLE profiles DROP COLUMN IF EXISTS new_col;` (columns added are nullable defaults, safe to drop) |
| New tables seeded with wrong data | `TRUNCATE TABLE grants, investment_opportunities, eligibility_rules, matches RESTART IDENTITY;` |
| Duplicate indexes created | `DROP INDEX CONCURRENTLY IF EXISTS idx_name;` |
| RLS broken by a trigger | Disable trigger in Dashboard → Database → Triggers |

---

## 5. How to Verify Migrations Applied

```bash
# Ping the tables via existing FastAPI client (Python one-liner)
cd backend && python -c "
from app.database import supabase
for t in ['grants','investment_opportunities','eligibility_rules','matches']:
    r = supabase.table(t).select('id', count='exact').limit(1).execute()
    print(t, 'count=', r.count)
"
```

Expected output after seed:
```
grants count= 6
investment_opportunities count= 2
eligibility_rules count= 5
matches count= 0
```
