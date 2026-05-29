# Trestle Financials — Onboarding Flow Redesign (Stage 3)

## Goal
Capture the 3 new eligibility-critical fields (`funding_raised`, `years_in_operation`, `accelerator_affiliation`) while keeping the flow ≤ 8 steps and minimizing friction.

---

## Existing 7 Steps vs. New 8 Steps

| # | OLD FIELD | ACTION | # | NEW FIELD | INPUT TYPE | WHY KEPT / CHANGED |
|---|-----------|--------|---|-----------|------------|-------------------|
| 1 | `name` | **KEEP** | 1 | `company_name` | text | Identity for personalization |
| 2 | `location` | **COMBINE w/ state** | 2 | `state` | select (dropdown) | Single-step geography; medtech grants are state-gated |
| 3 | `state` | **COMBINED into #2** | — | — | — | Removed as separate step |
| 4 | `stage` | **KEEP** | 3 | `stage` | select (cards) | Core eligibility filter |
| 5 | `industry` | **KEEP** | 4 | `industry` | multi-select chips | Needed for industry-keyword matching |
| — | — | **NEW** | 5 | `years_in_operation` | number input (0-100) | Core eligibility: many grants cap at < 2 yrs |
| — | — | **NEW** | 6 | `funding_raised` | currency input (USD) | Core eligibility: raised > $X disqualifies |
| 6 | `funding_need` | **KEEP** | 7 | `funding_need` | currency input (USD) | Used for amount-range matching |
| — | — | **NEW** | 8 | `accelerator_affiliation` | select + "Other" | Some grants require accelerator backing |
| 7 | `goals` | **DROP** | — | — | — | Free-text goals are not used by the eligibility engine; defer to profile-edit later |

**Result:** 10 old fields → 8 new steps (combined 2, dropped 1).

---

## Step-by-Step Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 1                    STEP 2                    STEP 3             │
│  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐      │
│  │ Company name │   →    │ State        │   →    │ Stage        │      │
│  │ [____text___]│         │ [v select v] │         │ [• Idea     ]│      │
│  │              │         │ MI / IL / OH │         │ [• Pre-rev  ]│      │
│  │              │         │ WI / Other   │         │ [• Seed     ]│      │
│  └──────────────┘         └──────────────┘         │ [• Series A]│      │
│                                                    └──────────────┘      │
│  STEP 4                    STEP 5                    STEP 6             │
│  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐      │
│  │ Industry     │   →    │ Years in     │   →    │ Funding      │      │
│  │ [chip chips] │         │ operation    │         │ raised (USD) │      │
│  │ medtech □    │         │ [ 0–100 #  ] │         │ [ $ ____ # ] │      │
│  │ biotech □    │         │              │         │              │      │
│  │ digi-hlth □  │         └──────────────┘         └──────────────┘      │
│  └──────────────┘                                                        │
│  STEP 7                    STEP 8 (FINAL)                               │
│  ┌──────────────┐         ┌────────────────────────────────────┐      │
│  │ Funding need │   →    │ Accelerator affiliation            │      │
│  │ (USD)        │         │ [v select v]                       │      │
│  │ [ $ ____ # ] │         │ YC / Techstars / J&J / None / Other│      │
│  └──────────────┘         └────────────────────────────────────┘      │
│                                                                         │
│  → POST /api/profiles  →  redirect /dashboard/financials               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Step Order Rationale (Minimum Friction)

| Order | Field | Placement Logic |
|-------|-------|-----------------|
| 1 | `company_name` | Warm, human start — feels like a conversation, not a form. |
| 2 | `state` | Quick win (single tap); immediately unlocks state-filtered matches. |
| 3 | `stage` | Second quick tap; narrows universe of grants dramatically. |
| 4 | `industry` | Chips let users multi-select fast; by now they trust the flow. |
| 5 | `years_in_operation` | First numeric input; small integer = low cognitive load. |
| 6 | `funding_raised` | USD currency; input-masking (`$`) makes it feel polished. |
| 7 | `funding_need` | Pair with #6 mentally — "what you have → what you need". |
| 8 | `accelerator_affiliation` | Final step; only relevant to some, so placing it last avoids drop-off for non-accelerator founders. "None" is a first-class option. |

**Key UX principle:** Move from identity (1) → fast filters (2–3) → more detailed eligibility (4–6) → goal-oriented (7) → niche qualifier (8).

---

## Input Specifications

| Field | UI Pattern | Validation | Keyboard / Mobile |
|-------|-----------|------------|-----------------|
| `company_name` | Single-line text, max 255, auto-capitalize first letter | Required, non-empty | Text keyboard, auto-focus |
| `state` | Bottom-sheet / native select (5 options) | Required | Tap-to-open, no typing |
| `stage` | 5 large tappable cards, single-select | Required | Tap |
| `industry` | Horizontal scroll chips, multi-select (max 3) | At least 1 | Tap to toggle |
| `years_in_operation` | Number spinner 0–100, default 0 | Integer ≥ 0 | Number pad |
| `funding_raised` | Currency input with `$` prefix, comma formatting | Integer ≥ 0 | Number pad |
| `funding_need` | Same as above | Integer ≥ 0 | Number pad |
| `accelerator_affiliation` | Select dropdown + "Other" reveals text input | Optional (nullable) | Tap, then text if Other |

---

## Data Payload (POST /api/profiles)

```json
{
  "company_name": "Acme Biomed",
  "state": "Michigan",
  "stage": "seed",
  "industry": ["medtech", "biotech"],
  "years_in_operation": 1,
  "funding_raised": 250000,
  "funding_need": 750000,
  "accelerator_affiliation": "Techstars"
}
```

**Dropped `goals`:** Not sent to API. If profile-edit page is added later, `goals` can be a free-text textarea there.

---

## Progress Bar

- Show "Step N of 8" centered under the brand wordmark.
- Thin segmented bar (8 segments) fills left-to-right with `primary` color.
- Animate width with `transition-all duration-300` on every `next()`.

---

## Error Handling per Step

| Scenario | UX |
|----------|-----|
| Empty required field | "Next" button disabled; inline helper text: "Required to find your matches." |
| Invalid number (e.g. negative) | Shake input + red ring; block advance |
| API 500 on final submit | Inline toast: "Couldn’t save profile. We’ll retry automatically." + retry count (max 3) |
| Network offline on submit | Same toast, but add "You can continue — we’ll sync when you’re back online." |
