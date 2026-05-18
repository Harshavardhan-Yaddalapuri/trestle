-- Supabase schema for Trestle v0.2

-- Enable vector extension for future semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- Resources table (discovered on-demand, no seed data)
CREATE TABLE resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN (
        'grant','accelerator','pitch_competition','coworking',
        'event','mentorship','tax_credit','hiring_program',
        'filing','learning_material','networking','other'
    )),
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
    provenance JSONB DEFAULT '{}',
    status TEXT DEFAULT 'active' CHECK (status IN ('active','stale','dead','pending_review')),
    last_scraped TIMESTAMPTZ,
    last_verified TIMESTAMPTZ,
    source_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Founder profiles
CREATE TABLE profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT,
    location TEXT,
    state TEXT,
    stage TEXT,
    industry TEXT[],
    demographics TEXT[],
    funding_need TEXT,
    goals TEXT,
    notification_freq TEXT DEFAULT 'daily',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Conversational memory per user
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    session_id TEXT,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Scout runs log
CREATE TABLE scout_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID REFERENCES profiles(id),
    run_type TEXT DEFAULT 'on_demand',
    status TEXT DEFAULT 'completed',
    run_at TIMESTAMPTZ DEFAULT now(),
    sources_queried JSONB,
    new_candidates JSONB,
    changes_detected JSONB,
    summary TEXT,
    duration_ms INT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS
ALTER TABLE resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE scout_runs ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "resources_public_read" ON resources
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "profiles_own" ON profiles
    FOR ALL TO authenticated USING (auth.uid() = user_id);

CREATE POLICY "memories_own" ON memories
    FOR ALL TO authenticated USING (profile_id IN (
        SELECT id FROM profiles WHERE user_id = auth.uid()
    ));

CREATE POLICY "scout_runs_own" ON scout_runs
    FOR ALL TO authenticated USING (profile_id IN (
        SELECT id FROM profiles WHERE user_id = auth.uid()
    ));

-- Indexes
CREATE INDEX idx_resources_type ON resources(type);
CREATE INDEX idx_resources_status ON resources(status);
CREATE INDEX idx_resources_location ON resources USING gin(location);
CREATE INDEX idx_resources_last_verified ON resources(last_verified);
CREATE INDEX idx_profiles_user_id ON profiles(user_id);
CREATE INDEX idx_memories_profile_id ON memories(profile_id);
CREATE INDEX idx_memories_category ON memories(category);
