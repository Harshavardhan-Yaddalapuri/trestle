# Agentic Search Experiment Results

This document summarizes the five exploratory experiments run on May 24, 2026 to test agentic internet search for founder-resource discovery and validation. The experiments used the resource taxonomy in `startup-funding-sources.md` and the founder examples in `founder-agentic-search-archetypes.md`.

These were lightweight live-web experiments, not production benchmarks. No code was run and no automated crawler was built. Each experiment used agentic web search, official-source checks where possible, and qualitative scoring.

## Executive Summary

Agentic search found many useful resources, but raw search output was not reliable enough to show directly to founders. The strongest pattern was a hybrid workflow:

1. Use agents for broad discovery, long-tail expansion, and freshness checks.
2. Use a separate validator agent or validation step for official source, deadline, eligibility, and actionability.
3. Maintain a structured resource index for canonical records, aliases, deadlines, cycles, and status history.
4. Present recommendations with status labels such as `Open now`, `Closed but recurring`, `Possible match`, `Needs expert review`, and `Stale/unverifiable`.

Across one 40-resource discoverer/validator run:

- **Strong matches:** 15/40, or 37.5%.
- **Strong + possible matches:** 31/40, or 77.5%.
- Main false-positive driver: stale application windows and outdated cohort pages.
- Main uncertainty driver: missing founder intake details such as geography, TRL, disease area, immigration/ownership status, academic affiliation, employee count, and willingness to give equity.

## Experiment 1: Discoverer + Validator on Five Founder Archetypes

### How It Was Conducted

A subagent used live web search against five founder archetypes:

1. AI infrastructure founder.
2. Climate hardware / carbon-removal founder.
3. Biotech diagnostics founder.
4. Defense / govtech founder.
5. Underrepresented consumer brand founder.

For each archetype, it discovered 6-8 candidate resources, then performed lightweight validation using official pages where possible. Each resource was labeled:

- **Strong:** official/current and likely eligible.
- **Possible:** real and relevant, but conditional on missing facts or timing.
- **Weak:** tangential or low fit.
- **Stale:** closed, past deadline, or not currently actionable.
- **Not eligible:** clear mismatch.

### Results

#### AI Infrastructure

Strong or likely useful resources included:

- NVIDIA Inception.
- Google for Startups Cloud Program.
- AWS Activate.
- Microsoft for Startups.
- YC S26, conditional on equity appetite.
- South Park Commons Founder Fellowship, conditional on timing and fit.

Stale or not eligible:

- AI Grant Batch 4 was closed.
- Anthropic + AWS Agentic AI Accelerator was current but India-limited.

#### Climate Hardware

Strong or likely useful resources included:

- Activate Fellowship.
- Breakthrough Energy Fellows.
- Third Derivative.
- Greentown Labs.
- ARPA-E IGNIITE, if deadline and PI constraints fit.

Stale or not eligible:

- XPRIZE Carbon Removal had concluded.
- DOE CDR Purchase Pilot Prize was closed to new entrants.
- DOE SBIR/STTR FY2026 release deadlines had mostly passed.

#### Biotech Diagnostics

Strong or likely useful resources included:

- JLABS.
- IndieBio / SOSV.
- NIH SBIR/STTR for a future receipt cycle.
- Illumina for Startups if genomics-related.
- Nucleate Activator if academic spinout criteria fit.

Main caveat: practical fit depends heavily on disease area, regulatory path, and university/IP status.

#### Defense / Govtech

Strong or likely useful resources included:

- AFWERX Open Topic.
- DoD SBIR/STTR / DSIP.
- APEX Accelerators.
- Military Founders Lab.
- DIU when a solicitation is open.
- In-Q-Tel if product-ready and national-security relevant.

Stale or weak:

- Army xTechSearch result surfaced an old deadline.
- Hivers & Strivers was veteran-relevant but less specific to government contracting.

#### Underrepresented Consumer Brand

Strong or likely useful resources included:

- Walmart Open Call.
- Target Takeoff / Supplier Intake.
- Cartier Women's Initiative, if impact and company criteria fit.
- Galaxy Grants.
- Made for Retail Chicago, if local.

Stale or uncertain:

- Sephora Accelerate 2026 applications were closed.
- Black Ambition and Ulta MUSE needed current-cycle confirmation.

### Main Takeaways

- Agentic search produced useful candidate lists, but only 37.5% were strong without caveats.
- Most "possible" matches needed better founder intake before ranking.
- Deadlines and application windows must be treated as first-class data.
- The best non-obvious finds were often niche or current-cycle resources such as ARPA-E IGNIITE, Nucleate, Military Founders Lab, Made for Retail Chicago, and Galaxy Grants.

## Experiment 2: Agentic Search vs Known Gold Set

### How It Was Conducted

A subagent built a hand-seeded gold set of 12 known resources across three archetypes:

- AI infrastructure.
- Climate hardware.
- Defense / govtech.

It then searched as if it did not know the gold set, validating whether each resource was found, missed, or partially found.

Gold resources included AWS Activate, Google for Startups Cloud AI Program, NVIDIA Inception, AI Grant, Activate Fellowship, ARPA-E, Breakthrough Energy Fellows, Greentown Labs, AFWERX, DIU, Army xTechSearch, and APEX Accelerators.

### Results

- **Strict first-pass recall:** about 5/12, or 42%.
- **Iterative recall after category refinement and validation:** 8 found + 4 partial out of 12.
- **Found or partial:** 12/12, but several required targeted query refinement.

Clear finds:

- AWS Activate.
- Google for Startups Cloud AI Program.
- NVIDIA Inception.
- Activate Fellowship.
- ARPA-E.
- Greentown Labs.
- DIU.
- Army xTechSearch.

Partial or nuanced:

- AI Grant had name collision and closed-cycle ambiguity.
- Breakthrough Energy Fellows was relevant but closed until a future cycle.
- AFWERX required defense/SBIR-specific refinement to rank well.
- APEX Accelerators was relevant procurement support, not direct capital.

### Main Takeaways

- Agentic search should not rely only on broad founder-style queries.
- Seeded canonical resources should be used as recall anchors.
- Acronym expansion matters, especially for defense and government resources: AFWERX, DIU, NSIN, APEX, SBIR, CSO, OTA.
- Resources should be typed carefully: funding, procurement support, lab access, credits, equity accelerator, or watchlist.

## Experiment 3: Freshness / Stale-Resource Test

### How It Was Conducted

A subagent tested 12 resources with deadlines, cohorts, or known staleness risk. It checked official URLs, status, deadlines or cycles, conflicting pages, and confidence.

Resources included TechCrunch Startup Battlefield, SXSW Pitch, Rice Business Plan Competition, MIT $100K, DOE American-Made Challenges, Challenge.gov, SBIR/STTR agency pages, Devpost, MLH, MassChallenge, 43North, and YC.

Freshness was scored:

- `3`: fresh/current authoritative page.
- `2`: usable but partial, moved, or conflicting.
- `1`: high stale/conflict risk.
- `0`: unusable.

### Results

Freshness distribution:

- **Score 3:** 7/12.
- **Score 2:** 4/12.
- **Score 1:** 1/12.
- **Score 0:** 0/12.

Status distribution:

- **Currently open / late-open / active listings:** 6.
- **Closed or completed 2026 cycle:** 4.
- **Recurring or upcoming but exact deadline unclear:** 2.

Important examples:

- TechCrunch Startup Battlefield was open with a May 27, 2026 deadline.
- YC Summer 2026 late applications were still accepted.
- SXSW Pitch and Rice Business Plan Competition had completed their 2026 cycles.
- Challenge.gov had sunset/migration issues and needed USA.gov or agency-page handling.
- DOE American-Made surfaced contradictory "open" labels beside old deadlines.
- MassChallenge and 43North required program-specific or waitlist interpretation.

### Main Takeaways

- Official pages can still be stale, archived, or internally contradictory.
- Recurring programs need cycle-level records, not one static URL.
- The product should automatically detect stale signals: old year, expired deadline, "applications closed," "winners announced," event already passed, placeholder content, and status/deadline mismatch.
- Founder-facing outputs should show confidence and verification status.

## Experiment 4: Missed-Resource Audit With Multiple Search Strategies

### How It Was Conducted

A subagent simulated three independent search strategies on one difficult founder profile:

> Immigrant woman climate-hardware founder with university IP, prototype, pre-seed stage, non-dilutive preference, and openness to accelerators/lab access.

Strategies:

1. **Broad search:** founder identity, climate hardware, prototype, pre-seed, non-dilutive, accelerator, lab access.
2. **Non-obvious search:** university spinout, IP commercialization, lab access, licensing, CRADA, prototype validation, voucher.
3. **Official/database search:** DOE, NSF, ARPA-E, Grants.gov/Simpler, American-Made, ENERGYWERX, NREL, Challenge.gov/USA.gov.

### Results

The overlap between strategies was very low.

Broad search found:

- Greentown First Valley Fellowship.
- Venture For ClimateTech.
- Cox Cleantech Residency.
- Cartier Women's Initiative Science & Technology Pioneer Award.
- Halcyon Caribbean Climate Pre-Accelerator.
- Unshackled Ventures U-Labs.

Non-obvious search found:

- LabStart Fellowship.
- 9Zero Lab Access.
- CRADAs and national-lab partnership paths.
- DOE Cradle to Commerce / CLIMR-style commercialization paths.
- Maryland Energy Innovation Accelerator Phase 2.
- mHUB and other hard-tech resources.

Official/database search found:

- NSF SBIR/STTR.
- DOE SBIR/STTR.
- ARPA-E opportunities.
- DOE LEEP.
- Activate Fellowship.
- American-Made Challenges.
- ENERGYWERX vouchers.
- DOE Critical Minerals & Materials Accelerator.
- NREL partnerships.

Approximate overlap:

- Broad and non-obvious shared only a small number of resources, mainly Greentown-related.
- Non-obvious and official/database overlapped on DOE/national-lab pathways.
- Broad and official/database had almost no clean overlap.
- No resource was clearly found by all three strategies.

### Main Takeaways

- One query style materially misses eligible resources.
- "Non-dilutive" must expand to grants, fellowships, stipends, prizes, vouchers, in-kind lab access, tech-transfer support, and vendor-paid prototyping.
- Demographic, technical, and official-government resources live in different search ecosystems.
- Immigration/ownership status is a critical eligibility detail for SBIR/STTR.
- The best search orchestration is multi-pass:
  1. Broad profile sweep.
  2. Technical/IP/lab-access sweep.
  3. Official/database sweep.
  4. Gap checker over categories.

## Experiment 5: Source-Type Performance Test

### How It Was Conducted

A subagent tested six source categories for generic early-stage US tech founders:

1. Cloud credits.
2. Accelerators.
3. Grants / SBIR.
4. Pitch competitions.
5. Demographic founder programs.
6. State/local/tax incentives.

Each category was scored from 0-5 for discoverability, freshness, eligibility clarity, actionability, and need for database/human review. A higher database/human-review score means the category is less suitable for open-web agentic search alone.

### Results

| Category | Discoverability | Freshness | Eligibility clarity | Actionability | Need DB / human review |
|---|---:|---:|---:|---:|---:|
| Cloud credits | 5.0 | 4.5 | 4.0 | 4.5 | 1.5 |
| Accelerators | 4.5 | 4.0 | 3.8 | 4.2 | 2.5 |
| Grants / SBIR | 4.0 | 3.2 | 4.1 | 3.3 | 4.5 |
| Pitch competitions | 4.3 | 3.6 | 3.4 | 3.7 | 3.5 |
| Demographic founder programs | 3.8 | 3.3 | 3.7 | 3.5 | 4.0 |
| State/local/tax incentives | 2.8 | 3.0 | 2.7 | 2.4 | 5.0 |

### Category Findings

#### Cloud Credits

Agentic search worked very well for AWS Activate, Google Cloud Startup Program, Microsoft for Startups, NVIDIA Inception, DigitalOcean Hatch, Vercel for Startups, and similar programs.

Main risk: credit amounts and partner requirements can be hidden behind dashboards, login walls, or third-party partner pages.

#### Accelerators

Agentic search worked well for YC, Techstars, 500 Global, MassChallenge, Alchemist, Antler, and ERA.

Main risk: old cohort pages and current cohort pages coexist, and terms/deadlines vary by program track.

#### Grants / SBIR

Agentic search found official pages for NSF, NIH, DOE, NASA, Defense, EPA, USDA, and SBIR.gov.

Main risk: eligibility is legally precise and topic-specific; PDFs and old solicitations rank highly; multiple portals must be checked.

#### Pitch Competitions

Agentic search found TechCrunch Startup Battlefield, SXSW Pitch, Rice Business Plan Competition, DOE American-Made, Challenge.gov/USA.gov, Army xTech, 43North, MIT Solve, and Devpost/XPRIZE challenges.

Main risk: annual competitions leave stale pages indexed, and "open" may mean waitlist or future-cycle interest form.

#### Demographic Founder Programs

Agentic search found Black Ambition, Cartier Women's Initiative, Visible Hands, StartOut Growth Lab, Military Founders Lab, Unshackled Ventures, Tory Burch Foundation Fellows, and digitalundivided BREAKTHROUGH.

Main risk: eligibility depends on sensitive founder attributes, revenue, geography, and current application windows.

#### State/Local/Tax Incentives

Agentic search was weakest here. Tested examples included SSBCI, R&D payroll tax credit, California Competes, START-UP NY, Pennsylvania KIZ Tax Credit, Michigan Business Development Program, and Texas Enterprise Fund.

Main risk: programs are jurisdiction-specific, negotiated, tax/legal-heavy, or not self-serve. A generic founder profile is insufficient.

## Overall Product Recommendations

### 1. Use Multi-Pass Search

Do not use one broad query. Run separate passes for:

- Broad founder profile.
- Resource-type expansion.
- Official databases.
- Non-obvious infrastructure such as lab access, vouchers, CRADAs, and procurement.
- Demographic or identity-specific resources, only when founders provide that information voluntarily.

### 2. Separate Discovery From Validation

Discovery should maximize recall. Validation should check:

- Official URL.
- Current status.
- Deadline or cycle.
- Eligibility.
- Resource type.
- Actionability.
- Confidence.

### 3. Keep a Structured Resource Index

The index should track:

- Canonical resource name.
- Aliases and old names.
- Sponsor.
- Official application URL.
- Resource type.
- Geography.
- Stage.
- Sector.
- Founder eligibility fields.
- Deadlines/cycles.
- Last checked date.
- Status history.
- Evidence quotes.

### 4. Use Different Treatment by Source Type

Agentic search is strongest for:

- Cloud credits.
- Major accelerators.
- Branded national competitions.

Agentic search needs validation for:

- SBIR/STTR.
- Pitch competitions.
- Demographic founder programs.
- University programs.

Agentic search is not enough alone for:

- State/local incentives.
- Tax credits.
- Foundation grants.
- Community resources.
- Wet-lab/coworking availability.
- Government procurement and set-asides.

### 5. Improve Founder Intake

Before search, collect:

- Geography and willingness to relocate.
- Company stage, revenue, funding, and team size.
- Entity type and ownership.
- Sector, technology keywords, TRL, and regulatory path.
- Use of funds/resources.
- University affiliation and IP status.
- Voluntary demographic, veteran, immigration, disability, or student status.
- Preferences around equity, debt, grants, credits, or in-kind support.

### 6. Present Results as Decision States

Instead of a flat directory, show:

- **Apply now.**
- **Track for next cycle.**
- **Possible match; answer these questions.**
- **Useful but not funding.**
- **Needs expert review.**
- **Rejected or stale.**

This matches the observed behavior of agentic search and gives founders a more trustworthy experience.
