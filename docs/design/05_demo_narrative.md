# Trestle Financials — Demo Narrative (Tuesday)

## The Walk-Through (1 minute, 15 seconds)

> *"This is how we’d walk through it live on Tuesday."*

**1. Welcome & Onboarding (30 sec)**
– After signing in, the founder lands on the new 8-step onboarding. We ask just *eight* structured questions: company name, state, stage, industry, years in operation, funding raised so far, how much they need, and accelerator affiliation. Notice we dropped the free-text "goals" question—eligibility is rule-based, so we only collect fields the engine can actually use.

**2. Personalized Match Dashboard (20 sec)**
– On submit we hit `POST /api/profiles`, store the new fields, and immediately redirect to `/dashboard/financials`. The hero reads *"4 grants matched for Acme Biomed"* with a freshness timestamp and a Refresh button. This doesn’t feel like a search-results page—it feels like *their* page.

**3. Match Cards (20 sec)**
– Each match card surfaces the opportunity title, a confidence badge, a one-sentence rationale explaining *why it fits this exact profile* (e.g. *"Eligible because you’re pre-Series A, in medtech, less than 2 years post-accelerator, and seeking ≤ $1M"*), the amount range, the deadline, and a direct source CTA. If the engine is temporarily unreachable, we show a clear *"Results may be stale"* banner above cached cards rather than a blank screen.

**4. Empty & Error Resilience (5 sec)**
– If no grants match, the empty state says *"No eligible grants found—we’ll notify you when new ones open"* with a manual retry. Because we skeleton-load the real layout instead of a spinner, the UI never feels broken.
