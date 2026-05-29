# Trestle — Authentication & Session Flow Design

**Date:** 2026-05-23  
**Owner:** Sam (Product)  
**Status:** Draft — pending team feasibility review  
**Related:** User flow doc, API contract (Clerk JWT + anon_session_id cookie)

---

## 1. Philosophy

Trestle is conversational first. We do **not** block the chat with a signup wall.
The user should get value (first grant match) before we ask for an email.
Auth exists to make the agent *better* — not to gatekeep.

---

## 2. State Machine (Happy Path)

```
[Anonymous Visitor]
       |
       v
[First Message Sent] ----(backend sets signed anon_session_id cookie)---->
       |
       v
[Conversation Active] ----(profile building in localStorage + server memory)---->
       |
       v
[Value Moment: First Grant Match Displayed] ----(agent asks to save/account)---->
       |
       +---> [User declines signup] ----(continue anonymous, warn about data loss)----> [End]
       |
       +---> [User accepts signup] ----(show signup method choice)---->
                   |
                   v
          [Account Created] ----(session merge: anon -> auth)---->
                   |
                   v
          [Authenticated User] ----(full persistence, proactive alerts)---->
                   |
                   v
          [Return Visit] ----("Welcome back, {name}. {n} new grants since {date}.")---->
```

---

## 3. Anonymous First Session

### What Persists (Anonymous)

| Layer | Data | TTL / Scope |
|-------|------|-------------|
| Server | `anon_session_id` (signed cookie, UUIDv4) | 30 days, HttpOnly, Secure, SameSite=Lax |
| Server | Conversation transcript (linked to `anon_session_id`) | 30 days |
| Server | Extracted profile fragments (industry, stage, location, etc.) | 30 days |
| Client | `trestle_profile` (localStorage, same fields) | Until browser cache cleared |
| Client | Dismissed grants list (localStorage) | Until browser cache cleared |
| Client | Tracked grants list (localStorage) | Until browser cache cleared |

### What Does NOT Persist (Anonymous)

- No email → no proactive alerts, no "deadline approaching" notifications
- No cross-device sync (localStorage is device-bound)
- No password recovery (there is no account)
- Profile can be lost if user clears cookies AND localStorage

### Agent Behavior During Anonymous Session

- Agent introduces itself normally. No mention of accounts until value delivered.
- After first match is shown, agent says:
  > "Want me to remember this and alert you when deadlines approach? Create a free account — takes 10 seconds."
- If user continues without signup, agent continues. No nagging. Ask again at 3rd session or 7 days.

---

## 4. Signup Trigger — When We Ask

### Primary Trigger: Post-First-Match

**When:** After agent displays first grant match AND user interacts with it (clicks "Tell me more", "Track this", or types a follow-up question).

**Why:** User has received value. They are emotionally invested. Asking before this is a wall.

**Agent Script:**
> "I can track this for you and ping you when the deadline gets close. Just need an email — no password required if you use Google."

### Secondary Triggers

| Trigger | Condition | Agent Script |
|---------|-----------|--------------|
| "Save this" intent | User says "save this grant" or clicks bookmark icon | "I'll save it here for now, but if you leave and come back, I won't remember. Want to create an account so I don't forget?" |
| Session #3 | Anonymous user returns for 3rd distinct session | "You're back — nice. I've helped you find {n} grants so far. Create an account and I can keep track across devices." |
| Proactive alert mention | User asks "can you remind me?" | "I can, but I need an email to send reminders to. Sign up — it's free." |

### Anti-Patterns (We Do NOT Do These)

- [ ] Popup modal on landing
- [ ] "Sign up to chat" before first message
- [ ] Nagging every message after first match
- [ ] Requiring signup to see grant details

---

## 5. Signup Methods

### Supported Methods (v1)

| Method | Effort | Trade-off | Recovery Path |
|--------|--------|-----------|---------------|
| **Google OAuth** | 1-click | Fastest, no password fatigue | Google account recovery |
| **Magic Link (email)** | 2 clicks (enter email → click link) | No password to forget | Resend link |
| **Email + Password** | Email + password + confirm | Full control, works for non-Google users | Password reset email |

### Recommended Default

**Magic link is the default.** No password to forget. One less field. One less decision.

Google OAuth is presented as the prominent alternative. Email+password is available as "More options".

### Signup Flow (Magic Link — Default)

```
[User clicks "Create account" in chat]
       |
       v
[Inline email input in chat widget] ----(type email, submit)---->
       |
       v
[Backend sends magic link email via Resend/SES]
[Agent says: "Check your email — I sent you a link. Click it and you're in."]
       |
       v
[User clicks link /user-auth/verify?token=xyz]
       |
       v
[Backend validates token, creates user row, issues Clerk JWT]
[Redirects back to chat with ?auth=success]
       |
       v
[Frontend detects ?auth=success, refreshes token, calls POST /api/v1/auth/merge-session]
       |
       v
[Agent: "You're all set. I moved everything from this conversation over to your account."]
```

### Signup Flow (Google OAuth)

```
[User clicks "Continue with Google" in chat widget]
       |
       v
[Clerk popup → Google OAuth consent]
       |
       v
[Callback to /user-auth/callback?clerk_token=...]
[Backend creates/updates user, issues JWT]
       |
       v
[POST /api/v1/auth/merge-session with anon_session_id cookie]
       |
       v
[Agent: "Welcome, {first_name}. I saved your conversation."]
```

### Signup Flow (Email + Password)

```
[User expands "More options" → Email + Password]
       |
       v
[Inline form: email, password, confirm password]
       |
       v
[Backend: validate email uniqueness, hash password (Argon2id), create user]
       |
       v
[Send verification email]
[Agent: "Account created. Check your email to verify — until then, you can keep chatting, but I can't send alerts."]
       |
       v
[User verifies email → POST /api/v1/auth/verify-email]
[Backend: mark email_verified = true, enable alerts]
```

---

## 6. Return User Experience

### Detection

- Cookie `trestle_auth_token` (Clerk JWT) present AND valid
- OR localStorage `trestle_user_id` present (checked against server on load)

### Welcome Back Script

**If new grants matching their profile were added since last visit:**
> "Welcome back, {first_name}. {n} new grants match your profile since {last_visit_date}. Want to see them?"

**If no new grants, but tracked grant deadline is approaching:**
> "Welcome back, {first_name}. Reminder: your {grant_name} application is due in {n} days. Need anything?"

**If no new grants, no approaching deadlines:**
> "Welcome back, {first_name}. Anything new with the company? I can re-run your matches if something changed."

### Session Restoration

```
[Return user opens chat widget / visits site]
       |
       v
[Frontend sends JWT in Authorization header]
[Backend looks up user_id, fetches latest profile + conversation history]
       |
       v
[Agent receives system prompt with full context:]
"User {name} is back. Last visit: {date}. Profile: {industry}, {stage}, {location}.
New grants since: {list}. Tracked grants: {list}. Previous conversation ended on: {topic}."
       |
       v
[Agent delivers welcome message + context-appropriate next step]
```

---

## 7. Session Merge: Anonymous → Authenticated

### Critical Rule

When a user signs up, **all anonymous session data must migrate** to their authenticated account. No data loss. The user did not "start over."

### Data to Merge

| Source (anon_session_id) | Target (user_id) | Conflict Resolution |
|--------------------------|------------------|---------------------|
| Conversation transcripts | Append to user's conversation history | Chronological merge |
| Extracted profile | Merge into user profile | Most recent wins per field; if auth profile has field, keep it; if empty, use anon |
| Dismissed grants | Merge into user's dismissed_grants | Deduplicate on grant_id |
| Tracked grants | Merge into user's tracked_grants | Deduplicate on grant_id; if conflict on status, most recent wins |
| localStorage `trestle_profile` | Sync to server profile; then clear localStorage | Server state is now source of truth |

### Merge API

```
POST /api/v1/auth/merge-session
Headers: Authorization: Bearer <new_clerk_jwt>
Body: { "anon_session_id": "anon_xxx" }
```

**Backend logic:**
1. Validate JWT → get user_id
2. Look up anon session by anon_session_id
3. If found and not older than 30 days:
   - Merge conversation history (append)
   - Merge profile (field-by-field, auth wins conflicts)
   - Merge dismissed/tracked grants (deduplicate)
   - Delete anon session row OR mark as merged (soft delete for audit)
4. Return: `{ "merged": true, "conversations_migrated": n, "grants_migrated": m }`
5. Invalidate anon_session_id cookie (set expired)

---

## 8. Logout / Switch Account / Recovery

### Logout

- Frontend: Clear Clerk JWT from memory/localStorage
- Frontend: Call POST /api/v1/auth/logout (optional, for server-side session invalidation)
- Frontend: Reset chat to Flow 1 (First Contact) state
- Backend: Optionally blacklist JWT in short-lived cache (Redis, TTL = JWT expiry)
- User returns to anonymous mode

### Switch Account

- Not supported in v1. Logout → sign in as different user.
- If user tries to login while already logged in: logout first, then login.

### Password Reset (Email + Password users only)

```
[User clicks "Forgot password?" on login form]
       |
       v
[POST /api/v1/auth/forgot-password { "email": "..." }]
[Backend: generate reset token, TTL 1 hour, email link]
       |
       v
[User clicks link: /reset-password?token=xyz]
[Enter new password + confirm]
       |
       v
[POST /api/v1/auth/reset-password { "token": "xyz", "new_password": "..." }]
[Backend: validate token, hash new password, invalidate all existing sessions]
```

### Token Expiry (Session Duration)

| Token Type | TTL | Refresh Behavior |
|------------|-----|------------------|
| Clerk JWT (auth) | 7 days | Auto-refreshed by Clerk SDK if user is active; silent refresh via Clerk's `useAuth` hook |
| Anon session cookie | 30 days | Extended on each API call; expires after 30 days idle |
| Magic link token | 15 minutes | Single-use; user must request new link if expired |
| Password reset token | 1 hour | Single-use |
| Email verification token | 24 hours | Single-use; resend available after 60s cooldown |

---

## 9. Sad Paths (Every State Transition)

### 9.1 Email Never Verified

**Scenario:** User signs up with email + password but never clicks the verification link.

**What they CAN do:**
- Continue chatting (we don't block conversation)
- View grant matches
- Track grants (stored in DB, but no email alerts sent)

**What they CANNOT do:**
- Receive email alerts about deadlines
- Receive proactive "new grant" emails
- Reset password (verification required first)

**Agent Script when unverified user asks for alerts:**
> "I can track it, but I can't email you reminders until you verify your email. Check your inbox for the verification link."

**Re-verification:**
- Button in settings: "Resend verification email"
- Rate limit: max 1 resend per 60 seconds, max 5 per day
- After 7 days unverified: agent says "Still haven't verified? I can resend the link."

### 9.2 Duplicate Email Signup

**Scenario:** User tries to sign up with an email that already exists.

**Behavior:**
> "Looks like you already have an account with that email. Want to log in instead?"

- Show login form with email pre-filled
- Offer "Forgot password?"

**Security note:** Do NOT say "email exists" vs "email doesn't exist" in forgot-password flow. Always say "If an account exists, we sent a reset link." to prevent email enumeration.

### 9.3 Google OAuth Down / Failure

**Scenario:** Google's OAuth endpoint is unreachable, or user denies consent.

**User denies consent:**
> "No worries. You can use your email directly instead — just type it below."
- Fallback to magic link form immediately

**Google OAuth endpoint down (timeout/error):**
- Frontend detects popup failure after 30s
- Show: "Google login isn't working right now. Try email instead — it'll work the same."
- Log to Sentry for monitoring

**Backend can't fetch Google profile info (partial success):**
- If we get auth token but not name/email: treat as failed login
- Show: "Something went wrong connecting to Google. Try again or use email."

### 9.4 Cookies Cleared Mid-Conversation

**Scenario:** User is chatting anonymously. They clear cookies (or browser does automatically). `anon_session_id` is lost.

**Detection:**
- Frontend: localStorage has `trestle_profile` but no valid `anon_session_id` cookie
- Server rejects anon session lookup → returns 404

**Behavior:**
- Frontend detects mismatch: localStorage profile exists, server says no session
- Agent says: "Looks like your session expired. I still have your info here (shows summary). Want me to restore it, or start fresh?"
- If user says "restore": Frontend sends localStorage profile as initial context; server creates new anon session, seeds with localStorage data
- If user says "start fresh": Clear localStorage, start Flow 1 from scratch

**Authenticated user cookies cleared:**
- JWT is gone → user appears anonymous
- But localStorage still has `trestle_user_id`
- Frontend: "You appear to be logged out. Sign in to restore your account?"
- Show login button inline in chat

### 9.5 Mobile → Desktop Switch (Cross-Device)

**Scenario:** User chats on phone anonymously. Later opens laptop.

**Anonymous cross-device:**
- localStorage does NOT sync across devices
- Server-side anon session exists (by cookie), but desktop has no cookie
- User must sign up (or login) to get cross-device sync
- After signup, all future sessions sync (server is source of truth)

**Agent script when desktop detects incomplete profile:**
> "Looks like you're new here on this device. If you've chatted with me before, sign in and I'll pull everything over."

**Authenticated cross-device:**
- JWT in localStorage on each device
- Profile and conversations load from server on login
- Real-time sync: if user dismisses a grant on mobile, it's dismissed on desktop next load

**Edge: Multiple simultaneous sessions**
- Not a concern for v1. Last-write-wins on profile updates.
- v2: Consider WebSocket or polling for real-time sync.

### 9.6 Magic Link Expired

**Scenario:** User clicks magic link after 15 minutes.

**Behavior:**
- Backend validates token → expired
- Redirect to `/login?expired=true`
- Show: "That link expired. Want me to send a new one?"
- User enters email again → new link sent (same rate limits)

### 9.7 Account Already Exists via OAuth

**Scenario:** User signs up with Google (sarah@gmail.com). Later tries magic link with same email.

**Behavior:**
- Backend detects email exists with OAuth provider
- Show: "You already have an account via Google. Sign in with Google to keep using the same account."
- Offer: "Or create a new account with a different email."

**Do NOT allow:** Creating a separate password-based account with same email as OAuth. Prevents account fragmentation.

### 9.8 Rate Limited During Signup

**Scenario:** Bot/human spams login/signup endpoints.

**Rate limits:**
| Endpoint | Limit | Window |
|----------|-------|--------|
| POST /auth/signup | 5 | per IP per hour |
| POST /auth/login | 10 | per IP per hour |
| POST /auth/forgot-password | 3 | per email per hour |
| POST /auth/magic-link | 3 | per email per hour |

**Behavior on rate limit:**
- Return 429 with `Retry-After: <seconds>` header
- Frontend: "Too many attempts. Try again in {n} minutes."

---

## 10. Session Persistence Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   Browser       │      │   Backend        │      │   Database      │
│                 │      │   (FastAPI)      │      │   (PostgreSQL)  │
├─────────────────┤      ├──────────────────┤      ├─────────────────┤
│ localStorage:   │      │ Clerk JWT        │      │ users           │
│ - trestle_user_ │◄────►│ validation       │◄────►│ - id, email,    │
│   id (optional) │      │                  │      │   auth_provider │
│ - trestle_      │      │ anon_session_id  │      │ - name, profile │
│   profile       │      │ cookie parsing   │      │ - email_verified│
│ - dismissed_    │      │                  │      │                 │
│   grants        │      │ /auth/merge-     │      │ anon_sessions   │
│ - tracked_      │      │ session          │      │ - id, data      │
│   grants        │      │                  │      │ - expires_at    │
│                 │      │                  │      │ - merged_to_    │
│ Cookies:        │      │                  │      │   user_id       │
│ - trestle_auth_ │◄────►│                  │      │                 │
│   token (JWT)   │      │                  │      │ conversations   │
│ - anon_session_ │◄────►│                  │      │ - user_id OR    │
│   id            │      │                  │      │   anon_session_ │
│                 │      │                  │      │   id            │
└─────────────────┘      └──────────────────┘      └─────────────────┘
```

---

## 11. Out of Scope — Not Building (v1)

| Item | Why cut | When revisited |
|------|---------|----------------|
| **Multi-factor authentication (MFA)** | Overkill for grant chat; magic link is already passwordless | v3 — if handling sensitive financial data |
| **Social login beyond Google (LinkedIn, GitHub, Apple)** | Google covers 90%+ of target user base | v2 — if users ask for it |
| **User roles / team accounts** | Single-founder use case for v1 | v2 — when accelerator cohorts need shared views |
| **SSO / SAML for enterprise** | No enterprise customers in first 6 months | v3 — if selling to accelerators |
| **Session revocation dashboard** | No admin panel in v1 | v2 — with operator dashboard |
| **"Login with Telegram"** | Bot is MVP channel, but auth via Telegram passport is complex | v3 — if retention on Telegram is high |

---

## 12. Team Feasibility Gates

Before this auth flow is approved for implementation:
- [ ] **Jason (Backend):** Clerk integration complexity — custom user store vs Clerk's default? How does `anon_session_id` cookie interact with Clerk's session management?
- [ ] **Jason (Backend):** Merge-session API — transaction safety for profile merge; what happens if merge fails halfway?
- [ ] **Floyd (Frontend):** Clerk SDK integration with Next.js — does `useAuth` handle silent refresh for our JWT TTL? How to inject auth state into chat widget?
- [ ] **Aurthur (Architect):** Should we use Clerk's user metadata for profile storage, or our own `users` table? Implications for sync.
- [ ] **Jim (DevOps):** Email service — Resend vs AWS SES? Rate limits, deliverability, cost per magic link.

---

## 13. Metrics to Track

| Metric | Baseline | Target | Why |
|--------|----------|--------|-----|
| Signup rate (anon → account) | N/A | ≥ 20% of users who see first match | Measures value-to-signup conversion |
| Magic link click-through rate | N/A | ≥ 70% | Measures email deliverability + UX clarity |
| Session merge success rate | N/A | ≥ 99% | Measures backend reliability |
| Cross-device return rate | N/A | ≥ 40% of auth users return on 2nd device | Measures account stickiness |
| Password reset completion rate | N/A | ≥ 60% | Measures UX friction in recovery |
| Average time to signup from first message | N/A | < 4 minutes | Measures wall placement |

---

*No signup wall before value. Every transition has a fallback. The user never loses data because they hesitated to create an account.*
