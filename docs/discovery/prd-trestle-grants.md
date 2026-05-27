# Trestle — Conversational Personal Assistant for Startup Founders
## Product Requirements Document (v1: Grant Intelligence)

**Date:** 2026-05-23  
**Owner:** Sam (Product)  
**Status:** Draft — pending team feasibility review  
**North Star Metric:** % of active founders who engage with Trestle weekly and report it "saved them time or surfaced an opportunity they would have missed"

---

## 1. Identity: What Trestle Is

Trestle is a **24/7 conversational personal assistant for startup founders**. It learns about you, your company, your stage, your constraints, and your goals over time — then proactively surfaces opportunities, answers questions, and handles research tasks.

**Think of it as:** OpenClaw or Hermes, but purpose-built for founders. Not a single-use tool. Not a chatbot that forgets. A persistent agent that accumulates context about you and gets smarter every conversation.

### v1 Skill: Grant Intelligence
The first skill Trestle ships is **grant matching for medtech/biomed founders**. But the architecture, memory model, and user profile are built to support additional skills without rewriting the core.

### Future Skills (Architecture-Ready, Not Building Now)
| Skill | What It Does |
|---|---|
| **Competitor Tracking** | "You're building a spinal stimulator. Here's what competitors filed with the FDA this quarter. Two raised Series B." |
| **Investor Matching** | "Based on your stage and therapeutic area, here are 5 angels who've funded devices in your class — with warm-intro paths." |
| **Regulatory Timeline Planning** | "If you start pre-submission now, here's your likely FDA pathway with milestones and costs through PMA." |
| **Team & Hiring** | "Your burn is $45K/mo. Here are 3 grant-funded fellowships that could cover a regulatory hire for 18 months." |
| **Office Space / Lab Access** | "Your city has 2 incubator labs with histopathology suites and CLSA-compliant cleanrooms. Below-market rates for startups." |
| **Legal & IP Monitoring** | "A patent was just published in your space. Here's the claim language — it might overlap with your filing." |

**The rule:** New skills plug into the existing founder profile and conversation memory. No rebuilding the user model. No new onboarding. The agent already knows you.

---

## 2. Problem Statement (v1 Focus: Grants)

Current grant discovery tools fail medtech/biomed founders in three ways:

1. **Form fatigue**: Competitors ask 80+ static questions, produce generic lists, and "still sound like ChatGPT." A founder with a benchtop prototype and a founder with FDA clearance answer the same forms and get the same results.
2. **Size blindness**: Tools surface $50K–$100K Phase I SBIR grants to founders who need $500K+ to survive a 5–10 year regulatory timeline. A $100K grant is 2–3 months of burn. It moves no regulatory needle. It loses the tool's credibility instantly.
3. **No follow-up**: Founders' situations change weekly — new data, new regulatory stage, new burn rate. Forms are snapshots. Grants are fluid. No tool remembers what changed and nudges when a new matching solicitation opens.

The result: medtech founders default to manual grant hunting or skip grants altogether and raise dilutive capital too early.

---

## 3. Target Personas

These personas apply to Trestle as a whole. Grants is the v1 use case, but the same founders will use competitor tracking, investor matching, and regulatory planning as skills come online.

### Primary — The First-Time PhD Founder (Pre-Seed)
**Archetype:** Dr. Sarah Chen, 31, postdoc, benchtop prototype, zero commercialization experience. Burn ~$12–15K/mo. Needs $500K+ of non-dilutive funding to reach first regulatory milestone. Scientifically precise; allergic to marketing language.
**Pain:** "Which NIH institute targets my device? Do I need FDA 510(k) or De Novo? Everyone says write an SBIR but I don't know where to start."

### Secondary — The Pivoting Biotech Entrepreneur (Seed → Series A)
**Archetype:** Amir Patel, 38, second-time founder, first company died mid-trial. Burn ~$40–60K/mo. Needs a capital-stack strategy, not a list.
**Pain:** "I raised a $500K seed and thought that'd get me to FDA. It didn't. I need $5M+ without giving away 40%. Where's the middle path?"

### Tertiary — The EU/UK-Based Founder (Pre-Seed → Seed)
**Archetype:** Dr. Elena Rossi, 35, Cambridge PhD, CE-1 prototype. Burn ~$15–25K/mo. Needs EU/US regulatory pathway comparison and Horizon consortium matching.
**Pain:** "Horizon grants are massive but the application is 80 pages. Is it worth it? Do I go CE or FDA first?"

---

## 4. Proposed Solution

### One-Sentence Pitch
A 24/7 conversational personal assistant that learns each founder's startup, constraints, and goals through natural dialogue — then proactively surfaces opportunities, starting with grants they'll actually qualify for, in the right sequence, with actionable next steps.

### Not a Chatbot. Not a Form. An Agent.

| What a chatbot does | What Trestle does |
|---|---|
| Answers one question and forgets | Remembers "last time you said NIH submission in October" and checks in |
| Outputs lists of 50 grants | Filters to 3–5 highly relevant matches with **why this fits** and a **clickable source URL** |
| Asks 80 questions up front | Asks 3–5 adaptive questions, then pivots: "You said preclinical — GLP data or benchtop?" |
| Surfaces $100K grants to everyone | Hard-filters by minimum grant size, funding stage, regulatory fit |
| Sounds generic | Knows SBIR Phase I vs II, DoD CDMRP, ARPA-H, BARDA, EIC Accelerator |
| Built for one task | Built to accumulate skills — grants today, investor matching tomorrow |

### The Founder Profile: What Trestle Learns About You

Trestle doesn't ask "What grants do you want?" It asks "Tell me about your startup." From conversation, it builds a persistent **founder profile** that all skills access:

```
FOUNDER PROFILE (general-purpose, not grant-specific)
├── Company basics
│   ├── Name, stage (pre-seed/seed/Series A)
│   ├── Location (US city / EU country)
│   ├── Incorporation type
│   └── Team size + roles
├── Product & regulatory
│   ├── Device/drug/diagnostic?
│   ├── Indication / therapeutic area
│   ├── Current data status (benchtop / GLP / clinical / FDA-cleared)
│   └── Regulatory pathway if known (510(k) / De Novo / PMA / CE)
├── Financials
│   ├── Monthly burn rate
│   ├── Runway months remaining
│   ├── Last raise amount + date
│   └── Capital need (next 12–18 months)
├── Eligibility signals (skill-populated)
│   ├── Company age, employee count, revenue
│   ├── IP ownership status
│   └── Prior SBIR awards, SBIR-eligible entity?
└── Preferences
    ├── Minimum grant size threshold ($300K default)
    ├── Geographic scope (US-only, UK, EU, multi-region)
    └── Alert frequency (daily / weekly / none)
```

This profile is **not rebuilt per skill**. Grant matching reads `Company basics`, `Product & regulatory`, and `Eligibility signals`. Investor matching reads the same fields plus `Financials`. Competitor tracking reads `Product & regulatory`. The agent enriches the profile across all skills as it learns more.

### Core Loop — The "Discovery → Skill Match → Nudge" Cycle

```
FOUNDER                                TRESTLE
  |                                      |
  |--- "I'm Sarah. Building a spinal ---|
      cord stimulation device. Preclinical.  |
      Need $2M for a 30-patient feasibility  |
      study by Q2 2027."                   |
         |                                 |
         | (builds founder profile)          |
         |                                 |
  |<---- "Got it, Sarah. Tell me: are ---|
         you incorporated in the US?        |
         What's your current burn rate?"    |
         |                                 |
  |--- "Delaware C-corp. Burn is $14K ---|
      per month. We have 8 months runway."  |
         |                                 |
         | (profile enriched; skills now   |
         |  ready to match)                  |
         |                                 |
  |<---- "Here's what I found for you ---|
         across my skills:                   |
                                          |
         ┌─ GRANT MATCHES (3 found) ─┐   |
         │ NIH R01-equivalent + SBIR   │   |
         │ Phase II for neuro devices  │   |
         └───────────────────────────────┘ │
                                          |
         Also: competitor alert — a team  |
         at Stanford published preclinical  |
         data on a similar device last     |
         month. Want me to track them?"    |
         |                                 |
         |   (memory: nudges when new      |
         |    solicitations open, checks    |
         |    if timeline shifted)          |
         |                                 |
```

**Key design principle:** The agent builds the founder profile *before* it pitches any skill. The first conversation is about *you*, not about *grants*. Once the profile is rich enough, Trestle says: "Here's what I can help you with." The founder picks.

### Key Differentiator: Eligibility Before Listing (v1: Grants Skill)

Trestle interrogates eligibility constraints **conversationally**, then filters:
- **Funding stage** (pre-seed → Series A maps to different grant pools)
- **Company age** (SBIR caps at 500 employees; EIC Accelerator has revenue caps)
- **Industry/regulatory path** (device class, clinical data status, GLP vs GMP)
- **Location** (US → NIH/NSF/DoD/ARPA-H/BARDA; UK → Innovate UK; EU → Horizon/EIC)
- **Minimum grant size** (default filter: $300K+, configurable)
- **Every match includes a direct source URL** (grants.gov, sbir.gov, ec.europa.eu, etc.) — not text attributions like "from the SBA"

If a grant doesn't match, it doesn't appear. Period.

### Post-Match Lifecycle

A match is not the end — it's the start of a **6-18 month relationship**. Trestle tracks every grant through a complete lifecycle:

`DISCOVERED → SAVED → INTERESTED → STARTED → APPLIED → SUBMITTED → UNDER_REVIEW → ACCEPTED → AWARDED → ARCHIVED`

With full rejection, abandonment, and reconsideration paths. See **[post-match-lifecycle.md](./post-match-lifecycle.md)** for the complete 14-state state machine, all 50+ transitions with trigger conditions, proactive nudges, and every sad path.

**What this enables:**
- Trestle can report: "3 grants in progress, 1 under review, 1 awarded"
- Trestle learns which grant types convert for which founder profiles
- Trestle adapts weighting when a founder consistently gets rejected by NIH but accepted by DoD
- Trestle can plan strategically: "Your next best move is Grant X, due in 45 days"

---

## 5. Auth & Session Architecture

Trestle uses a **delayed-auth** model — demonstrate value before asking for identity. See **[auth-flow.md](./auth-flow.md)** for the full specification covering:

- **Anonymous sessions** (no signup, instant entry)
- **Signup triggers** at natural value moments (saving a grant, tracking a deadline)
- **Return user recognition** via 6-layer fallback chain (JWT → device fingerprint → Telegram user_id)
- **Session merge** — anonymous data survives into authenticated accounts
- **Every sad path** — expired links, lost sessions, device sharing, email bounce, JWT compromise

Auth flow principle: *Let them use Trestle for 5 minutes, fall in love with a match, then ask for the account.*

---

## 6. Demo Success Criteria

To call the demo a win (for Maurinne and her Nucleate cohort):

| Metric | Baseline | Target | How measured |
|---|---|---|---|
| Time-to-first-match | 45 min (form-filling competitors) | < 5 min | Stopwatch from first message to displayed match |
| Match relevance score | 3–5 random grants | 3–5 filtered matches with eligibility rationale per match | Qualitative review with 3 founders |
| Conversational question count | 80+ questions | ≤ 5 adaptive questions | Completion flow log |
| Founder retention (return within 7 days) | N/A — new product | ≥ 50% | Product analytics |
| Proactive alert open rate | 0% (competitors don't do alerts) | ≥ 30% of alerts opened within 24h | Event tracking |

---

## 7. Out of Scope — Not Building (v1)

| Item | Why cut | When revisited |
|---|---|---|
| **Grant application drafting / auto-submission** | Regulatory complexity is too high; one wrong field kills an NIH submission | v3 — after legal review |
| **Investor matching (VC/angel)** | Future skill, but requires different data sources and trust model | v2 — grants loop proven, then add as skill |
| **Competitor tracking** | Future skill — requires FDA 510(k) scraping, PubMed monitoring, etc. | v2 — after grants skill is sticky |
| **Maurinne's batch/cohort dashboard** | Audience #2. Founder-facing agent first, accelerator-operator dashboard second | v2 — once individual usage proven |
| **Real-time grant database sync (live API feeds)** | Manual curation is faster to ship and more accurate in early days | v2 — when scale demands automation |
| **Multi-language support** | All initial personas are English-speaking; translation adds complexity | v3 — when Nucleate's non-English cohorts speak up |
| **Mobile app** | Telegram/WhatsApp bot is sufficient for a conversational agent MVP | v3 — if retention justifies native |

**Descoping rationale:** If we can't get a single founder to say "this actually found me a grant I'd have missed" in 30 days, nothing else matters. The architecture supports future skills, but v1 ships grants and nothing else.

---

## 8. Key Assumptions & Open Questions

### Assumptions
1. Founders will talk to an agent about their burn rate, regulatory stage, and IP. (Some are cagey with investors; will they be cagey with a bot that remembers?)
2. A curated grant database of ~200 grants, updated weekly, is enough to feel "comprehensive" for medtech.
3. "Conversational" matters more than "comprehensive." A founder who gets 3 great matches in 5 minutes is happier than one who gets 50 mediocre matches in 45 minutes.
4. **New:** A general-purpose founder profile is actually general enough. Do investor-matching and competitor-tracking need fields this profile doesn't capture?

### Open Questions (team review needed)
1. **Aurthur (Architect):** Does the skill architecture need a plugin system (separate modules per skill) or can skills be prompt-based with shared state? How does one skill's data enrich the founder profile for others?
2. **Jason (Backend):** Founder profile schema — one JSON blob or normalized tables? How do we handle schema evolution when new skills need new fields?
3. **Floyd (Frontend):** Conversation UI — how does the founder switch between skills mid-chat? "Trestle, switch to investor matching" or persistent tabs?
4. **ScoutBot:** What's the realistic API landscape for SBIR/NIH/EICAccelerator? Do we scrape or partner?
5. **Sam (Product):** How do we handle dead/changed URLs? Do we verify links before presenting? Store in DB alongside grants?
6. **Sam (Product):** Should Trestle proactively suggest new skills as they're released? "I noticed you raised a seed — want me to track competitor filings?" Or wait for the founder to ask?

---

## 9. Team Feasibility Gates

Before this PRD is sent to Arceus for approval:
- [ ] Aurthur signs off on architecture: conversational memory + skill plugin model + eligibility scoring engine
- [ ] Jason signs off on data model: founder profile schema (general-purpose) + grant schema
- [ ] Floyd signs off on UI estimate: chat interface with match cards + skill-switching UX
- [ ] Jim checks deploy/compute: LLM inference costs per conversation

---

*No. Show me the metric it moves. Ship 50% of this idea in 3 days, not 100% in 3 weeks.*
