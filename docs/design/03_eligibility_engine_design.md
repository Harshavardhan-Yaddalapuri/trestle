# Eligibility Engine Design

## 1. Python Module Structure

```
backend/app/services/
├── __init__.py
├── matching_engine.py          # Orchestrator: seed_data(), maybe thin wrapper
└── eligibility_engine.py       # Core deterministic evaluator (NEW)
```

Inside `eligibility_engine.py`:

```text
┌────────────────────────────────────────────────────────┐
│  eligibility_engine.py                                   │
│  ┌─────────────────┐  ┌──────────────────────┐         │
│  │ _normalize()    │  │ _apply_operator()    │         │
│  │ (type coercion) │  │ (eq/ne/gte/…/between)│         │
│  └────────┬────────┘  └──────────┬──────────┘         │
│           │                       │                      │
│  ┌────────▼──────────────────────▼────────┐           │
│  │ evaluate_opportunity(profile, opp, rules) │           │
│  │ → (score: int, rationale_items: list)    │           │
│  └────────┬─────────────────────────────────┘           │
│           │                                              │
│  ┌────────▼─────────────────────────────────┐           │
│  │ rank_matches(profile, grants, invs, …)  │           │
│  │ → top_matches ≤ 5 + freshness_timestamp │           │
│  └─────────────────────────────────────────┘            │
└────────────────────────────────────────────────────────┘
```

---

## 2. Rule Loading from `eligibility_rules` Table

Each call to `GET /matches` does **one lightweight** query:

```python
rules_res = (
    supabase
    .table("eligibility_rules")
    .select("*")
    .eq("is_active", True)
    .execute()
)
rules: List[Dict] = rules_res.data or []
```

Because there are < 50 rules in MVP, we load **all active rules into memory** and filter by `rule_type` in Python. This eliminates per-table round-trips and keeps latency < 2s.

**Future optimization:** add `.eq("rule_type", "grant")` or `"investment"` depending on query to reduce payload size.

---

## 3. Match Scoring Logic (`confidence_score`)

For each profile × opportunity pair:

1. **Initialize** `score = 0`, `rationale = []`.
2. **Iterate rules** (pre-sorted by `priority ASC`).
3. **Skip** inactive rules or rules where `rule_type != opportunity_type`.
4. **Extract values:**
   - `prof_val = profile[rule.field_name]` (may be `None`)
   - `opp_val  = opportunity[rule.field_name]` (may be `None`)
5. **Evaluate `_apply_operator(operator, prof_val, opp_val, value_str, value_num)`**.
6. **If `matched`:**
   - `score += rule["points"]`
   - `rationale.append(rule["description"] or rule["name"])`
7. **After all rules:** opportunity is a candidate if `score > 0`.

### Operator Matrix (`_apply_operator`)

| Operator | Direction | Example | Logic |
|----------|-----------|---------|-------|
| `eq` | profile == rule value | `stage == "seed"` | `_normalize(profile_val) == _normalize(rule_value)` |
| `ne` | profile != rule value | `industry != "saas"` | negation of `eq` |
| `gte` | profile ≥ rule value | `funding_raised ≥ 0` | numeric cast, False on non-numeric |
| `lte` | profile ≤ rule value | `years_in_operation ≤ 5` | numeric cast, False on non-numeric |
| `in` | profile value is inside rule set | `stage in [seed, pre-seed]` | list-contains; string fallback |
| `contains` | rule value is inside profile set (or vice versa) | `industry_focus contains "medtech"` | symmetric substring / list overlap |
| `between` | profile inside numeric range | `ticket between 250000,2000000` | parse `rule.value_str` as two numbers |

### Special Handling for Multi-Valued Strings

Fields like `industry_focus`, `stage_eligible`, `therapeutic_focus` are stored as comma-separated strings (`"biotech,medtech"`).

`_normalize()` always splits on `,`, strips whitespace, and lower-cases. This makes `contains` and `in` work without JSONB arrays.

---

## 4. Rationale String Generation

Current logic (skeleton) concatenates with `" | "`:

```python
rationale = " | ".join(rationale_items) if rationale_items else "Passed basic eligibility"
```

**For the demo, we want human-readable sentences.** Upgrade to:

```python
_RULE_FRIENDLY = {
    "Stage Match": "Company stage fits the opportunity's target stages",
    "Funding Raised Ceiling": "Current funding raised is below the maximum allowed",
    "Years in Operation Ceiling": "Company is younger than the age cutoff",
    "Industry Alignment": "Industry focus overlaps with the opportunity",
    "Therapeutic Area Overlap": "Therapeutic area matches the opportunity's focus",
}

def build_rationale(items: List[str]) -> str:
    friendly = [f"✓ {_RULE_FRIENDLY.get(i, i)}" for i in items]
    return "; ".join(friendly)
```

**Example output:**
```
✓ Company stage fits the opportunity's target stages;
✓ Current funding raised is below the maximum allowed;
✓ Industry focus overlaps with the opportunity
```

If `rationale_items` is empty but the opportunity made it through (shouldn’t happen with deterministic scoring), fallback to `"Passed basic eligibility"`.

---

## 5. Edge Case Handling

### 5.1 Missing / Null Profile Fields

| Scenario | Behavior |
|----------|----------|
| `funding_raised` not provided | Schema default is `0`; engine treats as `0`. Rule `funding_raised ≤ 500000` **passes**.
| `therapeutic_area` is `None` | `contains` → `False`. That rule contributes no points, but other rules can still score. |

### 5.2 Rule Explosion / Crash

Wrapped in `try/except` per rule:

```python
try:
    matched = _apply_operator(...)
except Exception:
    matched = False   # skip broken rule, keep evaluating
```

This fulfills the LLD requirement: *"Rule engine crash by malformed data → that opportunity skipped (never fails entire API)"*.

### 5.3 Stale Data Fallback

`matches` table acts as a cache:

```python
from datetime import datetime, timezone, timedelta

STALE_THRESHOLD = timedelta(hours=48)

def try_cached(profile_id: str):
    row = (
        supabase.table("matches")
        .select("*")
        .eq("profile_id", profile_id)
        .order("confidence_score", desc=True)
        .limit(5)
        .execute()
    )
    if row.data:
        freshest = max(datetime.fromisoformat(r["freshness_timestamp"]) for r in row.data)
        if datetime.now(timezone.utc) - freshest < STALE_THRESHOLD:
            return {"degraded": False, "matches": row.data}
    return None
```

**Fallback chain:**
1. Attempt live evaluation.
2. If live evaluation throws → return last good cache (set `degraded=True`).
3. If cache empty → return `HTTP 503` with message `"Unable to generate matches at this time"`.

### 5.4 No Matches

`GET /matches` returns:

```json
{
  "profile_id": "...",
  "total_matches": 0,
  "degraded": false,
  "freshness_timestamp": "2026-05-22T...",
  "matches": []
}
```

Do **not** return 404. 200 with an empty array is correct.

---

## 6. Performance Budget (< 2s)

| Step | Time Budget | Notes |
|------|-------------|-------|
| Fetch profile | ~80 ms | Single-row PK lookup |
| Fetch rules | ~80 ms | Small table; Supabase edge-caches |
| Fetch grants + investments | ~150 ms | `eq(is_active, True)` uses index |
| Evaluate all pairs | ~200 ms | 10 grants × 5 rules + 2 investments × 5 rules ≈ 60 iterations |
| Sort + slice | ~5 ms | Python in-memory |
| Optional cache write | ~100 ms | Best-effort async background insert (can be skipped for latency) |
| **Total** | **≈ 615 ms** | Well under 2s |

**Tip:** If latency spikes, add `limit=200` on grants/investments query to cap dataset size; then paginate post-matching.
