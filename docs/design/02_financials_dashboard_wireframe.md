# Trestle Financials — Dashboard Wireframe Spec (Stage 3)

## Route
`/dashboard/financials` (new tab inside the existing `/dashboard` layout)

## High-Level Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TRESTLE          Dashboard  |  Financials  |  Search History            🔍  │
│  ─────────  (sidebar tabs — Financials is NEW, highlighted when active)       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ╔═══════════════════════════════════════════════════════════════════════╗│
│  ║  HERO SECTION (max 120 px height)                                      ║│
│  ║                                                                        ║│
│  ║   4 grants matched for Acme Biomed                                      ║│
│  ║   Last checked 2 hours ago      [ 🔄 Refresh matches ]                ║│
│  ║                                                                        ║│
│  ╚═══════════════════════════════════════════════════════════════════════╝│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  MATCH CARD #1  (max 5 cards, vertical stack, gap-4)               │  │
│  │                                                                     │  │
│  │  ┌─────────────────────────────────────────────────────────────┐   │  │
│  │  │ 🔬 NIH R01 Research Grant                                    │   │  │
│  │  │                                                              │   │  │
│  │  │  [GRANT]  [95% MATCH]  [FRESH — 2h ago]                     │   │  │
│  │  │                                                              │   │  │
│  │  │  Eligible because you’re pre-Series A, in medtech,         │   │  │
│  │  │  less than 2 years post-accelerator, and seeking ≤ $1M.    │   │  │
│  │  │                                                              │   │  │
│  │  │  ─────────────────────────────────────────────────────────   │   │  │
│  │  │  💰 $250K – $1M        ⏰ Closes Aug 15, 2026                │   │  │
│  │  │  ─────────────────────────────────────────────────────────   │   │  │
│  │  │  [ View on NIH.gov → ]                                      │   │  │
│  │  └─────────────────────────────────────────────────────────────┘   │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  (Cards 2–5 repeat the same pattern; max 5 total)                           │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                               [ + Show 3 lower-confidence matches ] │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ───────────────────────  EMPTY STATE  ───────────────────────              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                                                                     │  │
│  │                       📭                                            │  │
│  │                                                                     │  │
│  │        No eligible grants found                                     │  │
│  │        We’ll notify you as soon as new ones open.                 │  │
│  │                                                                     │  │
│  │        [ ⚡ Check again now ]                                      │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ───────────────────────  ERROR / DEGRADED STATE  ────────────────────       │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  ⚠️  Results may be stale                                           │  │
│  │                                                                     │  │
│  │  Our eligibility engine is temporarily unreachable.               │  │
│  │  We’re showing cached matches from [timestamp].                     │  │
│  │                                                                     │  │
│  │  [ Retry connection ]                                              │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Anatomy

### 1. Hero Section

| Element | Content | Style |
|---------|---------|-------|
| Match count headline | "{N} grants matched for {company_name}" | `text-2xl font-bold` |
| Freshness line | "Last checked {relative_time} ago" | `text-sm text-on-surface-variant` |
| Refresh CTA | "Refresh matches" pill button | `outlined` variant, right-aligned |

**Responsiveness:** On mobile < 640 px, stack vertically (headline top, button below).

---

### 2. Match Card

Each card is a self-contained vertical block with `rounded-2xl bg-surface-container p-5 ring-1 ring-outline-variant/30`.

| Sub-element | Data Source | UI Treatment |
|-------------|-------------|--------------|
| **Title** | `match.title_or_fund` | `font-semibold text-on-surface` |
| **Type badge** | `match.opportunity_type` (grant | investment) | `rounded-full bg-primary-container text-on-primary-container` (leftmost) |
| **Confidence badge** | `match.confidence_score` mapped to % | `rounded-full bg-success-container text-on-success-container` if > 75%; `bg-warning-container` if 50–75%; omitted if < 50% |
| **Freshness badge** | `freshness_timestamp` → relative time | `rounded-full bg-surface-high text-on-surface-variant` with a 🕒 icon |
| **Rationale paragraph** | `match.rationale` | `text-sm text-on-surface-variant` inside a tinted `bg-surface-high` inner box |
| **Amount range** | `match.funding_min` – `match.funding_max` | 💰 + formatted currency |
| **Deadline** | `match.deadline` | ⏰ + formatted date; if within 14 days → `text-error` with urgent styling |
| **Source CTA** | `match.source_url` | Text link with external-link icon; opens in `_blank` |

**Card hover state:** Subtle `ring-2 ring-primary/30` on desktop hover.

---

### 3. Empty State

Rendered only when `total_matches === 0` AND `degraded === false`.

- Icon: `Inbox` from lucide-react, `h-12 w-12 text-on-surface-variant`
- Headline: "No eligible grants found"
- Subline: "We'll notify you when new ones open"
- Action: "Check again now" outlined button (triggers a fresh `GET /matches` call)

**Note:** The empty state must NOT feel like a dead end. The CTA gives the user agency.

---

### 4. Error / Degraded State

Rendered when `degraded === true` OR API returns 5xx.

- Icon: `AlertTriangle` from lucide-react, `h-6 w-6 text-warning`
- Headline: "Results may be stale"
- Body: "Our eligibility engine is temporarily unreachable. We're showing cached matches from {timestamp}."
- Action: "Retry connection" button (triggers `GET /matches` with cache-bypass header)

**Important:** Even when degraded, still render any cached match cards below the banner so the user doesn’t hit a blank screen.

---

## Grid / Spacing Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `page-padding` | `px-6 py-6` | Outer content padding |
| `max-content-width` | `max-w-3xl` | Centered column (same as chat range) |
| `card-gap` | `gap-4` | Vertical space between cards |
| `card-padding` | `p-5` | Internal card padding |
| `card-radius` | `rounded-2xl` | Card corners |
| `badge-gap` | `gap-2` | Horizontal gap between badges |

---

## Interactions

| Interaction | Behavior |
|-------------|----------|
| **Card click (non-CTA area)** | No-op (avoid accidental navigation) |
| **Source CTA click** | Opens `source_url` in new tab; records outbound click event (future) |
| **Refresh button** | Disables button, shows skeleton, re-fetches `GET /matches`, re-renders |
| **Show lower-confidence** | Expands inline accordion with 3 additional cards (confidence 40–75%); lazy-fetched via `GET /matches?min_confidence=40` |
