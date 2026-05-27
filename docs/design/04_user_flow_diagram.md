# Trestle Financials — User Flow Diagram (Stage 3)

## End-to-End Flow

```
                           ┌─────────────────┐
                           │   LANDING PAGE   │
                           │   trestle.io    │
                           └────────┬────────┘
                                    │ [Sign up]
                                    ▼
                           ┌─────────────────┐
                           │   SIGN UP        │
                           │   (Supabase)     │
                           └────────┬────────┘
                                    │ success
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ONBOARDING (8 steps)                            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │
│  │ company │→│  state  │→│  stage  │→│ industry│→│ years   │          │
│  │  name   │  │select   │  │  cards  │  │ chips   │  │in opera-│          │
│  │ [text]  │  │ [dropdown]│  │ [tap]   │  │ [multi] │  │ tion [0]│          │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘          │
│                                                        │                    │
│  ┌─────────┐  ┌─────────┐  ┌─────────────────────────┐ │                    │
│  │ funding │→│ funding │→│ accelerator affiliation│→│ POST                 │
│  │ raised $│  │  need $ │  │ select + Other text    │  │ /api/profiles        │
│  │ [input] │  │ [input] │  │ [dropdown]             │  │                     │
│  └─────────┘  └─────────┘  └─────────────────────────┘ │                    │
└────────────────────────────────────────────────────────┼────────────────────┘
                                                         │
                                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  [loading skeleton]  ──────────────────────────────▶  redirect to           │
│                                                        /dashboard/financials  │
└─────────────────────────────────────────────────────────────────────────────┘

                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DASHBOARD / FINANCIALS TAB                         │
│                                                                             │
│  ┌─────────────────────────────────────────────────┐                        │
│  │  "4 grants matched for Acme Biomed"              │                        │
│  │  "Last checked 2 hours ago"  [Refresh]         │                        │
│  └─────────────────────────────────────────────────┘                        │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  🔬 NIH R01 Grant                                                  │    │
│  │  [GRANT] [95% MATCH] [FRESH — 2h ago]                              │    │
│  │                                                                     │    │
│  │  "Eligible because you’re pre-Series A, in medtech,               │    │
│  │   less than 2 years post-accelerator, and seeking ≤ $1M."          │    │
│  │                                                                     │    │
│  │  💰 $250K – $1M    ⏰ Closes Aug 15, 2026                        │    │
│  │  [ View on NIH.gov → ]                                            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  💰 ARPA-H Investment                                                │    │
│  │  [INVESTMENT] [82% MATCH] [FRESH — 2h ago]                         │    │
│  │  ...                                                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  (up to 5 cards)                                                            │
└─────────────────────────────────────────────────────────────────────────────┘

                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ERROR / DEGRADED BRANCHES                          │
│                                                                             │
│  Engine 500 ──────────▶  ┌─────────────────────────────┐                   │
│  ┌────────────┐          │ ⚠️ Results may be stale    │                   │
│  │ /api/      │──────▶  │ Cached from 6h ago         │                   │
│  │ matches 500│          │ [Retry connection]         │                   │
│  └────────────┘          └─────────────────────────────┘                   │
│                                                                             │
│  Zero matches ──────────▶ ┌─────────────────────────────┐                   │
│  ┌────────────┐          │ 📭 No eligible grants found│                   │
│  │ total=0    │──────▶  │ We'll notify you when new  │                   │
│  │            │          │ ones open. [Check again now]│                   │
│  └────────────┘          └─────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Auth → Onboarding → Dashboard Gate

```
┌─────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Login  │─────▶│  Check profile   │─────▶│  /dashboard     │
│  done   │      │  completeness    │      │  (default view) │
└─────────┘      └────────┬────────┘      └────────┬────────┘
                          │ incomplete             │
                          ▼                      ▼
                   /onboarding              user clicks
                                            "Financials" tab
                                                │
                                                ▼
                                         /dashboard/financials
                                         ↓ triggers GET matches
```

## Sidebar Tab Layout (New)

```
┌──────────────────────────────┐
│  TRESTLE                     │
├──────────────────────────────┤
│  📊 Dashboard                │
│  💰 Financials   ←  NEW    │
│  🔍 Search History           │
├──────────────────────────────┤
│  Sign Out                    │
└──────────────────────────────┘
```

- **Dashboard** = existing chat/agent view (`/dashboard`)
- **Financials** = new grant/investment match view (`/dashboard/financials`)
- **Search History** = future feature (unchanged in Stage 3)
