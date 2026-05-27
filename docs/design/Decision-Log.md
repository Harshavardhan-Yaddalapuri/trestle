# Trestle Matching MVP — Decision Log (ADRs)

**Version:** 1.0  
**Date:** 2026-05-22  
**Stage:** SDLC Stage 2 — Architecture Decisions Recorded  

---

## ADR-001: Deterministic Rule-Based Eligibility Over Machine Learning

### Status
**Accepted** for Tuesday-Demo MVP. Revisitable after initial traction.

### Context
We need to match founder profiles with grants and investment opportunities. Two high-level approaches exist:
1. **ML/AI recommendation model** (embedding similarity, classifier, or LLM-based matching).
2. **Deterministic rule engine** (explicit if/then rules against structured fields).

### Decision
Use a **deterministic, hardcoded rule-based engine** for the MVP.

### Consequences
- **Positive:**
  - **Fast to build:** Can implement and tune rules in hours, not days/weeks.
  - **Transparent:** Every match has a human-readable rationale string; no black box.
  - **Easier to debug during demo:** If a wrong match appears, we immediately know which rule triggered.
  - **No cold-start problem:** Works on day one with a small dataset.
  - **Spectators at Tuesday demo can be shown the exact rule logic**—builds trust.
- **Negative:**
  - Cannot handle nuanced edge cases as gracefully as an LLM or trained model.
  - Rules require manual updates as new funding programs emerge.
  - Does not improve automatically with more data.

### Mitigation for Post-MVP
Defer ML to a v2 enhancement. When we have &gt; 100 profiles and &gt; 200 historical match outcomes with explicit feedback (clicked/not interested), we can train a lightweight classifier or use LLM embeddings for a hybrid engine.

---

## ADR-002: Profile Intake Limited to ≤ 8 Fields

### Status
**Accepted** for Tuesday-Demo MVP.

### Context
Gathering founder data is a friction point. Each additional field:
- Increases drop-off rate.
- Increases engineering surface (more edge cases, more rule permutations).
- Increases cognitive load during live demo.

### Decision
Cap the **mandatory profile intake at exactly 8 fields** (plus `id` and timestamps).

| # | Field | Required | Notes |
|---|-------|----------|-------|
| 1 | `company_name` | Yes | |
| 2 | `industry` | Yes | e.g., medtech, biotech |
| 3 | `stage` | Yes | pre-seed, seed, series_a, series_b |
| 4 | `funding_need` | Yes | Approx. USD amount |
| 5 | `therapeutic_area` | Yes | e.g., cardiovascular |
| 6 | `geographic_pref` | Yes | Preferred region |
| 7 | `regulatory_pathway` | Optional | 510(k), PMA, CE |
| 8 | `employees` | Optional | For SBIR eligibility |

### Consequences
- **Positive:**
  - **2-minute demo form:** A founder can be onboarded in under 60 seconds live.
  - **Tightly scoped rules engine:** Fewer complex inter-field logic groups.
  - **Mobile-friendly:** Small form renders without scrolling on most devices.
  - **Low validation complexity:** Fewer edge cases to defend against.
- **Negative:**
  - Loses granularity (e.g., no separate fields for "revenue", "patent count", "clinical phase").
  - May produce more generic matches if founders differ in ways not captured.

### Mitigation for Post-MVP
Add optional "expand" step after onboarding: founders can fill advanced fields later and receive more refined matches. The 8-field form remains the golden-path.

---

## ADR-003: PostgreSQL / SQLite for MVP Data Store (vs. NoSQL)

### Status
**Accepted** for Tuesday-Demo MVP.

### Context
We need a data store for profiles, grants, investment opportunities, eligibility rules, and match results. Candidate categories:
1. **Relational SQL** (PostgreSQL, SQLite, MySQL).
2. **Document / NoSQL** (MongoDB, DynamoDB, Firestore).
3. **Vector DB** (Pinecone, Weaviate).

### Decision
Use **SQLite for local development / single-laptop demo** and **PostgreSQL for any deployed/shared instance**. No NoSQL in MVP.

### Consequences
- **Positive:**
  - **Schema rigor:** Enforced `CHECK` constraints and `NOT NULL` prevent bad data early.
  - **Joins are natural:** Matching inherently joins `profiles × opportunities × rules`—SQL excels here.
  - **Deterministic indexes:** `B-tree` indexes give predictable `O(log n)` lookup performance.
  - **Trivial migration path:** SQLite DDL is nearly identical to PostgreSQL; switching is a single connection string change.
  - **No ops overhead for SQLite:** A file on disk means the demo works offline on a laptop.
- **Negative:**
  - SQLite does not support high write concurrency well (irrelevant for read-heavy demo).
  - PostgreSQL requires a running server (mitigated by free-tier managed hosts).
  - Less flexible schema than a document store (mitigated by frozen, small schema for MVP).

### Why Not NoSQL?
- **Relational data:** Our entities have clear FK relationships and tabular structure. No nested documents or polymorphic schemas.
- **No horizontal scale requirement:** Hundreds of rows, not millions.
- **SQL isTeam's current strength:** Faster to prototype queries and debug via standard `psql` or `sqlite3` CLI.

### Mitigation for Post-MVP
If we later need flexible metadata (unstructured grant attachments, dynamic profiles), we can bolt on a JSONB column inside PostgreSQL or add a Mongo side-table without rewriting the relational core.

---

*End of Decision Log*
