# Trestle — Product Roadmap: Demo to Scale

**Last updated:** 2026-05-22  
**Owner:** Sam (Product)  
**Status:** Draft — pending Arceus approval

---

## Roadmap Principles

1. **Ship 50% in 3 days, not 100% in 3 weeks.** Every milestone has a "minimum lovable demo" and a "polish layer."
2. **No "someday" items.** Every feature has a target date. If the date slips, it goes to the next milestone — it doesn't float.
3. **North Star:** % of users who receive a grant match and apply within 30 days. Every feature must move this or it's cut.
4. **Kill fast.** If a shipped feature doesn't move the North Star within 30 days of launch, it's dead. No attachments.

---

## V0: Demo — "Prove a founder will talk to it" (Target: 2026-06-15)

### Goal
Get one founder (Maurinne Bonnet / Nucleate cohort) to say "this found me a grant I'd have missed" in a single conversation.

### What Ships

| Feature | Why it matters | Owner |
|---------|---------------|-------|
| Conversational grant matching agent (web chat widget) | The core loop: discovery → match → nudge | Floyd (Frontend) + Aurthur (Architect) |
| Curated grant database (~200 grants, medtech-focused) | If the data is wrong, the agent is useless | Jason (Backend) |
| Landing page with "Talk to Trestle" CTA | Zero-friction entry point | Floyd (Frontend) |
| Basic auth (email/pass + Google OAuth) | Remember user across sessions | Jason (Backend) |
| Session memory (conversation history + user profile) | Enables the "nudge" loop later | Aurthur (Architect) |
| Simple match scoring (rules-based eligibility filter) | Hard constraints only; LLM does the reasoning on top | Aurthur (Architect) |

### V0 Success Criteria

| Metric | Baseline | Target | Deadline |
|---|---|---|---|
| Time-to-first-match | 45 min (competitors) | < 5 min | 2026-06-15 |
| Founder says match is relevant (qualitative) | N/A | 1/1 with Maurinne | 2026-06-15 |
| Conversational Q-count to first match | 80+ (forms) | ≤ 5 adaptive Qs | 2026-06-15 |

### V0 Dependencies
- Grant database seeded with 200 entries by 2026-06-08
- LLM provider chosen + latency tested by 2026-06-05
- Landing page domain + hosting by 2026-06-10

### V0 Out of Scope
- Proactive alerts (no cron/scheduler yet)
- Investor matching (v2 feature)
- Batch/cohort dashboard for Maurinne (v2 feature)
- Real-time grant database sync (manual weekly curation)
- Mobile app (web responsive only)

---

## V1: Post-Demo — "Prove they'll come back" (Target: 2026-07-31)

### Goal
Get 50% of users to return within 7 days. Move from "one great conversation" to "ongoing relationship."

### What Ships

| Feature | Why it matters | Owner |
|---------|---------------|-------|
| Full eligibility engine (rules + LLM hybrid) | Reduces false positives; builds trust | Aurthur (Architect) |
| Proactive alerts (new grants, deadline nudges) | Converts one-session novelty into retained usage | Jason (Backend) |
| Grant detail deep-dives (eligibility, deadlines, tips) | Reduces founder's research burden; increases apply rate | Floyd (Frontend) |
| User notification preferences (email, in-app) | Lets founder control the nudge frequency | Jason (Backend) |
| Application tracker ("I'm applying to NIH SBIR" flag) | Keeps the agent informed; improves future matching | Floyd (Frontend) |

### V1 Success Criteria

| Metric | Baseline (post-V0) | Target | Deadline |
|---|---|---|---|
| 7-day retention | N/A | ≥ 50% | 2026-07-31 |
| Proactive alert open rate | 0% | ≥ 30% | 2026-07-31 |
| Grants matched per user per month | 1–2 | ≥ 3 with eligibility rationale | 2026-07-31 |
| User-reported "would apply" rate | N/A | ≥ 25% of matched grants | 2026-07-31 |

### V1 Dependencies
- V0 demo validated by Maurinne (or equiv. Nucleate founder) by 2026-06-20
- LLM cost per conversation under $0.10 by 2026-06-25
- Cron/scheduler infra (Jim, DevOps) by 2026-07-01
- Email delivery service (SendGrid / Resend) by 2026-07-05

### V1 Out of Scope
- Auto-application / form drafting (regulatory risk too high)
- Real-time database sync (still manual weekly curation)
- Multi-industry expansion (stay medtech)
- Investor matching (positioning still "grant intelligence")

---

## V2: Scale — "Prove it works for more than one tribe" (Target: 2026-10-31)

### Goal
Expand beyond medtech to adjacent biotech, healthtech, and deep-tech verticals. Add investor matching as a capital-stack feature (not a positioning pivot). Build the operator dashboard for Maurinne to track her cohort.

### What Ships

| Feature | Why it matters | Owner |
|---------|---------------|-------|
| Multi-industry support (biotech, healthtech, cleantech) | Expands TAM; proves platform thesis | Jason (Backend) + ScoutBot |
| Investor matching (VC/angel introductions, cap-table-aware) | Complements grant matching; "complete capital stack" | Aurthur (Architect) |
| Team collaboration (shared workspace, notes, assign grants) | SaaS pricing tier; B2B revenue stream | Floyd (Frontend) |
| Maurinne's accelerator cohort dashboard | First B2B customer; proves operator value | Floyd (Frontend) |
| Real-time grant database sync (API feeds where available) | Scale demands automation; manual curation breaks | Jason (Backend) |
| Basic analytics (cohort match rates, engagement) | Prove ROI to accelerator operators | Jason (Backend) |

### V2 Success Criteria

| Metric | Baseline (post-V1) | Target | Deadline |
|---|---|---|---|
| Active verticals | 1 (medtech) | ≥ 3 | 2026-10-31 |
| Monthly active users (MAU) | TBD after V1 | ≥ 100 | 2026-10-31 |
| Cohort dashboard adoption (Maurinne + 1 other) | 0 | 2 accelerator partners | 2026-10-31 |
| Investor match → intro conversion | N/A | ≥ 10% | 2026-10-31 |

### V2 Dependencies
- V1 retention ≥ 50% validated by 2026-08-15
- Grant API landscape mapped by ScoutBot by 2026-08-01
- B2B pricing model defined by Sam by 2026-09-01
- Investor database seeded (50+ active medtech investors) by 2026-09-15

### V2 Out of Scope
- Auto-submission (still legal/regulatory risk)
- Mobile native app (still web responsive)
- Multi-language (English only until cohort demand)
- White-label / API product for other accelerators (V3)

---

## Kill Gates

| Milestone | What triggers a kill | What we cut |
|---|---|---|
| **V0 kill gate** (2026-06-20) | Time-to-first-match > 10 min, or Maurinne says "this doesn't help" | Cut proactive alerts (shift to V1), double down on conversation quality |
| **V1 kill gate** (2026-08-15) | 7-day retention < 30%, or alert open rate < 15% | Cut investor matching (was V2 anyway), double down on grant data quality |
| **V2 kill gate** (2026-11-15) | MAU < 50 after 6 weeks, or 0 accelerator partners onboard | Pivot to B2B-only (dashboard for accelerators, kill consumer chat) |

---

## Open Questions & Blockers

| Question | Who answers it | By when |
|---|---|---|
| Does eligibility scoring need a rules engine or can LLM handle it with structured output? | Aurthur | 2026-05-25 |
| Grant database schema — one table or per-program? How do we version rules when NIH changes Phase I caps? | Jason | 2026-05-25 |
| Conversation UI — simple chat or threaded with expandable cards? Design debt of either? | Floyd | 2026-05-25 |
| LLM inference cost per conversation — what's the monthly burn at 100 MAU? | Jim | 2026-05-27 |
| Realistic API landscape for SBIR/NIH/EIC Accelerator — scrape or partner? | ScoutBot | 2026-05-27 |

---

## RICE Priority Refresher

If scope conflicts emerge within a milestone, score by:
- **Reach:** How many users does this touch?
- **Impact:** How much does it move the North Star?
- **Confidence:** How sure are we we can build it in the milestone window?
- **Effort:** Engineering days estimated by Aurthur + Jason + Floyd.

Highest RICE wins. Features with no user evidence get cut first.

---

*Every feature is guilty until proven innocent. Ship 50% today. No "someday."*
