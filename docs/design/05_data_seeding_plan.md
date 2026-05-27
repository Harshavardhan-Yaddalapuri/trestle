# Data Seeding Plan

## 1. Where the Seed Data Comes From

### Grants (already curated)
The repo already contains `backend/app/data/seed_grants.json` with 6 real, high-credibility grants:

| Grant | Source | Real URL |
|-------|--------|----------|
| NIH SBIR Phase I | NIH | https://sbir.nih.gov/ |
| NIH SBIR Phase II | NIH | https://sbir.nih.gov/ |
| Bill & Melinda Gates Foundation Grand Challenges | Gates Foundation | https://gcgh.grandchallenges.org/ |
| NSF SBIR/STTR Phase I | NSF | https://new.nsf.gov/funding/funding-opportunities/sbir |
| BARDA DRIVe TechWatch | BARDA (HHS) | https://www.medicalcountermeasures.gov/ |
| PCORI Funding for Patient-Centered CER | PCORI | https://www.pcori.org/ |

### Investment Opportunities (new)
We hand-curate 3 real medtech/healthcare seed/Series A funds. Data sourced from public Crunchbase profiles, fund websites, and LinkedIn.

| Fund | Type | Ticket (USD) | Stage | Industry Focus | Geo | Source |
|------|------|--------------|-------|----------------|-----|--------|
| **Arboretum Ventures** | VC | $250K – $5M | seed / series-a | medtech, digital health | US | https://arboretumvc.com/ |
| **Healthtech Capital** | Angel / Seed | $100K – $1M | seed / series-a | medtech, digital health | US | https://www.healthtechcapital.com/ |
| **5AM Ventures** | VC | $1M – $15M | series-a / series-b | biotech, medtech | US | https://5am.co/ |

These are anonymized to typical ranges; exact terms change per deal.

---

## 2. How to Populate the Data

### Option A — Built-in auto-seed (preferred for demo)
The existing `matching_engine.py` has `seed_data(supabase_client)`.

What happens on startup:
1. FastAPI lifespan calls `seed_on_startup()`.
2. It checks row counts for `grants` and `eligibility_rules`.
3. If empty, it loads the local JSON files and bulk-inserts via Supabase REST.

We extend this pattern:

```python
def seed_data(supabase_client: Any) -> None:
    # existing grants + rules
    ...
    # NEW: investment opportunities
    inv_check = supabase_client.table("investment_opportunities").select("id", count="exact").limit(1).execute()
    if not (inv_check.count and inv_check.count > 0):
        investments = _load_json(_SEED_INVESTMENTS_PATH)
        if investments:
            supabase_client.table("investment_opportunities").insert(investments).execute()
```

### Option B — Python one-shot script
For manual control:

```bash
cd backend
python -c "
from app.database import supabase
import json
with open('app/data/seed_investments.json') as f:
    data = json.load(f)
supabase.table('investment_opportunities').insert(data).execute()
print('Inserted', len(data), 'investment opportunities')
"
```

### Option C — SQL insert (if skipping JSON)
Use the Dashboard SQL Editor to run hand-written `INSERT` statements.

---

## 3. Pre-Built Seed File: `seed_investments.json`

Create `backend/app/data/seed_investments.json` and load exactly as grants are loaded today.

```json
[
  {
    "fund_name": "Arboretum Ventures",
    "fund_type": "VC",
    "ticket_min": 250000,
    "ticket_max": 5000000,
    "preferred_stage": "seed,series_a",
    "industry_focus": "medtech,digital health",
    "therapeutic_focus": "general",
    "geographic_focus": "US",
    "regulatory_focus": "510(k),PMA",
    "lead_investor": true,
    "is_active": true,
    "source_url": "https://arboretumvc.com/"
  },
  {
    "fund_name": "Healthtech Capital",
    "fund_type": "angel_group",
    "ticket_min": 100000,
    "ticket_max": 1000000,
    "preferred_stage": "seed,series_a",
    "industry_focus": "medtech,digital health",
    "therapeutic_focus": "general",
    "geographic_focus": "US",
    "regulatory_focus": "510(k)",
    "lead_investor": false,
    "is_active": true,
    "source_url": "https://www.healthtechcapital.com/"
  },
  {
    "fund_name": "5AM Ventures",
    "fund_type": "VC",
    "ticket_min": 1000000,
    "ticket_max": 15000000,
    "preferred_stage": "series_a,series_b",
    "industry_focus": "biotech,medtech",
    "therapeutic_focus": "oncology,neurology,rare disease",
    "geographic_focus": "US",
    "regulatory_focus": "PMA,510(k),De Novo",
    "lead_investor": true,
    "is_active": true,
    "source_url": "https://5am.co/"
  }
]
```

### Required Accompanying Rules
To make investments match, add at least the following rules to `seed_rules.json` (or a new `seed_investment_rules.json`):

```json
[
  {
    "name": "Investment Stage Match",
    "description": "Company stage aligns with investor's preferred stage",
    "rule_type": "investment",
    "field_name": "preferred_stage",
    "operator": "in",
    "value_str": "seed,series_a",
    "points": 3,
    "priority": 10
  },
  {
    "name": "Investment Ticket Ceiling",
    "description": "Funding need is within investor's ticket range",
    "rule_type": "investment",
    "field_name": "funding_need",
    "operator": "between",
    "value_str": "100000,15000000",
    "points": 2,
    "priority": 20
  },
  {
    "name": "Investment Industry Alignment",
    "description": "Industry overlaps with investor's focus",
    "rule_type": "investment",
    "field_name": "industry_focus",
    "operator": "contains",
    "value_str": "medtech",
    "points": 2,
    "priority": 30
  }
]
```

---

## 4. Verification Checklist After Seeding

Run the following and expect:

```bash
cd backend
python -c "
from app.database import supabase
print('grants:', len(supabase.table('grants').select('*').execute().data))
print('investments:', len(supabase.table('investment_opportunities').select('*').execute().data))
print('rules:', len(supabase.table('eligibility_rules').select('*').execute().data))
"
```

| Table | Expected Row Count |
|-------|--------------------|
| `grants` | 6 |
| `investment_opportunities` | 3 |
| `eligibility_rules` | 8 (5 grant + 3 investment) |

> If counts are zero, check FastAPI startup logs for seed errors.
