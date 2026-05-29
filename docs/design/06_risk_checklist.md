# Risk Checklist — Trestle Financials Stage 3

## 1. What Could Break During Implementation

| # | Risk | Probability | Impact | Mitigation |
|---|------|-------------|--------|------------|
| 1 | **Supabase RLS blocks seed inserts** | Medium | High | Run `supabase.auth.admin.list_users()` is unnecessary; instead, use **service role key** (already configured in `config.py`). Ensure `SUPABASE_SERVICE_KEY` has bypass-RLS rights. Test seeding immediately after migration. |
| 2 | **`profiles.id` / `user_id` type mismatch** (FK from `matches.profile_id` → `profiles.id`) | Medium | High | Verify that `profiles.id` is actually `UUID` (not `TEXT`). `seed_data()` and the existing `profile.py` already use UUIDs, but double-check the ALTER statements don’t accidentally change the PK type. |
| 3 | **Frontend expects `/api/matches`, backend exposes `/api/matching/matches`** | High | Medium | Add alias routes in `main.py` (see `04_api_endpoints_plan.md` §5) or change the include_router prefix. Confirm exact paths with frontend team before Tuesday. |
| 4 | **`between` operator crashes on malformed `value_str`** | Low | Medium | Already wrapped in `try/except` in `matching_engine.py`; but ensure `seed_investment_rules.json` uses strict `"min,max"` syntax with no spaces. Add unit test. |
| 5 | **Seed JSON `funding_min` is `0` but check requires `≥ 0`** | Low | Low | PostgreSQL `CHECK` allows `0`; SQLite does not enforce `CHECK` by default. Ensure Supabase (Postgres) is the target DB for demo. |
| 6 | **Rate-limiting on `GET /matches`** | Low | Low | SlowAPI is already configured; `30/minute` is fine for demo. If you hit limits during load test, temporarily bump to `300/minute` or remove the decorator for the demo account. |
| 7 | **Supabase free-tier connection pool exhaustion** | Medium | Medium | Each request opens a short-lived HTTP call. Demo load is 1–2 users. Unless you run a load test with > 20 concurrent users, you’re safe. |
| 8 | **Date/time zone mismatches** (`deadline`, `created_at`, `freshness_timestamp`) | Medium | Medium | Use `datetime.now(timezone.utc).isoformat()` consistently in Python. Supabase stores `TIMESTAMPTZ` correctly. If frontend shows wrong dates, ensure it parses ISO-8601 and applies local TZ client-side. |
| 9 | **Missing `investment_opportunities` seed causes zero matches of type `investment`** | High | Low | Front-end may show empty “Investment” tab. Mitigate by creating `seed_investments.json` (see `05_data_seeding_plan.md`) and verifying counts. |

---

## 2. What Is Most Likely to Take Longer Than Expected

| # | Task | Time Estimate | Why It Might Slip |
|---|------|---------------|-------------------|
| A | **Building rationale strings with friendly sentences** | 1 hr | Requires a mapping table from rule names → human text; edge cases (empty string, too-long string, non-ASCII chars). |
| B | **End-to-end latency optimization (< 2s)** | 1–2 hrs | If Supabase table scan on `grants` is slow (no effective index), need to add `.limit(200)` or refactor query to push more filtering into Postgres (RLS may block). |
| C | **Writing meaningful investment-matching rules that score > 0** | 1 hr | Investment rules use numeric `between` and `in` on string lists; one syntax error and all 3 investment seeds return zero matches. |
| D | **Aligning existing profile router (`/api/profiles/me`) with new enriched schema** | 1–2 hrs | Existing code uses `profile_id = user_id` auto-generation in `matching.py` while `profile.py` uses `uid` from JWT. Need to make sure enriched fields survive round-trip without being dropped or overwritten by old onboarding data. |

---

## 3. What Can Be Cut If Behind Schedule

### Priority Order — Cut from bottom up

| Cut Rank | Item | Effect if Removed | Effort Saved |
|----------|------|-------------------|--------------|
| 1 | **Investment opportunities + matching rules** | Demo shows grants only (still 6 real grants). Matches still work, just fewer results. | ~2 hrs (seed JSON + rules + engine branch) |
| 2 | **Rationale sentence mapping** | Rationale strings become raw rule names joined by `" | "`. Still readable enough for a demo. | ~1 hr |
| 3 | **Caching / stale fallback via `matches` table** | If engine crashes, return 500 instead of degraded cached results. Acceptable for a 2-person demo. | ~1 hr |
| 4 | **`GET /grants` admin endpoint filters/pagination** | Return all rows (max 6). No offset/limit logic needed. | ~30 min |
| 5 | **`freshness_timestamp` compututation** | Hard-code to `now()` instead of scanning `_updated_at` across profile + opportunities. | ~30 min |
| 6 | **Profile onboarding integration** | Manually insert enriched profile via cURL or Swagger UI, bypassing onboarding UI. | ~1.5 hrs |

> **Minimum Viable Demo:** Even if you only keep items 7+ (i.e., do not cut the core engine or the grants seed), the demo can still show:  
> 1. Create enriched profile → 2. `GET /matches` → 3. See 5 ranked grants with scores.

---

## 4. Pre-Demo Smoke-Test Script

Save as `scripts/demo_smoke_test.sh`. Run it right before the demo:

```bash
#!/usr/bin/env bash
set -e
BASE="http://localhost:8000"

echo "=== 1. Health ==="
curl -s "$BASE/health" | jq .

echo "=== 2. Upsert profile ==="
PROFILE=$(curl -s -X POST "$BASE/api/matching/profiles" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Demo Med Inc",
    "industry": ["medtech"],
    "stage": "seed",
    "funding_raised": 100000,
    "years_in_operation": 1,
    "accelerator_affiliation": null,
    "therapeutic_area": "cardiovascular",
    "geographic_pref": "US",
    "funding_need": "400000",
    "goals": "FDA 510(k) clearance"
  }')
echo "$PROFILE" | jq .
PID=$(echo "$PROFILE" | jq -r '.id')

echo "=== 3. Get matches ==="
curl -s "$BASE/api/matching/matches?profile_id=$PID&opportunity_type=all" | jq .

echo "=== 4. List grants ==="
curl -s "$BASE/api/matching/grants?limit=10" | jq .

echo "=== Done ==="
```

**Expected total runtime:** < 4 seconds (well under 2s per endpoint).

---

## 5. Roll-of-Honor Escalation Path

If a critical bug is found < 2 hours before demo:

1. **Kill the server** and run SQLite fallback (dev mode) from `app/data/schema.sql` + `seed_grants.json`. This avoids all Supabase network latency.
2. **Serve static JSON** from `matching_engine.py` `rank_matches()` by replacing Supabase calls with in-memory lists (already loaded from JSON).
3. **Change `opportunity_type` to `grant` only** — disable investment matching entirely.
4. **Return hard-coded 5 matches** if engine completely fails (emergency fallback).
