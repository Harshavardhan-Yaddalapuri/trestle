-- ============================================================================
-- Trestle v1 — Initial Schema Migration
-- Derived from: /docs/discovery/lld-trestle.md (Aurthur, v0.2)
-- Date: 2026-05-25
-- Supabase project: Managed PostgreSQL 15.x
-- ============================================================================

-- Extension required for trigram GIN indexes on grant name search
create extension if not exists pg_trgm;

-- ============================================================================
-- 1. users — links to Supabase auth.users via FK
-- ============================================================================
create table users (
    id              uuid        primary key default gen_random_uuid(),
    supabase_uid    uuid        not null references auth.users(id) on delete cascade,
    email           text        not null,
    name            text,
    role            text        not null default 'founder'
                                check (role in ('founder', 'admin')),
    email_verified  boolean     not null default false,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    deleted_at      timestamptz
);

create unique index users_supabase_uid_idx on users (supabase_uid);
create unique index users_email_idx         on users (email) where deleted_at is null;

-- ============================================================================
-- 2. anonymous_sessions
-- ============================================================================
create table anonymous_sessions (
    id                  uuid        primary key default gen_random_uuid(),
    ip_address          inet,
    user_agent          text,
    fingerprint         text,
    profile_snapshot    jsonb       not null default '{}',
    converted_user_id   uuid        references users(id),
    merged_at           timestamptz,
    expires_at          timestamptz not null default (now() + interval '30 days'),
    created_at          timestamptz not null default now(),
    deleted_at          timestamptz
);

create index anon_sessions_expires_idx    on anonymous_sessions (expires_at);
create index anon_sessions_converted_idx  on anonymous_sessions (converted_user_id);
create index anon_sessions_fingerprint_idx on anonymous_sessions (fingerprint);

-- ============================================================================
-- 3. profiles — general-purpose founder profile (30+ columns)
-- ============================================================================
create table profiles (
    id                      uuid        primary key default gen_random_uuid(),
    user_id                 uuid        not null references users(id),
    -- Company basics
    company_name            text,
    incorporation_type      text        check (incorporation_type in
                                    ('delaware_c_corp', 'llc', 'other')),
    incorporation_country   text        default 'US',
    location_city           text,
    location_state          text,
    location_country        text        default 'US',
    team_size               int,
    team_roles              text[]      default '{}',
    -- Product & regulatory
    industry_tags           text[]      default '{}',
    product_type            text        check (product_type in
                                    ('device', 'drug', 'diagnostic', 'software', 'other')),
    therapeutic_area        text,
    data_status             text        check (data_status in
                                    ('benchtop', 'glp', 'clinical', 'fda_cleared')),
    regulatory_pathway      text        check (regulatory_pathway in
                                    ('510k', 'pma', 'denovo', 'de-novo', 'exempt', 'ce_mark')),
    -- Financials
    monthly_burn_usd        bigint,
    runway_months           int,
    last_raise_amount_usd   bigint,
    last_raise_date         date,
    capital_need_12m_usd    bigint,
    -- Eligibility signals
    company_age_months      int,
    revenue_usd             bigint,
    has_ip_license          boolean,
    prior_sbir_awards       int         default 0,
    sbir_eligible           boolean,
    -- Preferences
    minimum_grant_size_usd  bigint      default 300000,
    geographic_scope        text        check (geographic_scope in
                                    ('us_only', 'uk', 'eu', 'multi_region')),
    alert_frequency         text        check (alert_frequency in
                                    ('daily', 'weekly', 'never')),
    auth_decline_count      int         not null default 0,
    no_auth                 boolean     not null default false,
    -- Metadata
    profile_json            jsonb       default '{}',
    completeness_score      numeric(3,2) default 0.0,
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now(),
    deleted_at              timestamptz,
    -- 1:1 with users
    constraint profiles_user_id_unique unique (user_id)
);

create unique index profiles_user_id_idx         on profiles (user_id);
create index profiles_stage_idx                  on profiles (data_status);
create index profiles_regulatory_idx             on profiles (regulatory_pathway);
create index profiles_completeness_idx           on profiles (completeness_score);
create index profiles_profile_json_gin_idx       on profiles using gin (profile_json);

-- ============================================================================
-- 4. skills — multi-skill plugin registry
-- ============================================================================
create table skills (
    id                      uuid        primary key default gen_random_uuid(),
    slug                    text        not null,
    name                    text        not null,
    description             text,
    status                  text        not null default 'draft'
                                check (status in ('draft', 'beta', 'live', 'deprecated')),
    required_profile_fields text[]      default '{}',
    config_json             jsonb       default '{}',
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now(),
    deleted_at              timestamptz
);

create unique index skills_slug_idx   on skills (slug);
create index skills_status_idx       on skills (status);

-- ============================================================================
-- 5. user_skills — junction: user → skill
-- ============================================================================
create table user_skills (
    id          uuid        primary key default gen_random_uuid(),
    user_id     uuid        not null references users(id),
    skill_id    uuid        not null references skills(id),
    enabled_at  timestamptz default now(),
    created_at  timestamptz not null default now(),
    deleted_at  timestamptz,
    constraint user_skills_unique_active
        unique (user_id, skill_id)  -- partial unique handled by app layer (deleted_at IS NULL)
);

-- ============================================================================
-- 6. conversations
-- ============================================================================
create table conversations (
    id                    uuid        primary key default gen_random_uuid(),
    user_id               uuid        references users(id),
    anonymous_session_id  uuid        references anonymous_sessions(id),
    active_skill_id       uuid        references skills(id),
    status                text        not null default 'active'
                                check (status in ('active', 'closed', 'transferred')),
    turn_count            int         default 0,
    first_value_at        timestamptz,
    created_at            timestamptz not null default now(),
    updated_at            timestamptz not null default now(),
    deleted_at            timestamptz,
    -- Exactly one of user_id or anonymous_session_id must be non-null
    constraint conversations_ownership_check
        check (num_nonnulls(user_id, anonymous_session_id) = 1)
);

create index conversations_user_id_created_idx on conversations (user_id, created_at desc);
create index conversations_anon_session_idx     on conversations (anonymous_session_id);

-- ============================================================================
-- 7. messages
-- ============================================================================
create table messages (
    id                uuid        primary key default gen_random_uuid(),
    conversation_id   uuid        not null references conversations(id),
    role              text        not null check (role in ('user', 'assistant', 'system', 'tool')),
    content           text        not null,
    intent            text        check (intent in (
                            'greet', 'discover', 'match_request', 'deep_dive',
                            'grant_question', 'dismiss', 'edge_case', 'vague',
                            'unknown', 'skill_switch', 'profile_update', 'lifecycle_action'
                        )),
    tokens_used       int,
    latency_ms        int,
    idempotency_key   text,
    created_at        timestamptz not null default now(),
    deleted_at        timestamptz
);

create index messages_conversation_created_idx on messages (conversation_id, created_at desc);
create index messages_intent_idx               on messages (intent);
create unique index messages_idempotency_idx   on messages (idempotency_key)
    where idempotency_key is not null;

-- ============================================================================
-- 8. grants
-- ============================================================================
create table grants (
    id                  uuid        primary key default gen_random_uuid(),
    source              text        not null,
    source_id           text,
    name                text        not null,
    description         text,
    amount_min_usd      bigint,
    amount_max_usd      bigint,
    deadline            date,
    status              text        not null default 'open'
                                check (status in ('open', 'closed', 'rolling', 'upcoming')),
    eligibility_rules   jsonb       not null default '{}',
    tags                text[]      default '{}',
    -- source_url is MANDATORY — no grant without a verifiable URL
    source_url          text        not null,
    url_last_verified   timestamptz,
    url_is_live         boolean     not null default true,
    url_status_code     int,
    metadata_json       jsonb       default '{}',
    last_synced_at      timestamptz,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now(),
    deleted_at          timestamptz
);

create unique index grants_source_source_id_idx on grants (source, source_id)
    where source_id is not null;
create index grants_deadline_idx          on grants (deadline);
create index grants_status_idx            on grants (status);
create index grants_url_live_idx          on grants (url_is_live) where url_is_live = true;
create index grants_eligibility_gin_idx   on grants using gin (eligibility_rules);
create index grants_tags_gin_idx          on grants using gin (tags);
create index grants_name_trgm_idx         on grants using gin (name gin_trgm_ops);

-- ============================================================================
-- 9. grant_lifecycle — 14-state state machine
-- ============================================================================
create table grant_lifecycle (
    id                      uuid        primary key default gen_random_uuid(),
    user_id                 uuid        not null references users(id),
    grant_id                uuid        not null references grants(id),
    status                  text        not null
                                check (status in (
                                    'discovered', 'saved', 'interested', 'started',
                                    'applied', 'submitted', 'under_review', 'accepted',
                                    'awarded', 'rejected', 'reconsidering', 'dismissed',
                                    'abandoned', 'archived'
                                )),
    previous_status         text,
    attempt_number          int         not null default 1,
    saved_at                timestamptz,
    interested_at           timestamptz,
    started_at              timestamptz,
    applied_at              timestamptz,
    submitted_at            timestamptz,
    under_review_at         timestamptz,
    accepted_at             timestamptz,
    awarded_at              timestamptz,
    rejected_at             timestamptz,
    reconsidering_at        timestamptz,
    dismissed_at            timestamptz,
    abandoned_at            timestamptz,
    archived_at             timestamptz,
    expected_decision_date  date,
    award_amount_usd        bigint,
    award_terms             text,
    rejection_reason        text,
    feedback_notes          text,
    dismissal_reason        text        check (dismissal_reason in (
                                    'not_enough_money', 'wrong_category',
                                    'deadline_too_soon', 'already_applied', 'unspecified'
                                )),
    notes                   text,
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now(),
    deleted_at              timestamptz,
    constraint lifecycle_user_grant_attempt_unique
        unique (user_id, grant_id, attempt_number)
);

create index lifecycle_user_status_idx   on grant_lifecycle (user_id, status);
create index lifecycle_grant_status_idx  on grant_lifecycle (grant_id, status);
create index lifecycle_deadline_idx       on grant_lifecycle (expected_decision_date);

-- ============================================================================
-- 10. grant_lifecycle_transitions — audit log for every state change
-- ============================================================================
create table grant_lifecycle_transitions (
    id                uuid        primary key default gen_random_uuid(),
    lifecycle_id      uuid        not null references grant_lifecycle(id),
    from_status       text        not null,
    to_status         text        not null,
    trigger_type      text        not null
                            check (trigger_type in
                                ('user_action', 'agent_inference', 'time_based', 'auto')),
    trigger_detail    text,
    conversation_id   uuid        references conversations(id),
    created_at        timestamptz not null default now()
);

create index transitions_lifecycle_idx on grant_lifecycle_transitions (lifecycle_id, created_at desc);

-- ============================================================================
-- 11. grants_dismissed — negative signal for matching
-- ============================================================================
create table grants_dismissed (
    id                uuid        primary key default gen_random_uuid(),
    user_id           uuid        not null references users(id),
    grant_id          uuid        not null references grants(id),
    reason            text        check (reason in
                            ('not_enough_money', 'wrong_category', 'deadline_too_soon',
                             'already_applied', 'unspecified')),
    custom_reason     text,
    conversation_id   uuid        references conversations(id),
    created_at        timestamptz not null default now(),
    deleted_at        timestamptz,
    constraint dismissed_user_grant_unique
        unique (user_id, grant_id)
);

create index dismissed_user_reason_idx on grants_dismissed (user_id, reason);

-- ============================================================================
-- 12. alerts
-- ============================================================================
create table alerts (
    id                uuid        primary key default gen_random_uuid(),
    user_id           uuid        not null references users(id),
    grant_id          uuid        references grants(id),
    lifecycle_id      uuid        references grant_lifecycle(id),
    alert_type        text        not null
                            check (alert_type in (
                                'new_grant_match', 'deadline_approaching', 'deadline_imminent',
                                'deadline_passed', 'review_halfway', 'decision_expected',
                                'decision_overdue', 'reconsideration_window', 'no_activity',
                                'grant_updated', 'profile_change_unlock', 're_engagement'
                            )),
    message_preview   text        not null,
    rich_payload      jsonb       default '{}',
    status            text        not null default 'pending'
                            check (status in ('pending', 'sent', 'dismissed', 'acted')),
    dismissed_reason  text,
    scheduled_at      timestamptz,
    sent_at           timestamptz,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now(),
    deleted_at        timestamptz
);

create index alerts_user_status_idx   on alerts (user_id, status, created_at desc);
create index alerts_scheduled_idx     on alerts (scheduled_at) where status = 'pending';
create index alerts_type_idx          on alerts (alert_type);
create index alerts_lifecycle_idx     on alerts (lifecycle_id);

-- ============================================================================
-- 13. alert_deliveries
-- ============================================================================
create table alert_deliveries (
    id                uuid        primary key default gen_random_uuid(),
    alert_id          uuid        not null references alerts(id),
    channel           text        not null check (channel in ('in_app', 'email', 'telegram')),
    status            text        not null default 'queued'
                            check (status in ('queued', 'sent', 'failed', 'bounced')),
    external_id       text,
    error_message     text,
    idempotency_key   text        not null,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now()
);

create index deliveries_alert_channel_idx    on alert_deliveries (alert_id, channel);
create unique index deliveries_idempotency_idx on alert_deliveries (idempotency_key);

-- ============================================================================
-- 14. data_source_syncs
-- ============================================================================
create table data_source_syncs (
    id                      uuid        primary key default gen_random_uuid(),
    source                  text        not null,
    status                  text        not null
                                check (status in ('running', 'success', 'failed', 'degraded')),
    records_fetched         int         default 0,
    records_upserted        int         default 0,
    records_skipped_no_url  int         default 0,
    error_message           text,
    started_at              timestamptz not null,
    completed_at            timestamptz,
    created_at              timestamptz not null default now()
);

create index syncs_source_started_idx on data_source_syncs (source, started_at desc);

-- ============================================================================
-- 15. url_verification_logs
-- ============================================================================
create table url_verification_logs (
    id            uuid        primary key default gen_random_uuid(),
    grant_id      uuid        not null references grants(id),
    url           text        not null,
    status_code   int,
    is_live       boolean     not null,
    checked_at    timestamptz not null,
    error_message text
);

create index url_logs_grant_idx on url_verification_logs (grant_id, checked_at desc);

-- ============================================================================
-- 16. audit_logs
-- ============================================================================
create table audit_logs (
    id          uuid        primary key default gen_random_uuid(),
    user_id     uuid        references users(id),
    table_name  text        not null
                        check (table_name in
                            ('profiles', 'grant_lifecycle', 'grants_dismissed')),
    record_id   uuid        not null,
    action      text        not null check (action in ('create', 'update', 'delete')),
    old_values  jsonb,
    new_values  jsonb,
    ip_address  inet,
    created_at  timestamptz not null default now()
);

create index audit_user_idx          on audit_logs (user_id, created_at desc);
create index audit_table_record_idx  on audit_logs (table_name, record_id);

-- ============================================================================
-- Seed: default 'grants' skill for v1
-- ============================================================================
insert into skills (slug, name, description, status, required_profile_fields, config_json)
values (
    'grants',
    'Grant Intelligence',
    'Find, track, and manage grant applications for your startup.',
    'live',
    array[
        'company_name', 'incorporation_type', 'incorporation_country',
        'location_city', 'location_state', 'location_country',
        'team_size', 'industry_tags', 'product_type', 'therapeutic_area',
        'data_status', 'regulatory_pathway', 'monthly_burn_usd',
        'runway_months', 'last_raise_amount_usd', 'capital_need_12m_usd',
        'company_age_months', 'revenue_usd', 'has_ip_license',
        'prior_sbir_awards', 'sbir_eligible', 'minimum_grant_size_usd',
        'geographic_scope'
    ],
    '{
        "version": "1.0.0",
        "match_engine": "eligibility_rules_jsonb",
        "max_matches_per_query": 5,
        "require_source_url": true,
        "lifecycle_states": 14,
        "alert_types": [
            "new_grant_match", "deadline_approaching", "deadline_imminent",
            "deadline_passed", "review_halfway", "decision_expected",
            "decision_overdue", "reconsideration_window", "no_activity",
            "grant_updated", "profile_change_unlock", "re_engagement"
        ]
    }'::jsonb
);
