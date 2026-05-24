# Agentic Search Experiment Design

## Purpose

The product question is whether agentic internet search can solve fragmentation and validation for founder resources. The experiment should measure whether a model can move from "generic startup funding advice" to a founder-specific moment of discovery: "wait, that exists?"

Do not run these experiments yet. This is the design for later execution.

## Core Hypotheses

1. **Agentic search is strong for public, maintained, official resources.** Examples: AWS Activate, Google for Startups, YC, Techstars, Challenge.gov, SBIR.gov, Devpost.
2. **Agentic search needs validation guardrails for volatile resources.** Examples: accelerators with cohort deadlines, pitch competitions, local grants, foundation opportunities.
3. **Agentic search alone is weak for poorly indexed or relationship-driven resources.** Examples: hyperlocal community funds, family offices, small foundation grants, chamber programs, local wet-lab availability.
4. **A hybrid system should outperform pure search.** A structured resource database can provide baseline coverage and deduplication; agents can validate freshness, reason over eligibility, and discover new resources.

## Representative Resource Sample

Use a stratified sample from `startup-funding-sources.md`:

- **Obvious national resources:** YC, Techstars, AWS Activate, Google for Startups, SBIR/STTR, Grants.gov, Challenge.gov.
- **Specialized vertical resources:** AI Grant, Activate, Breakthrough Energy Fellows, IndieBio, JLABS, AFWERX, HAX, MassRobotics.
- **Demographic resources:** Visible Hands, Black Ambition, StartOut, Bunker Labs, Unshackled Ventures, Cartier Women's Initiative, 2Gether-International.
- **Freshness-sensitive opportunities:** TechCrunch Startup Battlefield, SXSW Pitch, Rice Business Plan Competition, DOE American-Made Challenges, university competitions, Devpost hackathons.
- **Structured-but-complex programs:** R&D tax credits, SSBCI, state economic development funds, USDA grants, government set-asides, OTAs.
- **Hard-to-index resources:** community foundations, local CDFIs, chambers of commerce, religious/community funds, wet-lab or coworking availability.

## Systems to Compare

### 1. Single-Agent Baseline

One model searches, validates, extracts, and ranks resources.

- **Use for:** a simple baseline.
- **Expected weakness:** missed resources and overconfidence because the model validates its own discoveries.

### 2. Discoverer + Validator

One agent discovers candidates. A separate validator checks official sources, status, deadlines, eligibility, and citations.

- **Use for:** the default experiment architecture.
- **Expected benefit:** lower stale-resource and eligibility hallucination rate.

### 3. Category-Specialist Agents

Separate agents search for resource categories:

- Grants and SBIR/STTR.
- Accelerators and credits.
- State/local funds.
- Demographic programs.
- Competitions and hackathons.
- Tax credits and incentives.
- University/lab resources.
- Foundation and community resources.

- **Use for:** recall testing and category-level failure analysis.
- **Expected weakness:** duplicate results and higher orchestration cost.

### 4. Multi-Agent Search + Central Evidence Judge

Several independent search agents produce candidates. A central judge deduplicates, validates, ranks, and records evidence.

- **Use for:** high-value benchmark rounds.
- **Expected benefit:** better detection of overlooked resources.

### 5. Hybrid Database + Agent

A structured resource index retrieves likely candidates; an agent validates freshness, eligibility, and missing categories.

- **Use for:** testing the likely product architecture.
- **Expected benefit:** more reproducible coverage and better freshness than either database or agent alone.

## Control Sets

### Known-Resource Control

Easy-to-find resources every capable system should surface when relevant: YC, Techstars, AWS Activate, Google for Startups, SBIR/STTR, Grants.gov, Challenge.gov, Kickstarter, Microsoft for Startups.

### Long-Tail Control

Valid but less SEO-dominant resources: niche accelerators, demographic programs, university competitions, disease foundations, federal lab partnerships, local CDFIs.

### Freshness Control

Resources with changing windows, renamed programs, paused programs, updated funding amounts, or recurring annual cycles.

### Eligibility Trap Control

Resources that look relevant but are not eligible because of nonprofit status, geography, stage, revenue, academic affiliation, founder demographic requirements, or application window.

### Stale-Web Control

Old blog posts, cached event pages, outdated application pages, expired deadlines, and aggregator pages that conflict with official sources.

### Oracle-Hidden Control

Resources discovered through expert curation, structured databases, direct site crawling, SBDC/APEX networks, foundation databases, or local ecosystem partners.

## Gold Standard Construction

For each founder profile, create a reviewed gold set with three labels:

- **Positive:** founder is likely eligible.
- **Conditional:** eligibility depends on missing facts or timing.
- **Negative:** resource is stale, closed, irrelevant, ineligible, or misleading.

Each gold entry should include canonical name, type, official URL, eligibility criteria, current status, amount/value, deadline, match rationale, last verified date, evidence quote, known aliases, and whether it is high-value, niche, local, demographic, or hidden.

## Metrics

### Recall

Measures whether the system found resources the founder should know about.

- Overall recall.
- High-value recall.
- Long-tail recall.
- Demographic-resource recall.
- Non-dilutive recall.
- Temporal recall for open/upcoming resources.
- Conditional recall where caveats are correct.

Scoring:

- `1.0`: found canonical resource or equivalent application page.
- `0.5`: found related umbrella program but missed the specific opportunity.
- `0`: missed.

### Precision

Measures whether surfaced resources are actually relevant.

- Strict precision: only currently eligible resources count.
- Lenient precision: conditional resources count if caveated.
- Top-k precision: top 5, top 10, top 20.
- Founder-fit precision: stage, sector, geography, and founder attributes match.

### Freshness

Score each resource:

- `3`: official source, current cycle, accurate deadline/status.
- `2`: official source, mostly current, minor uncertainty.
- `1`: third-party or outdated source, status unclear.
- `0`: expired, defunct, wrong deadline, stale page, or old funding amount.

### Eligibility Reasoning

Score each recommendation:

- `3`: correct eligibility reasoning with caveats and missing facts.
- `2`: mostly correct, minor caveats missing.
- `1`: vague keyword match.
- `0`: incorrect eligibility claim.

Track an eligibility hallucination rate: unsupported eligibility assertions divided by total recommended resources.

### Citation Quality

Score each cited source:

- `3`: official, specific page supporting the claim.
- `2`: reliable secondary source plus official homepage.
- `1`: generic homepage, stale blog, or weak support.
- `0`: missing, broken, unrelated, or contradictory.

### Usefulness

Founder or expert reviewers score:

- Actionability.
- Ranking by fit, urgency, value, and effort.
- Coverage across resource types.
- Eligibility clarity.
- Deadline awareness.
- Novelty.
- Avoidance of noise.

Suggested weighted score:

```text
0.25 actionability
+ 0.20 fit/prioritization
+ 0.15 coverage
+ 0.15 eligibility clarity
+ 0.15 freshness
+ 0.10 novelty
```

## Detecting Missed Resources

### Human Expert Oracle

Have domain experts independently curate resources for each founder. Use this especially for local funds, foundation grants, government procurement, university/lab resources, and demographic programs.

### Multi-Oracle Aggregation

Combine sources from experts, search engines, government databases, grant databases, accelerator directories, foundation databases, university offices, Challenge.gov, Devpost, MLH, F6S, local SBDCs, and APEX Accelerators.

### Query Expansion Oracle

Generate exhaustive search variants for each founder:

- Resource synonyms: grant, award, fellowship, accelerator, challenge, credit, incentive, procurement, sponsorship.
- Sector terms: climate, carbon, agtech, synthetic biology, defense, fintech, govtech.
- Founder terms: woman founder, immigrant founder, veteran-owned, disabled entrepreneur, student founder.
- Status terms: application open, deadline, rolling, current year.

### Cross-Agent Comparison

Run independent agents with different search objectives:

- Find non-obvious resources.
- Find official application pages only.
- Find resources that are not accelerators.
- Find demographic-specific resources.
- Find open opportunities in the next 90 days.
- Find government and foundation database resources only.

Resources found by one agent but missed by another become candidate misses.

### Directory and Database Oracle

Compare against structured sources such as Grants.gov, SBIR.gov, Challenge.gov, SAM.gov, Candid, Instrumentl, Devpost, MLH, F6S, university directories, and cloud credit directories.

### Link-Graph Expansion

Starting from known resources, crawl or inspect pages for partners, portfolio, programs, eligibility, apply, resources, sponsors, past winners, and similar programs.

### Adversarial Tests

Include profiles and resources designed to catch:

- Intersectional eligibility.
- Non-obvious resource types such as procurement or tax credits.
- Stale bait from old blog posts.
- Program rebrands.
- Over-broad demographic assumptions.
- Geographic traps.
- Entity-type traps.
- Stage traps.
- Sector traps.
- Closed-window traps.

### Capture-Recapture Estimation

Use independent search methods and overlap counts to estimate unseen resources when the full resource universe is unknowable.

## Failure Modes to Log

- Missed obvious resource.
- Missed niche or high-value resource.
- Missed demographic-specific resource.
- Over-focus on equity funding.
- Failure to search synonyms or aliases.
- Reliance on stale listicles.
- Wrong deadline or application status.
- Wrong geography, stage, sector, entity type, academic affiliation, citizenship, or demographic eligibility.
- Cited homepage instead of application or eligibility page.
- Broken or unsupported citation.
- No ranking, no next step, or too much irrelevant noise.
- Parent organization confused with specific program.
- Duplicate resources under old and new names.

## Run Record Schema

Each future experiment run should store structured evidence:

```json
{
  "founder_profile_id": "...",
  "system": "single_agent | discoverer_validator | category_agents | multi_agent_judge | hybrid",
  "resource_name": "...",
  "resource_type": "...",
  "official_url": "...",
  "recommended_rank": 1,
  "claimed_eligibility": "...",
  "gold_label": "positive | conditional | negative | missed",
  "freshness_score": 0,
  "eligibility_score": 0,
  "citation_score": 0,
  "usefulness_score": 0,
  "failure_modes": [],
  "reviewer_notes": "...",
  "verified_at": "..."
}
```

## What the Experiment Should Answer

- Which model and architecture has the best high-fit recall?
- Which categories are consistently missed?
- Which categories produce the most stale or ineligible recommendations?
- Does a separate validator reduce false positives?
- Does multi-agent search find resources that single-agent search misses?
- Does a structured resource index improve recall, reproducibility, and cost?
- Which source types should be handled by open-web agents, and which require databases, local partnerships, or human review?
