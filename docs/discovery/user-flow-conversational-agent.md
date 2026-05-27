# Trestle — Full Lifecycle User Flow

**Paradigm:** Trestle is a conversational personal assistant, NOT a grant-matching tool. Grants are v1 of many skills. Every interaction is dialogue. The agent remembers, reasons, and builds a relationship with the founder across sessions.

**Design principles:**
- Auth before value = dead. Demonstrate value, then ask for identity.
- Every match includes a clickable source URL. Always.
- Every action has a sad path. No happy-path-only flow design.
- The match is the hook. The lifecycle is the product.

---

## Tone & Personality

- **Personality:** Sharp, helpful, founder-friendly. Not corporate. Not chatty for chatty's sake.
- **Voice:** "Your well-connected friend who knows the grant landscape cold."
- **Trust Building:**
  - Always links to the **official source URL** (e.g., `https://grants.gov/...`). Never settles for text attribution.
  - Says "I don't know" when it doesn't know. Never hallucinates benefits.
  - Learns the founder's preferences over time and adjusts recommendations.
  - Remembers past conversations — "Last time you said you were bootstrapped. Has that changed?"
- **Session Memory:** Industry, stage, location, funding raised, team size, years in business, grants already applied to, grants dismissed and why.

---

## Flow 0: Auth — Who Is This?

Auth is integrated into every flow, not a separate gate. See **[auth-flow.md](./auth-flow.md)** for the full state machine and 50+ sad paths.

### Decision Tree (Entry)

```
USER APPROACHES TRESTLE
│
├── [FIRST VISIT — no cookie, no JWT, no Telegram]
│   → Anonymous session created (UUID v4, localStorage + cookie)
│   → Proceed to Flow 1: First Contact
│   → No auth prompt. Value first.
│   │
│   ├── [SAD PATH] User clears cookies mid-session
│   │   → Fresh anonymous session. Data from old session is gone.
│   │   → Agent: "Welcome back! Or is this your first time?"
│   │
│   └── [SAD PATH] User on shared device
│       → Multiple users in rapid succession detected
│       → Disable auto-login. Always prompt: "Is this [Name]? Or someone else?"
│
├── [RETURN VISITOR — cookie/JWT detected]
│   │
│   ├── Valid JWT → Authenticated. Resume full history. Skip to Flow 3.
│   │
│   ├── Expired JWT → Silent refresh. No user-facing interruption. Resume.
│   │   └── [SAD PATH] Refresh fails → Treat as anonymous. Re-prompt signup.
│   │
│   ├── Device fingerprint + cookie (anonymous return)
│   │   → Agent: "Welcome back! Your last session was [X days] ago.
│   │             You were looking at SBIR grants for your neuro device.
│   │             Still relevant?"
│   │   → User response:
│   │       ├── "Yes" → Resume. Go to Flow 3 (or Flow 4 if in-progress grants).
│   │       ├── "No, things changed" → Update profile. Re-run match.
│   │       └── "I'm new" → [SAD PATH] Reset fingerprint. Fresh session.
│   │
│   └── Telegram user_id detected
│       → Full auth via Telegram session. Resume with history.
│
├── [SIGNUP TRIGGER — during session]
│   Trigger events (any ONE fires the prompt):
│   │ 1. User says "save this grant" or clicks "Track Grant"
│   │ 2. User says "remind me about the deadline"
│   │ 3. User returns for 3rd+ session
│   │ 4. Agent needs to send proactive alert (deadline, new match)
│   │ 5. User explicitly asks "will you remember this?"
│   │
│   → Soft prompt (not a modal):
│   │ "If you create an account, I'll remember all these matches and
│   │  nudge you when deadlines approach. Want to do that now?
│   │  (No account needed to keep browsing.)"
│   │
│   ├── User accepts → Start signup (email + magic link, or Telegram)
│   │   → Session merge: all anonymous data moves to user record
│   │   → Agent: "Done. All your [N] matches are saved."
│   │   │
│   │   ├── [SAD] Email bounces → "Check spam. Want me to resend or try Telegram?"
│   │   ├── [SAD] Link expired (15 min) → "That link expired. Want a new one?"
│   │   ├── [SAD] Session ID lost (different device) → Fresh account, no history merge
│   │   └── [SAD] Duplicate email → "Already have an account. Log in instead?"
│   │
│   └── User declines
│       → Still persists to anonymous session. Count increment.
│       ├── Declined 3x total → Stop prompting. Mark no_auth: true.
│       │   Agent still works, but warns on session boundaries.
│       └── [SAD] User never signs up → Session expires after 30 inactivity days.
│           "Your old session expired. Let's start fresh."
│
└── [LOGOUT]
    → JWT invalidated. Session cleared. Device fingerprint preserved.
    → Agent: "Logged out. Your data is saved. Log back in anytime."
    ├── [SAD] Accidental logout → "You're logged out! Were you looking for something?"
    └── [SAD] Account deletion → Confirm: "This deletes everything. Export first?"
```

---

## Flow 1: First Contact

### Goal
Get from "visitor on landing page" to "active conversation" with zero friction. No auth gate. No form. Just talk.

### Conversation State Diagram
```
[Visitor sees landing page]
  → [CTA click or message "Hey Trestle"]
  → [Auth check — anonymous or return?]
  → [Agent introduces itself]
  → [User responds]
```

### Agent Actions
1. **Trigger:** Click "Talk to Trestle" or start chat widget.
2. **Auth check:** Session lookup (see Flow 0).
3. **Introduction (scripted, but warm):**
   > "Hey — I'm Trestle. I help founders find grants they actually qualify for. What's your company working on?"
4. **Fallback if no response in 10s:**
   > "No pressure. Tell me about your startup whenever you're ready, or I can show you what's currently open."

### User Actions
- Type freely about their company.
- Ask "What do you do?"
- Say "I'm looking for grants."
- Ignore the message (bounce).

### Decision Tree

```
USER OPENS CHAT
│
├── [Anonymous return user detected]
│   → Skip intro. Greet by topic from previous session.
│   │   "Welcome back! You were looking at SBIR grants last time.
│   │    Still relevant, or is this a new direction?"
│
├── [User describes business]
│   → Flow 2: Discovery Dialogue
│   │
│   ├── [SAD] User describes something that doesn't match grants
│   │   → Agent says what Trestle does. If no fit, says so honestly.
│   │   → "I focus on grant opportunities. If that's not useful,
│   │      I can still help with general startup guidance within my scope."
│   │
│   └── [SAD] User info conflicts with eligibility criteria
│       → "I want to check something — you said you're pre-seed
│          but also mentioned FDA clearance. Can you clarify?"
│
├── [User asks "what do you do?"]
│   → Brief elevator pitch + suggest starting with their business
│   │   "I'm a personal assistant for founders. I find grants,
│   │    track deadlines, and learn your company over time.
│   │    Tell me about your startup and I'll show you what's available."
│
├── [User asks about specific grant by name]
│   → Flow 5: Deep Dive (bypass discovery)
│   │
│   └── [SAD] Grant not in database
│       → "I don't have that one in my database yet. I can add it.
│          In the meantime, here are [2-3] that are similar."
│
├── [No response in 60s]
│   → End session. Landing page shows "Ask me anything about grants" as prompt.
│   → [SAD] User never returns → No data lost (anonymous session expires after 30 days).
│
└── [User says "I'm not a founder"]
    → "No problem. I'm specifically built for startup founders.
       If you know a founder who might need grant help, send them my way."
```

### Sample Dialogue (Return User)
```
Agent:  Welcome back! Your last session was 11 days ago.
        You were looking at SBIR grants for your neurostim device.
        Still relevant, or has anything changed?
User:   We actually just raised our seed round
Agent:  Congrats on the raise. That changes your grant landscape.
        Some grants close when you cross $X raised — let me re-run
        your match to show what's still open.
```

---

## Flow 2: Discovery Dialogue

### Goal
Extract founder profile NATURALLY through back-and-forth. No form. No interrogation. Ask 1-2 questions at a time, follow the user's lead.

### Fields to Extract
| Field | Why It Matters | How the Agent Learns It |
|-------|---------------|------------------------|
| Company stage | Determines SBIR/STTR phase eligibility | "How far along are you?" |
| Industry | Many grants are industry-specific | "What space are you in?" / inferred from user description |
| Location | State/local grants vary wildly | "Where are you based?" |
| Funding raised | Some grants require <$X raised | "Are you bootstrapped or have you raised?" |
| Team size | SBIR caps at 500 employees | "How many people on the team?" |
| Years in business | Some grants need <3 years, others >2 | "How long have you been at this?" |
| Previous grants applied to | Avoid duplicates, know what's in flight | "Have you applied to anything before?" |

### Agent Strategy
- **Never ask more than 2 questions in a row.** Let the user talk.
- **Infer when possible.** If they say "pre-seed," infer stage and team size. If they say "SBIR Phase I before," infer experience level.
- **Allow skipping.** "If you don't want to share revenue numbers, that's fine — I can still give you a direction."

### Decision Tree

```
DISCOVERY DIALOGUE
│
├── User provides complete info → Flow 3: Eligibility Matching
│
├── User provides partial info
│   → Ask only what's missing. Max 2 questions at a time.
│   │
│   ├── User fills gaps → Flow 3
│   │
│   ├── User refuses to answer → Flow 3 with partial data
│   │   → Warning: "Some grants have [X requirement]. Without knowing
│   │      yours, I'll flag uncertain matches. You can update anytime."
│   │
│   ├── [SAD] User info contradicts itself
│   │   → "I want to clarify — you said 'pre-seed' but also 'FDA clearance.'
│   │      FDA clearance usually comes after seed stage. Which is right?"
│   │   ├── User clarifies → Profile updated.
│   │   └── User doubles down → "I'll note both. Let me keep looking."
│   │
│   └── [SAD] User provides info that disqualifies ALL grants
│       → "Based on what you've told me, most grants right now require
│          US incorporation or a minimum team size. Want to discuss
│          what would make you eligible in the future?"
│       └── User interested → Roadmap conversation
│
├── [SAD] User gets overwhelmed
│   → "That's enough for now. I have enough to start finding matches.
│      Want to see what I found, or keep talking?"
│
└── [SAD] User contradicts session memory from previous visit
    → "Last time you said you were incorporated in Delaware. Has that changed?"
    ├── User confirms change → Update profile. Re-run match.
    └── User corrects memory → "Good catch. I'll update that."
```

### Sample Dialogue
```
Agent:  What does your company do?
User:   We're automating medical billing with AI
Agent:  Got it — so healthcare tech. How far along are you?
        Still building, have customers, or scaling?
User:   We have 8 hospital customers, about $200K ARR
Agent:  Nice traction. Are you bootstrapped, or have you raised?
User:   We raised a $500K pre-seed
Agent:  Okay, that rules out a few grants that require <$100K raised,
        but opens up others. Where are you incorporated?
User:   Delaware, but ops are in Austin
Agent:  Texas has some solid state-level programs.
        Let me check what matches your profile.
```

---

## Flow 3: Eligibility Matching

### Goal
Present ONLY grants the user is genuinely eligible for, with clear explanation of WHY each matches and a clickable source URL.

### Agent Actions
1. **Internal matching:** Cross founder profile against grant database (federal, state, local, private).
2. **Filtering logic:**
   - Hard reject if stage/location/funding/team disqualifies.
   - Soft flag if uncertain (e.g., "This grant says 'manufacturing' — your AI-for-hospitals could qualify if you frame the POC right").
3. **Presentation (max 3 at a time):**
   > "I found 2 grants that look like strong matches for a healthcare AI startup at your stage:
   >
   > **1. NIH SBIR Phase I** — Up to $400K for health tech R&D. You're eligible because you have working product + pilots. Due: June 30.
   > → https://grants.gov/search-guide.html
   >
   > **2. Texas Enterprise Fund** — State match for healthcare startups relocating jobs to TX. You're in Austin, but this requires 10+ new jobs. Flagging as partial.
   > → https://gov.texas.gov/business/texas-enterprise-fund"

4. **Always include:** Why the user is eligible, deadline, rough dollar amount, **clickable source URL**, and one-click "Tell me more" or "See more alternatives."

### Decision Tree

```
MATCHING PRESENTED
│
├── User likes a match
│   → Flow 4: Post-Match Lifecycle (SAVED state)
│   │
│   ├── User says "tell me more" → Flow 5: Deep Dive
│   └── User says "track this" → Add to tracking list. Set deadline reminder.
│
├── User rejects a match
│   → Ask why (store for learning)
│   │
│   ├── "Not enough money" → Raise min grant size filter. Show next tier.
│   ├── "Wrong category" → Adjust industry tags. Re-run match.
│   ├── "Deadline too soon" → Filter out imminent deadlines. Show later ones.
│   ├── "Already applied" → Update grants_applied list. Move to SUBMITTED.
│   └── "No reason" → Store as dismissal. No profile changes.
│
├── 0 matches found
│   → "I couldn't find any grants that match your profile directly.
│      Here's what's close and what you'd need to change:
│      - [Grant A] requires [X] — you're at [not X]
│      - [Grant B] requires [Y] — you're close on this
│
│      Want to explore any of those near-matches, or discuss
│      what would make you more eligible?"
│   │
│   ├── User wants to explore near-matches → Show with "partial" label
│   └── User says "nothing useful" → Ask for feedback. Log zero-result query.
│
├── 10+ matches found
│   → "I found 12 matches. Let me show the top 3 first."
│   → Filter by confidence (strong / partial / informational)
│   │
│   ├── User says "show all" → Display with confidence labels.
│   │   [SAD] User overwhelmed → "That's a lot. Want to narrow by
│   │   minimum grant size or specific agency?"
│   └── User asks to narrow criteria → Apply filters. Re-present.
│
└── [SAD] User says "these are useless"
    → "Tell me what went wrong — was the eligibility wrong?
      The fit? I'll learn from it."
    └── Pattern across 3+ sessions → Flag for product team. Spiral detection.
```

---

## Flow 4: Post-Match Lifecycle

### Goal
Track every grant from "discovered" through "applied" to "awarded" — handling every dead end along the way.

### State Machine (Complete)
```
DISCOVERED → SAVED → INTERESTED → STARTED → APPLIED → SUBMITTED → UNDER_REVIEW
                                                                              ↓
                                                          ┌─ ACCEPTED → AWARDED → ARCHIVED
                                                          │
                                                          └─ REJECTED → RECONSIDERING → STARTED (reapply)
                                                                             ↓
                                                                       DISMISSED → ARCHIVED
```

**14 states defined:**
| # | State | Description | How Entered |
|---|-------|-------------|-------------|
| 1 | DISCOVERED | User saw the grant. No action taken. | Auto (matching result) |
| 2 | SAVED | User bookmarked it. No commitment. | User action |
| 3 | INTERESTED | User said "tell me more" or "I'm interested." | User action |
| 4 | STARTED | User began prep (reading guidelines, assembling team). | User action or inferred |
| 5 | APPLIED | User submitted application. | User announces |
| 6 | SUBMITTED | Agent confirmed submission went through. | User confirms receipt |
| 7 | UNDER_REVIEW | Grant agency is reviewing. Waiting period. | Time-based |
| 8 | ACCEPTED | User notified of acceptance. | User announces |
| 9 | AWARDED | Funds received. Grant active. | User confirms funds |
| 10 | REJECTED | User received rejection. | User announces |
| 11 | RECONSIDERING | User wants to reapply next cycle. | User action |
| 12 | DISMISSED | User explicitly declined. | User action |
| 13 | ABANDONED | No activity for 90+ days. | Auto (agent) |
| 14 | ARCHIVED | Lifecycle fully closed. No further action. | Auto or user |

See **[post-match-lifecycle.md](./post-match-lifecycle.md)** for all 50+ transitions with trigger conditions, agent actions, and every sad path.

### Decision Tree (Per Grant)

```
USER SEES A GRANT MATCH
│
├── DOES NOTHING → DISCOVERED
│   └── [30 days no action] → Auto-archive if never interacted
│
├── SAVES IT → SAVED
│   → Agent: "Saved to your list. Want me to check back when applications open?"
│   │
│   ├── Says "yes" → Move to INTERESTED. Set deadline reminder.
│   ├── Says "no" → Stay SAVED. No tracking.
│   │   └── [SAD] Save duplicate → "Already in your saved list."
│   └── Ignores prompt → Stay SAVED. No deadline tracking.
│
├── SAYS "TELL ME MORE" → INTERESTED
│   → Agent: "Great choice. I'll track this one — due [date].
│     Start deadline monitoring. Set 30-day check-in timer.
│   │
│   ├── User starts prep (asks about budget, structure) → STARTED
│   │   └── [SAD] User says "almost there" but never submitted
│   │       → Agent checks in at 7 days pre-deadline
│   │       └── Deadline passes → Auto-ABANDONED after 7 days silence
│   │
│   ├── User submits application → APPLIED
│   │   → Agent: "Did you get a confirmation email from the agency?"
│   │   ├── Yes → SUBMITTED. Start review-waiting timer.
│   │   ├── No/Unsure → "Noted as submitted. Follow up in 3 days?"
│   │   └── [SAD] Confirmation never confirmed (14 days) → Agent asks
│   │
│   ├── SUBMITTED → UNDER_REVIEW (time-based, ~30 days)
│   │   → Expected decision date computed from grant metadata
│   │   → 50% check-in: "Any updates? Need anything?"
│   │   └── [SAD] Review takes longer → "That's normal. Check again in 30d."
│   │
│   ├── UNDER_REVIEW → ACCEPTED
│   │   → Agent celebrates: "That's huge. Congratulations!"
│   │   → Asks for award amount and terms
│   │   ├── User shares → Agent recalculates runway
│   │   └── [SAD] User cagey about amount → "No problem. What's next?"
│   │
│   ├── ACCEPTED → AWARDED (30 days post-acceptance or user confirms)
│   │   → "Funds in? Let me recalculate your runway."
│   │   └── [SAD] Disbursement delayed → "Some take 60-90 days."
│   │
│   ├── UNDER_REVIEW → REJECTED
│   │   → Agent: "Sorry to hear that. Did they give a reason?"
│   │   ├── Feedback received → Update profile. Suggest alternatives.
│   │   ├── No feedback → Show similar grants. Different panel.
│   │   └── [SAD] User devastated → "Rejection is the norm. 5-10 per win.
│   │         No pressure to jump back in."
│   │   │
│   │   ├── REJECTED → RECONSIDERING
│   │   │   → "Next cycle opens [date]. Want help tracking what to change?"
│   │   │   └── [SAD] Reapplication not allowed (12-month cool-off)
│   │   │       → Show alternatives for the gap
│   │   │
│   │   ├── RECONSIDERING → STARTED (reapplication)
│   │   │   → Full lifecycle restart with attempt_number: 2
│   │   │   → Agent knows previous rejection reason
│   │   │
│   │   └── RECONSIDERING → DISMISSED
│   │       → User says "done" or 90d no activity
│   │
│   └── USER GHOSTS (no activity 90 days) → ABANDONED
│       → Agent sent 2 check-ins (day 30, day 60)
│       → "I've paused tracking. Your notes are saved."
│       └── Re-entry → "Welcome back! Deadline passed but next cycle opens [date]."
│
├── DISMISSES GRANT → DISMISSED
│   → Agent: "Why not? Helps me avoid similar ones."
│   ├── "Not enough money" → Raise min grant size filter
│   ├── "Wrong category" → Adjust industry tags
│   ├── "Deadline too soon" → Filter imminent deadlines
│   ├── "Already applied" → Move to APPLIED instead
│   └── No reason → Store as unspecified
│
├── MULTIPLE GRANTS IN FLIGHT
│   → Agent tracks independently. Nudges per-grant, not batched.
│   └── [SAD] Overwhelm detected → "You've got 5 grants in progress.
│       Want to prioritize one?"
│
└── [SAD] USER CHANGES SITUATION
    → "You mentioned a raise / pivot / move. That changes your grants.
       Here's what opened and what closed."
    → Re-run matching for all tracked grants.
```

### Proactive Nudges (Time-Based)

| Nudge | Timing | Template |
|-------|--------|----------|
| Deadline approaching | 30 days before | "[Grant] due in 30 days. Want help starting?" |
| Deadline imminent | 7 days before | "[Grant] due in 7 days. Now's the time." |
| Deadline passed (not submitted) | 1 day after | "Deadline passed. Next cycle opens [date]. Remind you?" |
| Review halfway | 50% of review period | "Your [Grant] has been under review for [X] months. Any word?" |
| Decision expected | Expected decision date | "Your [Grant] decision should be in soon." |
| Decision overdue | Decision date + 30 days | "Decision is overdue. Might be worth checking with the agency." |
| Reconsideration window | Next cycle + 1 day | "[Grant] is open again. Try with what you learned?" |
| No activity (tracked grant) | 30 days since last change | "No movement on [Grant]. Still planning to apply?" |
| Grant updated in DB | When new data available | "[Grant] increased award cap. You now qualify for $[X]." |

---

## Flow 5: Deep Dive

### Goal
User asks about a specific grant. Agent provides FULL breakdown: eligibility, deadlines, requirements, application tips, and why it fits this user.

### Agent Actions
- Break down into: Eligibility, Deadlines, Budget, Application tips, Common pitfalls.
- Link to official sources (NIH ASSIST, SBA, state portals).
- Offer next steps: "Track this," "Find grant writer," "Set deadline reminder."

### Decision Tree

```
USER ASKS ABOUT A GRANT IN DETAIL
│
├── Grant is in database
│   → Full breakdown (see sample dialogue below)
│   │
│   ├── User wants to track it → Flow 4 (INTERESTED state)
│   ├── User wants to dismiss it → Flow 4 (DISMISSED state)
│   └── User asks follow-up questions → Deeper dive
│       │
│       ├── [SAD] Agent doesn't know the answer
│       │   → "I don't have that data yet. Let me find out."
│       │   └── "I found [answer]" or "I couldn't find that. Here's the
│       │       official source to check: [URL]"
│       │
│       └── [SAD] User asks about grant that doesn't exist
│           → "That doesn't match any grant in my database.
│              Did you mean [similar grant name]?"
│
├── Grant not in database
│   → "I don't have that one yet. Here are [2-3] similar grants
│      in the same category."
│   └── [SAD] User insists → "I'll add it to my research list."
│
└── [SAD] Grant eligibility changed since last match
    → "[Grant Name] updated their criteria. Let me double-check your profile."
```

### Sample Dialogue
```
User:   Tell me about the NIH SBIR
Agent:  NIH SBIR Phase I awards up to $400K for health-related R&D over 6-12 months.
        You'd apply through the NIH ASSIST portal.

        **Eligibility (for you):**
        - US-owned, <500 employees ✓ (you're 6 people)
        - Primary work in US ✓ (Austin)
        - For-profit business ✓
        - PI employed >10 hrs/week by applicant ✓

        **Your odds:**
        Your 2 pilots help — NIH likes proof the tech works in real clinical settings.
        Healthcare AI is a priority area for FY26.

        **Deadlines:**
        Standard submission: June 30 → https://grants.gov/apply
        Letter of intent: Optional but recommended, due June 1 → https://grants.gov/loi

        **Red flags to avoid:**
        - Don't double-dip with NSF for the same project
        - Budget needs to be 67%+ on direct costs

        Want me to walk through the budget template, or help you find an experienced grant writer?
```

---

## Flow 6: Edge Cases (Exhaustive)

### Case 1: Agent Is Wrong
```
User:   "You said I qualify for the Texas Enterprise Fund but I'm remote-only, no office."
Agent:  "You're right — my bad. The Texas Enterprise Fund requires a physical presence.
         I'll update that in your profile. Let me re-run the match without it."
Action: Own the mistake, correct instantly, update memory.
```

### Case 2: New Info Changes Eligibility
```
User:   "We just crossed 500 employees last month."
Agent:  "Whoa — that's huge. It means you no longer qualify for SBIR (hard cap at 500),
         but you unlock SBA 7(a) loans and some corporate innovation programs.
         Want a fresh search?"
Action: Flag profile change, re-run matching, explain what opened vs what closed.
```

### Case 3: User Disagrees With Recommendation
```
User:   "This grant is useless for my business."
Agent:  "What am I missing? If you tell me why it's off, I'll avoid similar ones next time."
Action: Don't argue. Ask for feedback. Update dismissal reasons. Learn.
```

### Case 4: User Is Vague or Uncertain
```
User:   "I don't really know what stage we are."
Agent:  "No worries — common problem. Do you have revenue?
         Do you have a product people actually use? Those are the key ones."
Action: Simplify, reframe, let user self-identify.
```

### Case 5: User Is Defensive About Info
```
User:   "I'm not sharing revenue numbers."
Agent:  "Totally fair. I'll work with what you've given me. Just know that a few grants
         have revenue caps, so I might show you one you're actually over the limit for
         — you'll need to self-filter those."
Action: Respect boundary, note limitation openly, continue anyway.
```

### Case 6: Spiral Detection
```
Scenario: User rejected from 3+ grants in <30 days
Agent: "You've had a rough streak. Want me to review your profile
        and adjust the filter criteria?"

Scenario: User accepted 3+ grants
Agent: "You're on a roll. Some awards have reporting requirements.
        Want me to track those?"
```

### Case 7: Grant Database Quality Issues
```
Scenario: Source URL is dead (404)
Agent: "The official page for this grant seems to be down. Grant info was
        last verified [date]. Want me to search for an updated link?"

Scenario: Grant expired/closed
Agent: "It looks like this grant cycle has closed. Here are [2-3] current alternatives."

Scenario: Grant cancelled by agency
Agent: "[Grant] was cancelled by the agency. I'll remove it. Here are similar alternatives."
```

### Case 8: Data Contradictions
```
Scenario: User says "I submitted" but deadline is in 3 months
Agent: "Just confirming — the deadline is [date in 3 months].
        Did you submit for a different cycle?"

Scenario: User says "got rejected" but status shows not submitted
Agent: "I didn't have a submission recorded. Did you submit it elsewhere?"
```

### Case 9: User Ghosting
```
Day 30:   "Still looking for grants?" → No response
Day 45:   "Haven't heard from you — should I archive your matches?" → No response
Day 90:   → ABANDONED state. Stop notifications.
Re-entry: "It's been a while. A lot has changed. Want to rebuild your profile
           or pick up where you left off?"
```

---

## Flow 7: Future Skills (Architecture)

Trestle is a general personal assistant, not a grant tool. Grants is v1. Future skills plug into the same founder profile:

| Skill | What It Does | How It Uses the Profile |
|-------|-------------|------------------------|
| Competitor Tracking | Monitors FDA filings, PubMed, news | Reads Product & Regulatory fields |
| Investor Matching | Finds angels/VCs who fund your space | Reads Company basics + Stage + Financials |
| Regulatory Planning | FDA pathway with milestones + costs | Reads Product & Regulatory + Company stage |
| Team & Hiring | Grant-funded fellowships for hires | Reads Financials + Team size |
| Lab Access | Incubator/cleanroom matching | Reads Location + Product stage |

**Architecture rule:** New skills share the founder profile. No re-onboarding. No new signup. The agent already knows you.

### Skill Switching UX (Future)

When multiple skills are active:
```
User:   "Check competitors for my neurostim device"
Agent:  "I found 2 competitors: [details]. Also, I noticed your NIH grant
         deadline is in 10 days — want a reminder?"

User:   "Switch to investor matching"
Agent:  "Based on your profile, here are 3 angels who fund neuro devices at seed."
```

---

## Session Memory Schema

```json
{
  "user_id": "anon_session_or_uuid",
  "auth_status": "anonymous | authenticated | recognized_return",
  "profile": {
    "company_name": "",
    "industry": [],
    "stage": "",
    "location": { "city": "", "state": "", "incorporated": "" },
    "funding_raised": "",
    "team_size": 0,
    "years_in_business": 0,
    "revenue": ""
  },
  "grants": {
    "discovered": [],
    "saved": [{"grant_id": "", "source_url": "", "saved_at": ""}],
    "tracking": [
      {"grant_id": "", "source_url": "", "status": "interested|started|applied|submitted|under_review",
       "deadline": "", "attempt_number": 1}
    ],
    "awarded": [{"grant_id": "", "amount": "", "awarded_at": ""}],
    "rejected": [{"grant_id": "", "reason": "", "feedback": ""}],
    "dismissed": [{"grant_id": "", "reason": "", "dismissed_at": ""}],
    "abandoned": [{"grant_id": "", "last_active": ""}],
    "archived": []
  },
  "conversations": [
    { "timestamp": "", "summary": "", "decisions_made": [] }
  ],
  "preferences": {
    "proactive_frequency": "weekly",
    "notification_channel": "email|telegram|in-app",
    "min_grant_size": 300000,
    "auth_ever_prompted": false,
    "auth_decline_count": 0
  }
}
```

---

## Principles Reminder (Cut into the Implementation)

1. **Auth before value = dead.** Let them use Trestle for 5 minutes, fall in love with a match, then ask for the account.
2. **Ask questions like a curious friend, not a form.**
3. **Never present a grant without saying why the user qualifies.** And always include a clickable source URL.
4. **Never present a grant without a deadline.** Deadlines are the urgency engine.
5. **If uncertain, say so.** "I don't know" builds trust. Hallucination destroys it.
6. **The agent gets smarter over time.** First session = broad strokes. Third session = surgical recommendations.
7. **Founders are busy. Respect their time.** Every message should save them time, not waste it.
8. **The match is the hook. The lifecycle is the product.** Track everything. Learn from every rejection. Celebrate every award.
9. **Trestle is a personal assistant, not a grant tool.** Grants is v1. The architecture supports skills. Design for tomorrow.
