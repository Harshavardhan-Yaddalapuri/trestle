# Trestle Financials Module — Build & Deployment Notes

## What changed (minimum viable for demo)
- `ProfileBase` now uses `company_name` (drops legacy `name`, `location`, `demographics`, `goals`).
- `ProfileUpdate` / `ProfileResponse` inherit the new fields.
- `PATCH /api/profiles/me` accepts the new fields (`company_name`, `state`, `stage`, `industry`, `funding_raised`, `years_in_operation`, `funding_need`, `therapeutic_area`, `geographic_pref`, `accelerator_affiliation`, `regulatory_pathway`, `employees`).
- `GET /api/profiles/onboarding-steps` returns the new **8-step onboarding** per the design spec.
- Added `seed_investments.json` (3 medtech VCs/funds) and wired it into `matching_engine.py` auto-seed on startup.
- Existing `seed_grants.json` and `seed_rules.json` remain untouched.
- No auth or search routers were modified.

## Supabase migration
1. Open your Supabase project > SQL Editor > New query.
2. Paste the contents of `docs/SUPABASE_MIGRATION.sql`.
3. Click **Run**. All changes are idempotent (`IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`).

### Columns added to `profiles`
- `company_name`
- `funding_raised`
- `years_in_operation`
- `accelerator_affiliation`
- `therapeutic_area`
- `geographic_pref`
- `regulatory_pathway`
- `employees`

### Tables created if missing
- `grants`
- `investment_opportunities`
- `eligibility_rules`
- `matches`

## Seed investment data
Startup auto-seeds `seed_investments.json` via the FastAPI lifespan event in `main.py`. To seed manually:

```bash
cd /Users/harshavardhan/trestle/backend
python -c "
from app.database import supabase
import json
with open('app/data/seed_investments.json') as f:
    data = json.load(f)
res = supabase.table('investment_opportunities').insert(data).execute()
print('Inserted', len(res.data or []), 'investment opportunities')
"
```

## API test endpoints
Onboarding steps:
```bash
curl http://localhost:8000/api/profiles/onboarding-steps
```

Profile upsert (PATCH) — example payload:
```json
{
  "company_name": "Acme Biomed",
  "state": "Michigan",
  "stage": "seed",
  "industry": ["medtech", "biotech"],
  "years_in_operation": 1,
  "funding_raised": 250000,
  "funding_need": "750000",
  "accelerator_affiliation": "Techstars"
}
```

Matches for a seeded profile:
```bash
curl "http://localhost:8000/api/matching/matches?profile_id=<profile-uuid>&opportunity_type=all"
```

Health checks:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/matching/health
```

## Re-start locally after changes
```bash
cd /Users/harshavardhan/trestle/backend
pip install -r requirements.txt   # if new deps were added
uvicorn app.main:app --reload
```
