# Trestle Financials — State & API Integration Notes (Stage 3)

## 1. New / Changed API Contract

### 1.1 `POST /api/profiles` (Upsert Profile)
**Where it is called:** `onboarding/page.tsx` → final step submission.

**Current body sent:**
```json
{
  "name": "...",
  "location": "...",
  "state": "...",
  "stage": "...",
  "industry": ["..."],
  "funding_need": "...",
  "goals": "..."
}
```

**New body sent:**
```json
{
  "company_name": "...",
  "state": "...",
  "stage": "...",
  "industry": "...",
  "years_in_operation": 1,
  "funding_raised": 250000,
  "funding_need": 750000,
  "accelerator_affiliation": "..."
}
```

**Changes required:**
- Rename `name` → `company_name`
- Drop `location` (replaced by `state` select)
- Drop `goals` (not used by eligibility engine)
- `industry` now sent as comma-separated string OR array — confirm with backend contract.
- `funding_need` now sent as **integer** (USD) not free text.
- Add `years_in_operation` (integer), `funding_raised` (integer), `accelerator_affiliation` (string | null).

---

### 1.2 `GET /api/matches` (New Endpoint)
**Where it is called:** `app/dashboard/financials/page.tsx` (new page) and on Refresh CTA.

```http
GET /api/matches?profile_id={uuid}&opportunity_type=all&limit=5
Authorization: Bearer {supabase_token}
```

**Expected response (200):**
```json
{
  "profile_id": "uuid",
  "total_matches": 4,
  "degraded": false,
  "freshness_timestamp": "2026-05-22T10:00:00Z",
  "matches": [
    {
      "opportunity_id": "uuid",
      "opportunity_type": "grant",
      "title_or_fund": "NIH R01 Research Grant",
      "confidence_score": 95,
      "rationale": "Eligible because you’re pre-Series A, in medtech, less than 2 years post-accelerator, and seeking ≤ $1M.",
      "source_url": "https://grants.nih.gov/...",
      "funding_min": 250000,
      "funding_max": 1000000,
      "deadline": "2026-08-15"
    }
  ]
}
```

**Key fields consumed by frontend:**
- `total_matches` → hero headline
- `degraded` → error banner
- `freshness_timestamp` → relative time under hero + freshness badge per card
- `matches[].confidence_score` → badge text & color variant
- `matches[].rationale` → rationale paragraph
- `matches[].source_url` → CTA link
- `matches[].funding_min` / `funding_max` → amount range
- `matches[].deadline` → date + urgency styling

---

### 1.3 `GET /api/matches` (Fallback / Expanded)
**Called when user clicks "Show 3 lower-confidence matches":**
```http
GET /api/matches?profile_id={uuid}&opportunity_type=all&limit=8&min_confidence=40
```

**Client-side behavior:** Already-fetched top-5 are deduplicated; append the next 3 below an accordion divider.

---

## 2. Data Flow Diagram

```
┌──────────────┐     ┌──────────────────────────┐     ┌─────────────────┐
│   ONBOARDING │     │        BACKEND           │     │   DASHBOARD     │
│   (8 steps)  │────▶│  POST /api/profiles      │────▶│  /dashboard/    │
│              │     │  (stores profile + new     │     │  financials     │
│  Payload:    │     │   3 fields)              │     │                 │
│  company_name│     └──────────────────────────┘     │  GET /api/      │
│  state       │                           │          │  matches        │
│  stage       │                           │          │                 │
│  industry    │                           ▼          │  Renders:       │
│  years_op    │                ┌──────────────────┐  │  hero, cards,   │
│  funding_    │                │ Eligibility      │  │  empty, error   │
│   _raised    │◄──────────────│ Engine (rules)   │  │                 │
│  funding_need│   runs rules   │                  │  │                 │
│  accel_affil │   on profile   │  Outputs:        │  │                 │
└──────────────┘                │  scored matches  │  └─────────────────┘
                                │  (confidence,    │
                                │   rationale)       │
                                └──────────────────┘
```

**Session-level state:**
1. Onboarding stores answers in local `useState` (unchanged).
2. On completion, POST body includes all 8 fields.
3. Backend returns `profile_id` in response (or frontend already knows it from Supabase `user.id`).
4. Dashboard `financials` page calls `GET /api/matches?profile_id=...` on mount + whenever user hits Refresh.

---

## 3. Component / Page Impact Matrix

| File | Change Type | Notes |
|------|-------------|-------|
| `app/onboarding/page.tsx` | **Major refactor** | Rewrite `STEPS` array (8 steps), change input types, drop `goals`, combine `location` + `state`, add 3 new fields, update POST body shape. |
| `app/dashboard/page.tsx` | **Add navigation** | Add "Financials" tab to sidebar; keep chat view as default "Dashboard". |
| `app/dashboard/financials/page.tsx` | **New file** | Consumes `GET /api/matches`; renders hero, cards, empty state, error banner. |
| `app/lib/supabase.ts` | **No change** | Auth layer remains identical. |
| `app/page.tsx` (landing) | **No change** | Login CTA already routes to `/login`. |
| `app/login/page.tsx` | **No change** | Post-login redirect to `/onboarding` if profile incomplete; already handled. |

---

## 4. Loading Skeleton Specification

**Rule:** No spinners. Use skeleton placeholder shapes that mirror the final layout.

### 4.1 Onboarding Skeleton
Not needed — each step is single-field with instant transition animation.

### 4.2 Dashboard Financials Skeleton
Rendered while `GET /api/matches` is in flight.

```
┌─────────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  [████████████████████████  skeleton headline  ███████████] │   │
│  │  [█████████ skeleton subline ███████]  [░░░░░░░░░░░░░░░░░] │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  [░░░░░░] [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]│   │
│  │  [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] │   │
│  │  [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] │   │
│  │  [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] │   │
│  │  [░░░░░░░░░░░░░░]  [░░░░░░░░░░░░░░░░░░]                    │   │
│  │  [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  (repeat 3× for card placeholders)                                  │
└─────────────────────────────────────────────────────────────────────┘
```

**Implementation notes:**
- Use `bg-surface-container` with a subtle `animate-pulse`.
- Skeleton headline: `h-8 w-64 rounded-md`.
- Skeleton card: full-width `h-48 rounded-2xl` with internal gaps matching real card padding.
- **Minimum skeleton display time:** 400 ms to prevent jarring flash — even if API is fast.
- If cached data exists from a previous session, show cached cards **behind** a semi-transparent skeleton overlay and swap in fresh data on arrival (avoids blank-screen flicker).

---

## 5. Error Boundary Strategy

### 5.1 Error Types & UX

| Error | Origin | UX |
|-------|--------|-----|
| **Engine unreachable** | `GET /api/matches` 500 / timeout | Render degraded banner + cached cards (if any). If no cache → fallback to empty state with retry CTA. |
| **Profile not found** | `GET /api/matches` 404 | Redirect to `/onboarding` with a toast: "We need a bit more info to find your matches." |
| **Network failure** | `navigator.onLine === false` | Inline banner: "You’re offline. Showing last saved results." Disable Refresh button. |
| **Unexpected runtime** | React render error | `error.tsx` in `app/dashboard/financials/` — generic "Something went wrong" with reload button. |

### 5.2 Next.js Error Boundary Placement

```
app/
  dashboard/
    financials/
      page.tsx          ← main UI
      loading.tsx       ← skeleton (optional Next.js async convention)
      error.tsx         ← catchesrender / fetch errors in this segment
  dashboard/
    error.tsx           ← fallback for dashboard-level crashes
```

**`error.tsx` spec (financials):**
- `use client` directive
- Accepts `{ error, reset }: { error: Error; reset: () => void }`
- Renders `AlertTriangle` icon + "Couldn’t load your matches." + "Try again" button calling `reset()`
- Log error details to console (Sentry integration later)

### 5.3 React Query / SWR (Recommended)

If the team adopts a data-fetching library before Tuesday:

```typescript
// SWR pattern
const { data, error, isLoading, mutate } = useSWR(
  `/api/matches?profile_id=${profileId}`,
  fetcher,
  { revalidateOnFocus: false, dedupingInterval: 60000 }
);
```

This gives stale-while-revalidate behavior for free — matches stay visible during background refetch.

---

## 6. New Profile Schema Fields (Supachtre / Postgres)

Ensure these columns exist in the `profiles` table:

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `funding_raised` | `bigint` | `false` | `0` |
| `years_in_operation` | `smallint` | `false` | `0` |
| `accelerator_affiliation` | `text` | `true` | `null` |

If the backend is using a JOINed view or different table, the onboarding POST body MUST still include these fields so the eligibility engine receives them.
