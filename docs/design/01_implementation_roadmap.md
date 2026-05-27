# Stage 3 Implementation Roadmap — Trestle Financials Module

> Target: Demo-ready by Tuesday.  
> Duration: ~1–2 days (assume 12–16 dev hours).

---

## 1. Files to Create (New)

| # | File | Purpose |
|---|------|---------|
| 1 | `backend/app/data/seed_investments.json` | 2–3 real medtech investment opportunities for the seed loader |
| 2 | `backend/app/routers/financials.py` *(or extend `matching.py`)* | New / refactored router for `GET /matches`, `GET /grants`, `POST /profiles/me` |
| 3 | `backend/app/services/eligibility_engine.py` | Standalone deterministic rule evaluator (extracted from `matching_engine.py`) |
| 4 | `supabase/migrations/001_add_profile_cols.sql` | ALTER TABLE on existing `profiles` (new matching fields) |
| 5 | `supabase/migrations/002_create_grants.sql` | `grants` table + indexes |
| 6 | `supabase/migrations/003_create_investments.sql` | `investment_opportunities` table + indexes |
| 7 | `supabase/migrations/004_create_eligibility_rules.sql` | `eligibility_rules` table + indexes |
| 8 | `supabase/migrations/005_create_matches.sql` | `matches` (audit/cache) table + indexes |
| 9 | `scripts/populate_seed.py` | One-shot script: inserts JSON seed data into Supabase via REST API (safe for someone without direct SQL access) |

---

## 2. Files to Modify (Existing)

| # | File | Change | Why |
|---|------|--------|-----|
| A | `backend/app/models/schemas.py` | Add `funding_raised`, `years_in_operation`, `accelerator_affiliation` as required on `ProfileBase`; add response schemas for financials | Front-end already expects these fields in the design |
| B | `backend/app/routers/profile.py` | Update `GET /me` and `PATCH /me` to read/write the three new fields | Must serve enriched profiles before matching can run |
| C | `backend/app/routers/matching.py` | Wire correct Supabase table names, add `investment_opportunities` fetch, fix JSON seed path, wire `seed_investments.json` | Existing router is close but missing investment seed and has placeholder UUID code |
| D | `backend/app/services/matching_engine.py` | Extract core rule logic into `eligibility_engine.py`; keep only `seed_data()` orchestrator | Single responsibility; engine must be testable offline |
| E | `backend/app/main.py` | Verify `/health` includes a DB ping (it already exists); ensure `matching` router prefix is merged or alias added | `/api/matches` must be reachable |
| F | `.env.example` | No changes needed (no new secrets) | — |

---

## 3. Exact Build Order (Dependency Chain)

> **Golden rule:** Schema first → Seed data → Engine → Router → Smoke tests

### Day 1 Morning (3–4 hrs)
1. **Run migration 001** — Add columns to `profiles`.
2. **Run migrations 002–005** — Create the four new tables.
3. **Insert seed data** — Run `seed_data()` logic (or `populate_seed.py`) to load existing `seed_grants.json`, new `seed_investments.json`, and `seed_rules.json`.
4. **Spot-check in Supabase dashboard** — Verify tables, indexes, and seed rows are present.

### Day 1 Afternoon (4–5 hrs)
5. **Update schemas** (`schemas.py`) — Make new profile fields required; tighten models.
6. **Update `profile.py`** — Wire the new columns in `GET /me` and `PATCH /me`.
7. **Build `eligibility_engine.py`** — Extract/polish rule evaluation, add rationale builder.
8. **Update `matching.py`** — Fetch both `grants` and `investment_opportunities`, use new engine, write audit rows to `matches`, return `MatchListResponse`.

### Day 2 Morning (3–4 hrs)
9. **Wire `GET /grants`** — Admin listing with filters (`source`, `is_active`, pagination).
10. **Wire `/health` DB ping** — Already exists, just confirm Supabase latency is healthy.
11. **End-to-end smoke test** — `PATCH /profiles/me` → `GET /matches` → check ≤5 results, latency < 2s.
12. **Add `seed_investments.json`** — Populate 2–3 real medtech VCs (see `05_data_seeding_plan.md`).

### Day 2 Afternoon (Buffer / Polish)
13. **Rationale strings** — Ensure every returned match has a human-readable sentence, not just pipe-separated rule names.
14. **Edge-case handling** — Stale data fallback (return cached `matches` table rows if engine errors).
15. **Cut scope if behind schedule** — See `06_risk_checklist.md`.

---

## 4. Supabase Migration Order

| Order | Migration | Depends On |
|-------|-----------|------------|
| 1 | `001_add_profile_cols.sql` | None (safe `IF NOT EXISTS` syntax) |
| 2 | `002_create_grants.sql` | None |
| 3 | `003_create_investments.sql` | None |
| 4 | `004_create_eligibility_rules.sql` | None |
| 5 | `005_create_matches.sql` | Migration 001 (FK to `profiles.id`) |

---

## 5. Seed Data Strategy

* **Grants** — Already curated in `backend/app/data/seed_grants.json` (6 real grants: NIH SBIR Phase I/II, Gates Grand Challenges, NSF SBIR, BARDA DRIVe, PCORI).  
* **Rules** — Already curated in `backend/app/data/seed_rules.json` (5 rules: stage match, funding ceiling, company age, industry alignment, therapeutic area).  
* **Investment opportunities** — **Not yet created.** Need 2–3 real medtech VC / corporate fund entries (e.g., Healthtech Capital, SV Health Investors, Cultiv8). Will be authored in `seed_investments.json` and loaded by the same `seed_data()` function.
