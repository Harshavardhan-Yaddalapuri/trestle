# Trestle — Post-Match Grant Lifecycle

**Date:** 2026-05-23
**Owner:** Sam (Product)
**Status:** Draft
**Design Principle:** The match is not the end. It's the beginning of a 6-18 month relationship. Trestle must track every transition from "saw the grant" through "celebrated the award" — and handle every dead end along the way.

---

## 1. Why This Exists

Harsha said it directly: _You covered saving and dismissing grants. You never designed what happens AFTER._ Without post-match lifecycle, Trestle is a search engine. With it, Trestle is a grant co-pilot that:

1. Knows which grants the founder is actually pursuing
2. Sends deadline reminders before they slip
3. Nudges when the founder should have heard back
4. Adapts strategy when a grant is rejected (plan B, plan C)
5. Celebrates wins and asks "what's next?"
6. Feeds rejection/acceptance data back into the matching algorithm

---

## 2. Grant Lifecycle State Machine

### States Overview

```
[DISCOVERED] → [SAVED] → [INTERESTED] → [STARTED] → [APPLIED] → [SUBMITTED] → [UNDER_REVIEW]
                                                                                      ↓
                                                    ┌─────────────────────── [ACCEPTED] → [AWARDED]
                                                    │
                                                    └─────────────────────── [REJECTED] → [RECONSIDERING]
                                                                                            ↓
                                                                                      [DISMISSED]
                                                                                            ↓
                                                                                      [ARCHIVED]
```

### States Defined

| # | State | Description | Who enters it |
|---|-------|-------------|---------------|
| 1 | DISCOVERED | User saw the grant in a match result. No explicit action taken. | Agent (auto) |
| 2 | SAVED | User bookmarked the grant for later. No commitment to apply. | User |
| 3 | INTERESTED | User said "tell me more" or "I'm interested in this." Agent starts tracking. | User |
| 4 | STARTED | User has begun preparation (reading guidelines, assembling team). | User or Agent (inferred) |
| 5 | APPLIED | User submitted the application. | User |
| 6 | SUBMITTED | Agent confirmed submission (checking for confirmation email or user confirmation). | Agent |
| 7 | UNDER_REVIEW | Grant agency is reviewing the application. Waiting period (2-9 months typical). | Agent (time-based, or user says "waiting") |
| 8 | ACCEPTED | User was notified of provisional acceptance. | User |
| 9 | AWARDED | Funds received. Grant is active. | Agent (user confirms funds received) |
| 10 | REJECTED | User received rejection notification. | User |
| 11 | RECONSIDERING | User was rejected but is considering reapplication, rebuttal, or alternative. | User |
| 12 | DISMISSED | User explicitly declined or abandoned (no action for >90 days). | User or Agent (auto) |
| 13 | ABANDONED | User showed interest, then went silent for >90 days without explicit dismissal. | Agent (auto) |
| 14 | ARCHIVED | Grant lifecycle is fully closed. No further agent action needed. | Agent (auto or user-requested) |

---

## 3. State Transitions (Every Path)

### Core Happy Path: Match → Apply → Award

```
DISCOVERED → SAVED → INTERESTED → STARTED → APPLIED → SUBMITTED → UNDER_REVIEW → ACCEPTED → AWARDED → ARCHIVED
```

#### Transition: DISCOVERED → SAVED

| Field | Value |
|-------|-------|
| Trigger | User clicks "Save" or says "save this one" |
| Agent action | Add to `grants_saved` list. Update profile. |
| Agent message | _Saved to your list. Want me to check back when the application window opens?_ |
| Data stored | `grant_id`, `saved_at`, `source_url`, `deadline` |
| Sad path — save duplicate | Agent: _This is already in your saved list. Want to open it?_ |

#### Transition: SAVED → INTERESTED

| Field | Value |
|-------|-------|
| Trigger | User says "I'm interested in this," "tell me more," or clicks "Deep Dive" |
| Agent action | Move to `grants_tracking` list. Set status = `interested`. Start deadline monitoring. |
| Agent message | _Great choice. I'll track this one — due [date]. Need help with the structure?_ |
| Agent starts | 30-day check-in timer. Deadline reminder timer. |
| Data stored | `interested_at`, `deadline_reminder_set: true` |

#### Transition: INTERESTED → STARTED

| Field | Value |
|-------|-------|
| Trigger | User says "I'm starting the application," "working on it now," or agent infers from activity (e.g., user asks about budget template) |
| Agent action | Update status to `started`. Offer application support resources. |
| Agent message (if user announces) | _Let me know if you need help with the budget template or finding a grant writer._ |
| Agent message (if inferred) | _I noticed you were looking at the guidelines — are you starting the application? I can help._ |
| Data stored | `started_at` |

#### Transition: STARTED → APPLIED

| Field | Value |
|-------|-------|
| Trigger | User says "I submitted it," "just applied," or "sent it in" |
| Agent action | Move to `applied`. Wait for confirmation. |
| Agent message | _Congrats on getting it in! Did you get a confirmation email from the agency?_ |
| | _[If yes] → Move to SUBMITTED_ |
| | _[If no/not sure] → Agent: Want me to note it as submitted and follow up in a few days?_ |
| Sad path — user says "almost there" | Status stays `started`. Agent: _No rush. How close are you? Need anything?_ |
| Sad path — deadline passed, not submitted | → DISMISSED (auto-ABANDONED if no contact in 7 days post-deadline) |

#### Transition: APPLIED → SUBMITTED

| Field | Value |
|-------|-------|
| Trigger | User confirms receipt of agency confirmation email, or agent has access to verify |
| Agent action | Update status to `submitted`. Start review-waiting timer. |
| Agent message | _Confirmed. Now the waiting game begins. Average review time for this grant is [X months]. I'll check in at the [X/2] mark._ |
| Data stored | `submitted_at`, `expected_review_duration` |
| Sad path — confirmation never confirmed | After 14 days, agent: _I never confirmed your submission — did it go through?_ If no response for 30 days → ABANDONED. |

#### Transition: SUBMITTED → UNDER_REVIEW

| Field | Value |
|-------|-------|
| Trigger | Time-based (automated, ~30 days after SUBMITTED for most grants) |
| Agent action | Update status to `under_review`. Set notification at expected decision date. |
| Agent message | _Your grant is under review. Decision expected by [date]. I'll nudge you when it's close._ |
| Proactive check-in | At 50% of expected review duration: _Just checking in — any updates on your grant? Need anything else in the meantime?_ |
| Data stored | `under_review_at`, `expected_decision_date` |
| Sad path — review takes longer than expected | User says "still waiting." Agent: _That's normal for [Grant Name]. Some take up to [X months]. I'll check again in 30 days._ |

#### Transition: UNDER_REVIEW → ACCEPTED

| Field | Value |
|-------|-------|
| Trigger | User says "I got accepted," "we won it," or "received the award letter" |
| Agent action | Update status to `accepted`. Celebrate. Ask for award amount and terms. |
| Agent message | _That's huge. Congratulations._ [Actual congratulations, not corporate boilerplate] _What's the amount? Want me to help plan the next phase?_ |
| Data stored | `accepted_at`, `award_amount`, `award_terms` |
| Sad path — user is cagey about amount | Agent: _No problem. The important thing is you got it. What's next?_ |

#### Transition: ACCEPTED → AWARDED

| Field | Value |
|-------|-------|
| Trigger | User confirms funds received, or 30 days post-acceptance (default timeout) |
| Agent action | Update to `awarded`. Re-evaluate financial runway with new capital. |
| Agent message | _Funds in? Let me recalculate your runway with this $[X]. Your burn was $[Y]/mo — that's [Z] months of extra runway._ |
| Data stored | `awarded_at`, `runway_extended_months` |
| Sad path — never received funds | User says "still waiting on disbursement." Agent: _Some grants take 60-90 days to disburse. Want me to remind you to check in 30 days?_ |

#### Transition: ACCEPTED/AWARDED → ARCHIVED

| Field | Value |
|-------|-------|
| Trigger | User says "done with this grant," or 90 days post-award with no activity |
| Agent action | Move to `archived`. Grant lifecycle complete. |
| Agent message | _Archived. If anything changes, I can unarchive it._ |
| Sad path — grant requires reporting | If award has reporting requirements, agent sets reminder: _This grant has a Q1 report due [date]. Want me to remind you?_ |

---

### Rejection Path: Match → Apply → Reject → Reconsider/Dismiss

```
DISCOVERED → SAVED → INTERESTED → STARTED → APPLIED → SUBMITTED → UNDER_REVIEW → REJECTED
                                                                                      ↓
                                                                              [RECONSIDERING] → [STARTED] (reapply)
                                                                                      ↓
                                                                              [DISMISSED] → [ARCHIVED]
```

#### Transition: UNDER_REVIEW → REJECTED

| Field | Value |
|-------|-------|
| Trigger | User says "we got rejected," "didn't get it," or "declined" |
| Agent action | Update to `rejected`. Offer alternatives. |
| Agent message | _Sorry to hear that. Can I ask — did they give a reason? Sometimes grants give feedback about competitiveness, budget, or scope fit._ |
| Agent follow-up (if feedback received) | _Good data. I'll adjust your profile so future matches avoid similar mismatches. Here are [2-3 alternative grants] that might be a better fit._ |
| Agent follow-up (if no feedback) | _Some grants don't give feedback. Here are [2-3 similar grants] to try. Same category, different review panel._ |
| Data stored | `rejected_at`, `rejection_reason`, `feedback_notes` |
| Sad path — user is devastated | "I'm not sure about this whole grant thing." Agent: _Rejection is the norm in grants. Most successful founders get 5-10 rejections per acceptance. Let me know when you're ready to look at the next one — no pressure._ |
| Sad path — user blames the product | "Your matches are useless." Agent: _Tell me what went wrong — was the eligibility wrong? The fit? I'll learn from it._ If pattern persists across 3+ grants, flag for product team. |

#### Transition: REJECTED → RECONSIDERING

| Field | Value |
|-------|-------|
| Trigger | User says "I'll reapply," "next cycle," "let me try again," or "maybe with revisions" |
| Agent action | Update to `reconsidering`. Set next deadline reminder. Offer revision support. |
| Agent message | _Good call — many grants encourage resubmission. The next cycle opens [date]. Want me to help you track what needs to change?_ |
| Data stored | `reconsidering_at`, `reapplication_deadline` |
| Sad path — reapplication not allowed | User wants to reapply but grant has a 12-month cool-off. Agent: _This one has a 12-month wait. Here are [2-3 alternatives] in the meantime._ |

#### Transition: RECONSIDERING → STARTED (reapplication loop)

| Field | Value |
|-------|-------|
| Trigger | User begins preparing reapplication |
| Agent action | Loop back to STARTED state. Full lifecycle restarts with reapplication context. |
| Agent note | Same grant_id, incremented `attempt_number` in metadata. |
| Data stored | `attempt_number: 2`, `previous_rejection_reason` |

#### Transition: RECONSIDERING → DISMISSED

| Field | Value |
|-------|-------|
| Trigger | User says "I'm done with this one," "skip it," or 90 days in reconsidering with no action |
| Agent action | Move to dismissed. |
| Agent message (if user-initiated) | _Noted. I'll stop tracking this one._ |
| Agent message (if auto-dismissed) | _I noticed [Grant Name] has been on your reconsider list for 3 months. Want me to keep it, or should I archive it?_ |
| Data stored | `dismissed_at`, `dismissal_reason` |

---

### Abandonment Path: Interest → Silence → Lost

```
DISCOVERED → SAVED → INTERESTED → [90 days no activity] → ABANDONED → [Re-engagement attempt] → [Re-entry]
                                                                                                    ↓
                                                                                              [DISMISSED]
```

#### Transition: INTERESTED/STARTED → ABANDONED

| Field | Value |
|-------|-------|
| Trigger | No user activity for 90 days since last state change, and no response to 2 check-ins |
| Agent action | Move to `abandoned`. Stop deadline reminders. |
| Agent check-in #1 (at 30 days) | _Just checking in — still working on [Grant Name]? Deadline's coming up._ |
| Agent check-in #2 (at 60 days) | _Hey — haven't heard from you about [Grant Name]. Want me to keep tracking it, or should I archive it?_ |
| Agent message (at 90 days, auto-abandon) | _I've paused tracking on [Grant Name]. If you want to pick it back up, just say the word — your notes are saved._ |
| Data stored | `abandoned_at`, `last_active_at` |
| Sad path — user returns after abandonment | → Re-entry (see below). |

#### Re-entry After Abandonment

| Field | Value |
|-------|-------|
| Trigger | User returns after being in ABANDONED state |
| Agent action | Restore to previous state. Agent picks up context. |
| Agent message | _Welcome back! You were working on [Grant Name]. The deadline has passed, but the next cycle opens [date]. Want to try again?_ |
| If deadline hasn't passed | Restore to saved/interested. Agent: _You're back in time — [Grant Name] is still open. Want to pick up where you left off?_ |

---

### Dismissal Path: Fast Rejection

```
[DISCOVERED] → [DISMISSED]
[INTERESTED] → [DISMISSED]
[ANY STATE] → [DISMISSED]
```

| Field | Value |
|-------|-------|
| Trigger | User says "skip," "not for me," "not interested," or click "Dismiss" |
| Agent action | Move to `dismissed`. Store reason. Learn from it. |
| Agent message | _Got it. Why not? (This helps me avoid similar ones.)_ |
| User says "not enough money" | Agent stores: `dismissal_reason: min_amount_too_low`. Update profile: raise minimum grant size filter. |
| User says "wrong category" | Agent stores: `dismissal_reason: category_mismatch`. Update profile: adjust therapeutic area/industry tags. |
| User says "deadline too soon" | Agent stores: `dismissal_reason: deadline_too_soon`. Agent: _Noted. I'll avoid imminent deadlines unless you ask._ |
| User doesn't give reason | Agent stores: `dismissal_reason: unspecified`. No profile changes. |
| Data stored | `dismissed_at`, `dismissal_reason` |

---

### Archive (Terminal State)

| Field | Value |
|-------|-------|
| Trigger | Grant lifecycle complete: awarded + 90 days, or dismissed + 90 days, or abandonded + 90 days |
| Agent action | Move to `archived`. No further agent activity on this grant. |
| Data retention | Archived grants remain searchable. User can unarchive. |
| Long-term archive | After 2 years in archive, anonymized and retained for matching algorithm training only. |

---

## 4. Proactive Agent Nudges (Time-Based)

These are automated, not triggered by user action:

| Nudge | Timing | Agent Message Template |
|-------|--------|----------------------|
| Deadline approaching | 30 days before deadline | _[Grant Name] is due in 30 days. Your profile looks eligible. Want help getting started?_ |
| Deadline imminent | 7 days before deadline | _[Grant Name] is due in 7 days. If you're applying, now's the time._ |
| Deadline passed (not submitted) | 1 day after deadline | _[Grant Name] deadline passed. The next cycle opens [date]. Want me to set a reminder?_ |
| Review halfway mark | 50% of expected review period | _Your [Grant Name] application has been under review for [X months]. Any word yet?_ |
| Decision expected | Expected decision date | _Your [Grant Name] decision should be in soon. Let me know how it goes._ |
| Decision overdue | Expected decision date + 30 days | _[Grant Name] decision is overdue. Might be worth checking with the agency._ |
| Reconsideration window opens | Next cycle date + 1 day | _[Grant Name] is open for applications again. Want to try again with what you learned?_ |
| No activity on tracked grant | 30 days since last state change | _I haven't seen any movement on [Grant Name]. Still planning to apply?_ |
| Grant status change (database update) | When new data is available | _Good news — [Grant Name] increased their award cap. Your profile now qualifies for $[X]._ |

---

## 5. Edge Cases & Sad Paths (Exhaustive)

### 5.1 Multiple Grants in Flight Simultaneously

| Scenario | Agent Behavior |
|----------|----------------|
| User has 5 grants in INTERESTED/STARTED | Agent tracks them all independently. Nudges are per-grant, not batched. But: if user shows overwhelm (delayed responses, avoidance), agent merges into a single status: _You've got 5 grants in progress. Want to prioritize one?_ |
| User applies to 2 grants with same deadline | Agent: _I noticed you're working on [Grant A] and [Grant B], both due [date]. That's ambitious. Here's a timeline if you want to do both._ |
| Same grant, multiple application cycles | Tracked as attempt_number iterations. Each cycle is a fresh lifecycle, linked to previous by parent grant ID. Agent knows the history. |

### 5.2 User Ghosting (No Activity)

| Scenario | Agent Behavior |
|----------|----------------|
| User hasn't returned in 30 days | One check-in: _Still looking for grants?_ |
| User hasn't returned in 60 days | Two check-ins sent (day 30, day 45). No response → ABANDONED. |
| User returns after 6+ months | Full re-onboarding: _It's been a while. A lot has changed in grants. Want me to re-build your profile from scratch, or pick up where you left off?_ |
| User returns after account deletion | No history. Fresh start. Agent doesn't reference past. |

### 5.3 Data Contradictions

| Scenario | Agent Behavior |
|----------|----------------|
| User says "I submitted" but deadline is in 3 months | Agent: _Just confirming — the deadline for this grant is [date in 3 months]. Did you submit for a different cycle?_ |
| User says "got rejected" but status shows not submitted | Agent: _I didn't have a submission recorded for this one. Did you submit it elsewhere?_ |
| User says "I got $500K" but grant max is $250K | Agent: _Interesting — the official listing says $250K max. Did you get a supplemental or a different award tier?_ |

### 5.4 Grant Database Data Quality Issues

| Scenario | Agent Behavior |
|----------|----------------|
| Source URL is dead (404) | Agent: _The official page for this grant seems to be down. The grant info was last verified [date]. Want me to search for an updated link?_ Fallback: search for grant by name. |
| Grant is expired/closed but still in DB | Agent: _It looks like this grant cycle has closed. I'll update the database. Here are [2-3 current alternatives]._ |
| Grant eligibility changed since last match | Agent: _[Grant Name] updated their eligibility criteria. Your profile still matches, but let me double-check._ |

### 5.5 Spiral Detection

| Scenario | Agent Behavior |
|----------|----------------|
| User rejected from 3+ grants in <30 days | Agent pauses proactive suggestions. Check-in: _You've had a rough streak. The grants I'm surfacing might not be the right fit. Want me to review your profile and adjust the filter criteria?_ |
| User accepted 3+ grants | Agent: _You're on a roll. How are you managing multiple awards? Some have reporting requirements. Want me to track those?_ |
| User applied to 10+ grants simultaneously | Agent: _You've got a lot of applications in play. That's great. But some grants require effort overlap checks — want me to verify you're not double-dipping?_ |

### 5.6 User Changed Their Situation

| Scenario | Agent Behavior |
|----------|----------------|
| User raises new funding | Agent detects via conversation (_"we just raised $2M"_). Re-runs grant matching. Some grants now ineligible (funding cap exceeded). Agent flags: _Congrats on the raise. It changes your grant landscape — here's what opened and what closed._ |
| User moves to new state/country | Agent detects via conversation (_"we relocated to Boston"_). Re-runs location-based matching. Agent: _Boston opens up MassChallenge, Massachusetts Life Sciences Center grants, and Biogen consortium — want me to check those?_ |
| User pivots product/therapeutic area | Agent: _I see you're pivoting. Your current grant matches are based on your old profile. Want a fresh match?_ |
| User changes company stage | Agent re-evaluates eligibility for all tracked grants. Some grants have stage-specific requirements. Agent flags changes proactively. |

### 5.7 Grant Lifecycle Exceptions

| Scenario | Agent Behavior |
|----------|----------------|
| Grant is cancelled mid-cycle by agency | Agent: _[Grant Name] was cancelled by the agency. Sorry — I'll remove it from your list. Here are similar alternatives._ |
| Grant deadline extended | Agent: _[Grant Name] extended their deadline to [new date]. Good news for your timeline._ |
| Grant changes name or rebrands | Agent treats as same grant (same grant_id in DB). Updates display name. Agent: _[Old Name] is now called [New Name]. Same program, new name._ |

---

## 6. Metrics & Success Criteria

| Metric | What It Measures | Target |
|--------|------------------|--------|
| Saved → Applied conversion rate | % of saved grants where user reaches APPLIED state | ≥ 20% in first 3 months → ≥ 35% after algorithm learns |
| Submitted → Awarded conversion rate | % of submissions that result in an award | ≥ 15% (SBIR average is ~14%) |
| Dismissed → Reconsideration rate | % of dismissed grants where user re-engages | ≥ 10% |
| Abandonment rate (INTERESTED → ABANDONED) | How often users lose interest before applying | Target: < 30% (meaning >70% of interested grants get an application) |
| Time from INTERESTED to APPLIED | How fast users move through the pipeline | Average: < 60 days |
| Nudge response rate | % of proactive nudges that get a user response | ≥ 40% |
| Post-application satisfaction | User says "this helped me get a grant" or similar | 1 win = signal. 5 wins = validated |

---

## 7. What This Unlocks

With post-match lifecycle:
- Trestle can report: "You have 3 grants in progress, 1 under review, 1 awarded"
- Trestle can learn: Which grants actually convert for which founder types? Which fields predict rejection?
- Trestle can adapt: If a founder consistently gets rejected from NIH but accepted by DoD, the matching algorithm shifts weight
- Trestle can plan: "Based on your application history, your next best move is [Grant X], due in 45 days"

*The match is the hook. The lifecycle is the product. Track everything. Learn from every rejection. Celebrate every award.*
