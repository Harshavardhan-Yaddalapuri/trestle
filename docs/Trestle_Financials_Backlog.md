# Trestle Financials Module — Initial Product Backlog

## GitHub-Issue-Ready Titles (MVP Vertical Slice)

### P0 (Must-Have for Tuesday Demo)
1. `[Fin] Design lightweight founder profile schema (≤8 fields) for accelerator-based medtech/biomedical startups`
2. `[Fin] Implement deterministic eligibility rule engine for grant/investment matching`
3. `[Fin] Ingest and normalize primary grant dataset (NIH/SBIR/Grants.gov) into structured records`
4. `[Fin] Add investment opportunity sample records (seed/Series A medtech)`
5. `[Fin] Build match-and-rank endpoint: input profile → return ≤5 eligible opportunities with rationale`
6. `[Fin] Create single-page dashboard / CLI slice to display shortlist and eligibility rationale`
7. `[Fin] Add "last checked" timestamp and data-freshness indicator to matches`
8. `[Fin] Seed demo with realistic founder profile and run end-to-end dry-run`

### P1 (Immediate Follow-On)
9. `[Fin] Expand eligibility rules to cover geographic restrictions and non-profit status`
10. `[Fin] Integrate secondary grant source (state/regional biotech fund)`
11. `[Fin] Set up daily ETL cron/job to refresh grant snapshot`
12. `[Fin] Implement proof-of-concept notification for new eligible grant addition`
13. `[Fin] Add input validation and edge-case handling to profile schema`

### P2 (Next Milestone)
14. `[Fin] Build notification pipeline (email/Slack) for new match alerts`
15. `[Fin] Add numeric relevance score with human-readable explanation string`
16. `[Fin] Design investment pipeline stage taxonomy and basic CRM UI`
17. `[Fin] Implement feedback loop to improve match quality from user signals`
