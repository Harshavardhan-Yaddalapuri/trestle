# Trestle Financials Module — Product Roadmap Outline

## Milestones

### M1 — MVP Vertical Slice (Grant Matching Engine)
- **Target:** Tuesday (demo)
- **Deliverable:** End-to-end workflow from profile intake to eligible shortlist display + single notification proof-of-concept.
- **Key Activities:**
  - Finalize 8-field founder profile schema.
  - Build deterministic eligibility rule engine (rules, no ML).
  - Ingest and clean 1 primary grant dataset + 1 investment sample.
  - Lightweight UX (web dashboard or CLI/Single page).
  - Run a dry-run with a real founder profile sample.

### M2 — Double the Data Coverage + Real-Time Scoring
- **Target:** End of Week 2
- **Deliverable:** 2x more sources (e.g., SBIR, state biotech grants, additional angel groups); updated scoring logic; auto-refresh daily snapshots.
- **Key Activities:**
  - Expand crawl/ETL to secondary source(s).
  - Add numeric relevance score with explanation strings.
  - Implement a daily sync job and stale-data warnings.

### M3 — Notifications + Alerts MVP
- **Target:** End of Month 1
- **Deliverable:** Asynchronous alerting pipeline — push (email / Slack / in-app) when a newly added grant matches the user profile.
- **Key Activities:**
  - Webhook/notification system (email + Slack).
  - Differential scanning of source feeds.
  - User preference controls (frequency, channels).

### M4 — Investment Pipeline + Deal Desk UX
- **Target:** End of Month 2
- **Deliverable:** Full “financials” view: side-by-side grants vs. investment opportunities, pipeline stages, intro warm-tracker.
- **Key Activities:**
  - Define deal-stage taxonomy.
  - CRM-like pipeline UI for tracked opportunities.
  - Intro/warm-intro tracking for investment leads.

### M5 — Growth + Analytics
- **Target:** End of Month 3–4
- **Deliverable:** Funding pipeline analytics, cohort success metrics, ML-powered recommendation refinement, marketplace / partner integrations.
- **Key Activities:**
  - Match outcome feedback loop.
  - A/B test rule-sets vs. learned recommendation.
  - Integrate with external cap table/accounting tools.
