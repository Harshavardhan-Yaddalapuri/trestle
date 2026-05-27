-- ============================================
-- Supabase Migration: Trestle Financials Module
-- Date: 2026-05-22
-- Run via: Supabase Dashboard → SQL Editor → New query → Paste → Run
-- ============================================

-- 1. Add new columns to existing `profiles` table (safe — no destructive changes)
ALTER TABLE IF EXISTS profiles
  ADD COLUMN IF NOT EXISTS company_name text,
  ADD COLUMN IF NOT EXISTS funding_raised integer DEFAULT 0,
  ADD COLUMN IF NOT EXISTS years_in_operation integer DEFAULT 0,
  ADD COLUMN IF NOT EXISTS accelerator_affiliation text,
  ADD COLUMN IF NOT EXISTS therapeutic_area text,
  ADD COLUMN IF NOT EXISTS geographic_pref text,
  ADD COLUMN IF NOT EXISTS regulatory_pathway text,
  ADD COLUMN IF NOT EXISTS employees integer DEFAULT 0;

-- 2. Create new `grants` table (if not exists)
CREATE TABLE IF NOT EXISTS grants (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL,
    source text NOT NULL,
    source_url text,
    funding_min integer,
    funding_max integer,
    deadline date,
    industry_focus text,
    stage_eligible text,
    therapeutic_focus text,
    qualifying_criteria text,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- 3. Create new `investment_opportunities` table (if not exists)
CREATE TABLE IF NOT EXISTS investment_opportunities (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fund_name text NOT NULL,
    fund_type text NOT NULL,
    ticket_min integer,
    ticket_max integer,
    preferred_stage text,
    industry_focus text,
    therapeutic_focus text,
    geographic_focus text,
    regulatory_focus text,
    lead_investor boolean DEFAULT false,
    is_active boolean NOT NULL DEFAULT true,
    source_url text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- 4. Create new `eligibility_rules` table (if not exists)
CREATE TABLE IF NOT EXISTS eligibility_rules (
    id serial PRIMARY KEY,
    name text NOT NULL,
    description text,
    rule_type text NOT NULL CHECK (rule_type IN ('grant','investment')),
    field_name text NOT NULL,
    operator text NOT NULL CHECK (operator IN ('eq','ne','contains','gte','lte','in','between')),
    value_str text,
    value_num integer,
    points integer NOT NULL DEFAULT 1,
    is_active boolean NOT NULL DEFAULT true,
    priority integer NOT NULL DEFAULT 100,
    logic_group text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- 5. Create new `matches` table (if not exists)
CREATE TABLE IF NOT EXISTS matches (
    id serial PRIMARY KEY,
    profile_id text NOT NULL,
    opportunity_id text NOT NULL,
    opportunity_type text NOT NULL CHECK (opportunity_type IN ('grant','investment')),
    confidence_score integer NOT NULL,
    rationale text NOT NULL,
    freshness_timestamp timestamptz NOT NULL,
    created_at timestamptz DEFAULT now(),
    expires_at timestamptz
);

-- 6. Indexes for performance
CREATE INDEX IF NOT EXISTS idx_grants_active ON grants(is_active);
CREATE INDEX IF NOT EXISTS idx_grants_source ON grants(source);
CREATE INDEX IF NOT EXISTS idx_investments_active ON investment_opportunities(is_active);
CREATE INDEX IF NOT EXISTS idx_investments_stage ON investment_opportunities(preferred_stage);
CREATE INDEX IF NOT EXISTS idx_rules_type_active ON eligibility_rules(rule_type, is_active);
CREATE INDEX IF NOT EXISTS idx_matches_profile ON matches(profile_id);
CREATE INDEX IF NOT EXISTS idx_matches_freshness ON matches(freshness_timestamp);
CREATE INDEX IF NOT EXISTS idx_profiles_updated ON profiles(updated_at);

-- 7. Grant public read access (matching engine reads these)
ALTER TABLE grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE investment_opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE eligibility_rules ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public read" ON grants FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON investment_opportunities FOR SELECT USING (true);
CREATE POLICY "Allow public read" ON eligibility_rules FOR SELECT USING (true);

-- 8. 🚀 Done — confirm with:
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'profiles';
