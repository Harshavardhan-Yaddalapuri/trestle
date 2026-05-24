# Agentic Search Model and Source Strategy

## What We Learned

Founder-resource discovery is not one task. It combines candidate discovery, source validation, eligibility reasoning, deduplication, ranking, and founder-facing explanation. Different resource categories stress different capabilities:

- Major accelerators and cloud-credit programs test whether agents can find maintained official pages.
- Grants, tax credits, and procurement programs test whether agents can interpret complex eligibility language.
- Local funds, community resources, and foundation grants test whether open-web search has enough coverage.
- Pitch competitions and hackathons test freshness, deadline accuracy, and stale-page handling.
- Demographic resources test whether agents collect enough founder information and avoid unsupported assumptions.

The strongest expected product pattern is not "agent only" or "database only." It is a hybrid: structured resource records for coverage and reproducibility, plus agentic search for freshness checks, long-tail expansion, and personalized eligibility reasoning.

## Model Classes to Test

Do not assume one "best" model. Test capability classes against the same benchmark.

### 1. Frontier Reasoning + Tool-Use Models

- **Use for:** lead search, validation, eligibility reasoning, conflict resolution, final ranking.
- **Why test:** these models should be best at interpreting nuanced eligibility across government, university, foundation, and accelerator pages.
- **Expected strengths:** reasoning over founder constraints, catching contradictions, explaining caveats.
- **Expected weaknesses:** cost, latency, occasional overconfidence.

### 2. Search-Native or Browsing-Optimized Models

- **Use for:** broad candidate discovery and current web research.
- **Why test:** many resources are only visible through current search, not model memory.
- **Expected strengths:** query expansion, finding official pages, locating current deadlines.
- **Expected weaknesses:** may retrieve broad SEO results without enough eligibility reasoning.

### 3. Long-Context Models

- **Use for:** comparing many candidate resources against a complete founder profile and a long evidence bundle.
- **Why test:** resource matching requires holding stage, geography, sector, legal structure, founder attributes, restrictions, and deadlines in context.
- **Expected strengths:** deduplication, ranking, evidence synthesis.
- **Expected weaknesses:** can still miss new resources if not paired with strong search.

### 4. Fast / Mid-Tier Models

- **Use for:** extraction, classification, normalization, and cheap second-pass processing.
- **Why test:** after discovery, many tasks are repetitive field extraction.
- **Expected strengths:** lower cost and speed.
- **Expected weaknesses:** should not be trusted as the final validator for eligibility-heavy resources.

### 5. Small or Local Extraction Models

- **Use for:** structured extraction from already fetched pages.
- **Why test:** may reduce cost for database maintenance.
- **Expected strengths:** JSON extraction, date parsing, category classification.
- **Expected weaknesses:** weak autonomous discovery and complex reasoning.

## Suggested Model Experiment Matrix

| Role | Model class to test | Main success metric |
|---|---|---|
| Lead discoverer | Frontier reasoning or search-native | Recall of valid opportunities |
| Validator | Frontier reasoning | Freshness, citation, and eligibility accuracy |
| Extractor | Fast/mid-tier or small model | Structured-field accuracy |
| Deduper/ranker | Long-context or frontier | Correct ranking and alias resolution |
| Adversarial reviewer | Frontier reasoning | Catches stale, hallucinated, or ineligible sources |

At test time, select current representative models from several providers and run them on the same founder profiles, prompts, and scoring rubric. Avoid relying on vendor claims; use empirical performance on this benchmark.

## Should We Split Off Subagents?

Yes, but compare against a single-agent baseline.

### Recommended Default: Discoverer + Validator

- **Discoverer:** produces broad candidates and source URLs.
- **Validator:** checks official pages, current status, eligibility, deadlines, and evidence.
- **Why:** separates search creativity from verification discipline.

### Main Benchmark: Category Specialists + Central Judge

Use category specialists for:

- Federal grants and SBIR/STTR.
- Accelerators and cloud credits.
- State/local funds.
- Demographic founder programs.
- Competitions and hackathons.
- Tax credits and incentives.
- University, lab, and sponsored research resources.
- Foundation and community capital.

Then use a central evidence judge to dedupe, validate, and rank. This should improve recall and expose category-specific blind spots.

### High-Recall Audit: Independent Search Agents

Run multiple agents with intentionally different prompts. Compare overlaps and differences. A resource found by one agent and missed by another is an important signal for overlooked-resource testing.

## Source-Type Fit for Agentic Search

### Tier 1: Fantastic Fit for Agentic Web Search

These sources tend to have official pages, clear applications, and public eligibility.

- **Corporate startup programs and credits:** AWS Activate, Google for Startups, Microsoft for Startups, NVIDIA Inception.
- **Major accelerators:** YC, Techstars, 500 Global, MassChallenge, Alchemist, StartX, Antler.
- **Federal challenge portals:** Challenge.gov, DOE American-Made Challenges, NASA challenges, AFWERX/xTech.

Agentic search should find and validate these well, as long as it cites official pages and checks current terms.

### Tier 2: Good Fit, But Validation Is Required

These are discoverable but have changing cycles or nuanced eligibility.

- **SBIR/STTR:** NSF, NIH, DOE, DoD, NASA, USDA, EPA.
- **National demographic founder programs:** Black Ambition, Visible Hands, StartOut, Bunker Labs, Unshackled Ventures, Cartier Women's Initiative.
- **Pitch competitions and hackathons:** TechCrunch Startup Battlefield, SXSW Pitch, Rice Business Plan Competition, Devpost, MLH, HeroX.
- **University programs:** Harvard i-lab, MIT delta v, Cornell eLab, Berkeley SkyDeck, university tech transfer offices.

Agents can work well here if the system requires official-source validation, current-cycle evidence, and founder-fit reasoning.

### Tier 3: Mixed Fit; Use Agent + Indexed Database

These sources are fragmented, legally complex, or inconsistently published.

- **State and local funds:** SSBCI, state economic development funds, city grants, local innovation funds.
- **Tax credits and incentives:** R&D tax credits, hiring credits, IRA credits, CHIPS Act, state incentives.
- **Foundation grants:** Gates, CZI, Open Philanthropy, disease foundations, community foundations.
- **Government procurement:** SAM.gov, set-asides, OTAs, CSOs, APEX Accelerators.

The agent can discover and summarize, but a structured database or expert-reviewed ruleset should anchor coverage and eligibility.

### Tier 4: Weak Fit for Open-Web Agents Alone

These sources may be offline, poorly indexed, relationship-driven, or stale.

- **Community resources:** Rotary, Lions, Kiwanis, religious/community funds, church-affiliated CDFIs, tribal economic development grants.
- **Very local events:** small chamber competitions, local bank grants, local university pitch nights, Eventbrite and Lu.ma listings.
- **Private investor networks:** family offices, UHNW individuals, informal angel networks.
- **Physical availability:** wet-lab benches, coworking capacity, incubator space availability.

These require local partnerships, structured intake from ecosystem organizations, periodic human verification, or direct data feeds.

## Source Validation Rubric

Score each candidate from 0-5:

| Dimension | 5 | 3 | 1 |
|---|---|---|---|
| Officialness | Official program or agency page | Reputable aggregator | Blog/listicle only |
| Freshness | Current cycle or deadline visible | Recent but unclear | No date or stale |
| Eligibility clarity | Explicit criteria | Partial criteria | Vague or absent |
| Founder fit | Strong match | Possible match | Weak or unclear |
| Actionability | Apply/contact link present | Next step inferable | No clear next step |
| Evidence quality | Direct quote supports claim | Indirect support | Unsupported |
| Staleness risk | Low | Medium | High |

Recommended labels:

- **Validated:** official, current, eligible, actionable.
- **Promising but needs human review:** likely relevant but missing a key fact.
- **Weak candidate:** category-relevant but poor evidence.
- **Reject:** stale, closed, unofficial, ineligible, or non-actionable.

## Product Suggestions

### Build Around Evidence, Not Just Recommendations

Every resource recommendation should store:

- Official URL.
- Evidence quote.
- Last checked date.
- Deadline or rolling status.
- Eligibility fields matched to founder profile.
- Confidence and uncertainty.
- Human-review flag when needed.

### Treat Resource Types Differently

Do not use one generic search strategy for all categories. Cloud credits, SBIR solicitations, local CDFIs, and foundation grants have different discovery paths and failure modes.

### Require Founder Intake Before Search

The agent cannot reliably find demographic, university, procurement, tax, or grant resources without key facts such as geography, entity type, stage, sector, founder statuses, university affiliation, revenue, and use of funds.

### Maintain a Living Resource Index

Use agents to update and validate an index rather than generating one-off answers. Track old names, aliases, sponsor domains, application URLs, deadlines, cycles, eligibility, and last verification dates.

### Use Agents for Freshness and Gaps

Agents are especially valuable for:

- Detecting changed deadlines.
- Finding newly announced programs.
- Checking whether a database entry is stale.
- Discovering adjacent categories the founder did not ask about.
- Explaining conditional eligibility.

### Add Human Review Where Risk Is High

Tax credits, legal structures, securities issues, immigration-sensitive founder programs, government procurement, and foundation grants should be labeled as discovery assistance and routed to expert review where necessary.

## Answer: What Does This Agent Remember?

This agent can use the conversation context while this chat is active and can read files in the repository, including the Markdown files created here. It does not have a separate durable memory that future agents automatically inherit beyond what is saved in durable places such as repository files, commits, branches, PR descriptions, or any system-generated summaries. If something must persist across agents or sessions, write it into the repo or another explicit artifact.
