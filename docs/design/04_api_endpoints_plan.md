# API Endpoints Plan

## How to Read This Doc

- 🔧 = existing endpoint requiring changes  
- 🆕 = net-new endpoint  
- ✅ = already exists, verify only

---

## 1. 🔧 POST `/api/profiles/me`

### What to Change
- Add three new required fields to the request payload: `funding_raised`, `years_in_operation`, `accelerator_affiliation`.
- Also accept `company_name`, `therapeutic_area`, `geographic_pref`, `regulatory_pathway`, `employees` (as already present in schema). 

### Request Shape

```json
{
  "name": "Acme Medtech",
  "location": "Boston, MA",
  "company_name": "Acute Diagnostics Inc.",
  "industry": ["medtech"],
  "stage": "seed",
  "funding_raised": 150000,
  "years_in_operation": 1,
  "accelerator_affiliation": "Y Combinator",
  "therapeutic_area": "cardiovascular",
  "geographic_pref": "US",
  "regulatory_pathway": "510(k)",
  "funding_need": "500000",
  "goals": "FDA clearance and first clinical pilot"
}
```

> Only fields sent are updated (`exclude_unset=True`).  
> Validation: `funding_raised` / `years_in_operation` must be `int ≥ 0`. `accelerator_affiliation` may be `null`.

### Response Shape (200)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "...",
  "name": "Acme Medtech",
  "location": "Boston, MA",
  "company_name": "Acute Diagnostics Inc.",
  "industry": ["medtech"],
  "stage": "seed",
  "funding_raised": 150000,
  "years_in_operation": 1,
  "accelerator_affiliation": "Y Combinator",
  "therapeutic_area": "cardiovascular",
  "geographic_pref": "US",
  "regulatory_pathway": "510(k)",
  "funding_need": "500000",
  "goals": "FDA clearance and first clinical pilot",
  "created_at": "2026-05-20T12:00:00Z",
  "updated_at": "2026-05-22T08:00:00Z"
}
```

### Error Codes

| Code | When |
|------|------|
| `400 VALIDATION_ERROR` | Missing required field or `funding_raised < 0` |
| `401 AUTHENTICATION_REQUIRED` | No valid Supabase JWT |
| `404 NOT_FOUND` | Profile does not exist for authenticated user |
| `500 INTERNAL_ERROR` | Supabase row update failed |

---

## 2. 🆕 GET `/api/matches`

### Request

```text
GET /api/matches?profile_id=<uuid>&opportunity_type=all
```

Query params:

| Param | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `profile_id` | UUID | **Yes** | — | Which profile to match against |
| `opportunity_type` | string | No | `all` | Enum: `grant`, `investment`, `all` |

### Response Shape (200)

```json
{
  "profile_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_matches": 4,
  "degraded": false,
  "freshness_timestamp": "2026-05-22T07:55:00Z",
  "matches": [
    {
      "opportunity_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "opportunity_type": "grant",
      "title_or_fund": "NIH SBIR Phase I",
      "confidence_score": 6,
      "rationale": "✓ Company stage fits the opportunity's target stages; ✓ Current funding raised is below the maximum allowed; ✓ Industry focus overlaps with the opportunity",
      "source_url": "https://sbir.nih.gov/"
    },
    {
      "opportunity_id": "b2c3d4e5-f6a7-8901-bcde-f23456789012",
      "opportunity_type": "investment",
      "title_or_fund": "Healthtech Capital",
      "confidence_score": 5,
      "rationale": "✓ Investment stage alignment; ✓ Geographic preference fits; ✓ Industry focus overlaps",
      "source_url": "https://www.healthtechcapital.com/"
    }
  ]
}
```

### Invariants Enforced by API Layer
- `total_matches ≤ 5` (hard slice after sorting by `confidence_score DESC`).
- Every item has non-empty `rationale`.
- `freshness_timestamp` = `MAX(profile.updated_at, opportunity.updated_at, rule.updated_at)`.

### Error Codes

| Code | When |
|------|------|
| `400 VALIDATION_ERROR` | Missing `profile_id`, or `opportunity_type` invalid |
| `404 NOT_FOUND` | `profile_id` does not exist |
| `503 DEGRADED` | Engine failed; stale cached results returned with `degraded: true` |
| `500 INTERNAL_ERROR` | Unexpected crash |

---

## 3. 🆕 GET `/api/grants` (Admin / Debug)

### Request

```text
GET /api/grants?is_active=true&source=NIH&limit=20&offset=0
```

Query params:

| Param | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `is_active` | boolean | No | `true` | Filter by active status |
| `source` | string | No | — | e.g., `NIH`, `NSF`, `BARDA` |
| `limit` | integer | No | 50 | Max 200 |
| `offset` | integer | No | 0 | Pagination offset |

### Response Shape (200)

```json
{
  "total": 6,
  "limit": 50,
  "offset": 0,
  "grants": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "title": "NIH SBIR Phase I",
      "source": "NIH",
      "source_url": "https://sbir.nih.gov/",
      "funding_min": 0,
      "funding_max": 500000,
      "deadline": "2026-10-15",
      "industry_focus": "biotech,medtech",
      "stage_eligible": "seed,pre-seed",
      "therapeutic_focus": "general",
      "is_active": true,
      "updated_at": "2026-05-22T06:00:00Z"
    }
  ]
}
```

### Error Codes

| Code | When |
|------|------|
| `400 VALIDATION_ERROR` | `limit > 200` or `offset < 0` |
| `500 INTERNAL_ERROR` | DB unreachable |

---

## 4. ✅ GET `/api/health`

### Current State
Already exists in `main.py`:

```python
@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.3.0"}
```

### Minor Enhancement for Demo Confidence
Add a lightweight DB ping so the health check proves **end-to-end connectivity** to Supabase:

```python
@app.get("/health")
async def health():
    db_ok = True
    try:
        supabase.table("grants").select("id", count="exact").limit(1).execute()
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "version": "0.3.0",
        "db_connected": db_ok,
    }
```

> No breaking change; just an extra `db_connected` boolean in the response.

### Response Shape

```json
{
  "status": "ok",
  "version": "0.3.0",
  "db_connected": true
}
```

### Error Codes

| Code | When |
|------|------|
| `200` | Always (no 500 by design; we swallow DB exceptions) |

---

## 5. Router Wiring (`main.py`)

No new routers needed if you keep using the `/api/matching` prefix:

```python
app.include_router(matching.router, prefix="/api/matching", tags=["matching"])
```

That gives you:
- `POST /api/matching/profiles` (works today)
- `GET  /api/matching/matches` (works today, needs polish)
- `GET  /api/matching/grants` (works today, needs polish)
- `GET  /api/matching/health` (already exists)

If the frontend expects `/api/matches` and `/api/grants`, add aliases:

```python
@app.get("/api/matches")
async def matches_alias(...):
    return await matching.get_matches(...)

@app.get("/api/grants")
async def grants_alias(...):
    return await matching.list_grants(...)
```

---

## 6. Response Consistency Rules

| Field | Rule |
|-------|------|
| `freshness_timestamp` | ISO-8601 UTC string with `Z` or `+00:00` suffix |
| `confidence_score` | Integer ≥ 0 |
| `total_matches` | Integer 0–5 |
| `rationale` | Non-empty string, max ~500 chars |
| `source_url` | Absolute URL if present, else `null` |
| `error_code` | Upper-snake-case string for programmatic handling |
