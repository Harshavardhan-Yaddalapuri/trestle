# Trestle Financials Module — Stage 1 Discovery PRD (1-Pager)

## Problem
Accelerator-backed biomedical/medtech founders currently rely on an internal tool that surfaces generic grant recommendations after forcing them through 80+ redundant questions. The result is verbose, ChatGPT-sounding lists of irrelevant opportunities, and founders are left to manually filter eligibility, check data freshness, and chase opportunities worth ~$500k on average. This wastes time and causes missed funding windows.

## Goal
Ship an MVP vertical slice (by Tuesday) of an intelligent grant/funding matching system that **knows the founder’s profile first**, then only surfaces genuinely eligible opportunities (grants + investments), and alerts them as soon as a new matching source opens.

## Solution
1. **Onboarding/Profile Capture** (lightweight): intake key company attributes (funding raised, years in operation, industry/nuance, bona fide accelerator affiliation, target raise size, geographic scope). 
2. **Eligibility Engine**: a rule-based eligibility matcher that filters opportunities *before* surfacing them. No generic output.
3. **Curated Data Feed**: combine grant catalogs (e.g., NIH, SBIR/STTR, regional life-science funds) and selected angel/seed investment rounds/opportunities into a single structured dataset refreshed daily.
4. **Match & Alert**: return a scored, shortlist of <=5 high-relevance matches; notify the user asynchronously when a new eligible opportunity is added.
5. **MVP UX**: a simple dashboard or CLI/Slack/single-page web experience that shows the shortlist and eligibility rationale (e.g., “Eligible because you’re <2 years post-accelerator, pre-Series A, in medtech”).

## Success Criteria
- [ ] 100% of displayed grants have passed the profile-informed eligibility rule set.
- [ ] End-to-end flow (profile update → score/re-rank → display) works in the demo.
- [ ] Latency for match query < 2 seconds.
- [ ] At least one grant and one investment opportunity included in the curated data.

## Out of Scope (this slice)
- Automated grant application drafting or submission.
- Generic/horizontal grant search (e.g., Y Combinator or non-medtech sources).
- Equity transaction processing, cap table modeling, or due-diligence coordination.
- Multi-user/org or advisor role management.
- Founders not in biomedical/medtech or not accelerator-based.

---

## Core Risks Blocking Tuesday Demo
| Risk | Likelihood | Mitigation |
|------|------------|------------|
| No clean, structured source of _current_ grant / eligibility rules | High | Identify a primary data source and parse rules manually for the MVP subset |
| MVP match engine over-engineered to Tuesday; scope creep into “search engine” | High | Hard cap outputs to 5; use deterministic rules, no ML/reranking in MVP |
| Onboarding form too long (recreating pain point) | Medium | Limit onboarding to ≤ 8 structured questions |
| Data freshness guarantees unrealistic without a live data pipeline | Medium | Show a “last checked” timestamp; use 1 static daily snapshot as demo data layer |
| Target user profile nuances (medtech sub-segments, FDA stage) not captured | Medium | Define explicit MVP profile fields before writing any code |

## Data We MUST Have
1. **Primary Grant Data Feed** (minimum)
   - Source(s): NIH Grants & Funding (and/or Grants.gov/SBIR.gov), plus one regional/accelerator-linked life-science program.
   - Content: Grant title, amount range, close date, eligibility criteria, description, URL.
2. **Eligibility Rules** (minimum)
   - Predefined deterministic rules for the MVP set: company age, prior total raised, industry keyword match, accelerator affiliation status, geographic restrictions, for-profit vs non-profit status.
3. **Investment Opportunity Sample** (minimum)
   - At least 2–3 records of seed/Series A angel or VC medtech-specific rounds or introductions, with comparable attributes.
