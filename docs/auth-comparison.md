# Authentication Solutions Comparison for Trestle

**Context:** Trestle is local-first (Docker Compose) with Next.js 15 frontend + FastAPI backend. Need auth that works locally without cloud dependencies if possible, but cloud options with generous free tiers are acceptable. May deploy later.

**Date researched:** May 2026

---

## Quick Recommendation

| Use case | Recommendation |
|----------|---------------|
| **Local-only, zero cloud dependencies** | NextAuth.js v5 + Credentials provider or Authentik (self-hosted Docker) |
| **Fastest time-to-ship, generous free tier** | Clerk (50K MRU free) or Supabase Auth (50K MAU free) |
| **Enterprise-grade self-hosted, unlimited users** | Keycloak or Ory Kratos (Apache 2.0) |
| **Google ecosystem / mobile-first** | Firebase Auth (50K MAU free) |
| **If you already pay for Supabase** | Supabase Auth (no extra cost, tightly integrated) |

---

## 1. Supabase Auth

### Pricing Breakdown
| Plan | MAUs | Key Limits | Cost |
|------|------|-----------|------|
| Free | 50,000 | 2 projects, 500MB DB, 5GB egress, community support | $0/mo |
| Pro | 100,000 included | $0.00325/MAU beyond, 8GB DB, 250GB egress | $25/mo |
| Team | 100,000 included | Same per-MAU, more DB | $599/mo |
| Enterprise | Custom | Custom | Contact |

**Third-Party Auth MAUs:** Using Clerk/Auth0/Auth0 with Supabase counts as "Third-Party MAUs" — also 50K free, then $0.00325/MAU on Pro+.

### Self-Hosting
- **Yes, fully Docker-based.** Official `docker-compose.yml` with all services (Kong API gateway, GoTrue auth, PostgREST, Realtime, Storage, Studio).
- Setup time: ~30 minutes.
- Self-hosted = unlimited MAUs, no per-user costs beyond your own infrastructure.
- The auth service (GoTrue) is open source under MIT license.
- JWT signing is configurable — supports HS256 (symmetric) and ES256 (asymmetric) keys.
- Gotcha: Free cloud projects are **paused after 1 week of inactivity**.

### Complexity to Integrate (Next.js + FastAPI)
- **Frontend:** `@supabase/supabase-js` and `@supabase/ssr` for Next.js. Well-documented, 15-30 min setup.
- **Backend (FastAPI):** Validate JWTs via Supabase's JWKS endpoint (`https://<project>.supabase.co/auth/v1/.well-known/jwks.json`). Use `python-jose` or `PyJWT`.
- **Docker Compose local:** Self-host Supabase entirely in Docker alongside Trestle. No cloud dependency needed.

### JWT/Session Support
- Access tokens (JWTs, default 1 hour expiry) + refresh tokens.
- Sessions stored in `auth.sessions` table.
- Supports session timeouts, single-session enforcement, inactivity timeouts (Pro+).
- MFA, anonymous sign-ins, social OAuth, passwordless, phone auth all available.

### Gotchas for Local-Only Deployment
- Self-hosting requires managing ~6 containers (Kong, GoTrue, PostgREST, Realtime, Storage, Studio) — resource-heavy for a simple local dev setup.
- Cloud free tier pauses after 1 week of inactivity — unacceptable for intermittent local dev.
- Self-hosted Supabase is the entire platform (DB + Auth + Storage + Realtime). If you only want auth, this is overkill.
- JWT validation in FastAPI requires either calling the JWKS endpoint (network dependency) or embedding the JWT secret — both are fine locally.

---

## 2. Clerk

### Pricing Breakdown
| Plan | Price (monthly) | Price (annual) | MRUs Included | Key Limits |
|------|-----------------|----------------|--------------|------------|
| Hobby (Free) | $0 | $0 | 50,000 per app | 7-day fixed session, 1-day log retention, no orgs, no branding removal |
| Pro | $25/mo | $20/mo | 50,000 included | $0.02/MRU (50K-100K), $0.018 (100K-1M), $0.015 (1M-10M), $0.012 (10M+) |
| Business | $300/mo | $250/mo | 50,000 included | + SOC 2 report, priority support |
| Enterprise | Custom | Custom | Custom | Everything + SLAs |

**Add-ons:** Enhanced B2B Auth $100/mo ($85 annual), Enhanced Admin $100/mo ($85 annual).

### Self-Hosting
- **No. Clerk is a managed SaaS only.** No self-hosted option.
- This means local-only deployment always requires internet access to Clerk's servers.
- Development instances work locally but still phone home to Clerk.

### Complexity to Integrate (Next.js + FastAPI)
- **Frontend:** `@clerk/nextjs` — purpose-built for Next.js 15. Setup in minutes. Prebuilt UI components, middleware (`clerkMiddleware()`), `auth()` helper in Server Components.
- **Backend (FastAPI):** Validate Clerk session tokens. Clerk issues JWTs — verify using Clerk's JWKS endpoint. Or use Clerk's backend SDK (available in Node, Go, etc.; Python requires manual JWT verification).
- Overall: Easiest integration of all cloud options for Next.js.

### JWT/Session Support
- Stateless JWT verification with automatic refresh.
- "First Day Free" policy — users not counted as retained until 24+ hours after signup.
- Sessions managed by Clerk; access tokens with configurable lifetime.
- MFA, passkeys, social login, passwordless, email magic links all included.

### Gotchas for Local-Only Deployment
- **Cannot work fully offline.** Requires internet to reach Clerk's API for auth flows.
- Free tier has 7-day fixed session lifetime (can't customize).
- No organizations on free tier.
- If Clerk has an outage, your local auth stops working. No local fallback.
- Vendor lock-in: user data lives in Clerk; migration requires export.

---

## 3. Auth0

### Pricing Breakdown
| Plan | B2C Price | B2B Price | MAUs Included |
|------|----------|----------|--------------|
| Free | $0/mo | $0/mo | 25,000 |
| Essentials | $35/mo | $150/mo | 500 (then tiered) |
| Professional | $240/mo | $800/mo | 500 (then tiered) |
| Enterprise | Custom | Custom | Custom |

- **B2C MAU tiers:** After Essentials/Professional base (500 MAU), pricing jumps at tiers (1K, 2.5K, 5K, 7.5K, 10K, 25K, 50K, 100K, etc.).
- Yearly billing = 11x monthly (1 month free).
- Free tier now includes 25K MAU (up from 7.5K in 2024), custom domains (credit card required), 1 enterprise SSO connection, passwordless, 5 organizations.

### Self-Hosting
- **No. Auth0 is a managed SaaS only.**
- Free tier requires credit card for custom domains.
- Entity limits: 10 applications, 100 connections, 3 rules, 3 admin users on free tier.

### Complexity to Integrate (Next.js + FastAPI)
- **Frontend:** Auth0 Next.js SDK (`@auth0/nextjs-auth0`). Well-documented but more configuration-heavy than Clerk. ~30 min setup.
- **Backend (FastAPI):** Validate JWTs using Auth0's JWKS endpoint. Well-supported via `python-jose` or Auth0's Python quickstart.
- Auth0's mature platform means extensive docs, but the DX is API-first (vs Clerk's component-first).

### JWT/Session Support
- Full JWT-based auth with access/refresh tokens.
- MFA, passwordless, social connections, SSO, SAML, OIDC.
- Advanced security (breach detection, brute force protection, adaptive MFA) — but mostly on paid tiers.

### Gotchas for Local-Only Deployment
- **Cannot work offline.** Requires Auth0's cloud.
- "Growth penalty" pricing — crossing tier thresholds can cause 15x cost jumps.
- Historical security incidents (two breaches in 12 months reported in 2024).
- Free tier reduced from 25K to 7.5K, then restored to 25K — pricing history shows volatility.
- MAUs count per tenant — dev/staging/prod all count separately.
- For Trestle's local-first model, Auth0 is a poor fit due to cloud dependency.

---

## 4. NextAuth.js (Auth.js v5)

### Pricing Breakdown
- **Completely free and open source (ISC license).**
- No per-user fees, no MAU limits, no cloud dependency.
- You pay only for your own infrastructure (hosting, database).

### Self-Hosting
- **Fully self-hosted by design.** Runs inside your Next.js application.
- Works in Docker (set `AUTH_TRUST_HOST=true`).
- Database adapters for PostgreSQL, MySQL, SQLite, Prisma, Drizzle, etc.
- All you need: `AUTH_SECRET` env var + providers configured.
- Can use OAuth providers (Google, GitHub) which require those providers' cloud services — but the auth logic runs locally.

### Complexity to Integrate (Next.js + FastAPI)
- **Frontend (Next.js):** Native integration. Single `auth.ts` file at project root. `auth()` helper in Server Components, middleware, route handlers. Session provider for client components.
- **Backend (FastAPI):** The challenge. NextAuth.js manages sessions via cookies/JWT on the Next.js side. FastAPI needs to:
  - **Option A:** Validate NextAuth.js JWTs directly in FastAPI (share `AUTH_SECRET`, decode JWT). Works for JWT strategy.
  - **Option B:** FastAPI calls Next.js endpoint to validate session (adds latency).
  - **Option C:** FastAPI acts as the authorization server (OAuth2/OIDC) — complex.
- **Credentials Provider:** For email/password auth without any cloud provider — fully local. You handle password hashing (bcrypt/argon2) and user storage yourself.
- Setup time: 30-60 min for basic setup, more for FastAPI integration.

### JWT/Session Support
- Two strategies: **JWT** (default for credentials, stateless) and **database** (sessions stored in DB).
- JWT encrypted with `AUTH_SECRET`. Can store custom claims via callbacks.
- Session management via HTTP-only cookies.
- Edge-compatible with JWT strategy.

### Gotchas for Local-Only Deployment
- **Best option for local-first.** Zero cloud dependencies with Credentials provider.
- Credentials provider is intentionally limited — no built-in password reset, email verification, rate limiting. You build these yourself.
- FastAPI integration is non-trivial. Need to share JWT secret between Next.js and FastAPI, or use API key / service-to-service auth pattern.
- OAuth providers (Google, GitHub) still require internet + provider registration.
- No admin UI, no user management dashboard — all must be custom built.
- You are responsible for security (password hashing, brute force protection, CSRF, etc.).

---

## 5. Firebase Auth

### Pricing Breakdown
| Plan | MAU Limit | Cost |
|------|----------|------|
| Spark (Free) | 50,000 MAU (Tier 1) | $0 |
| Blaze (Pay-as-you-go) | Unlimited | Tier 1: $0 (0-50K), $0.0055 (50K-100K), $0.0046 (100K-1M), $0.0032 (1M-10M), $0.0025 (10M+) |
| Tier 2 (SAML/OIDC) | 50 MAU free | $0.015/MAU after 50 |
| Phone Auth (SMS) | — | $0.01-$0.34/SMS |

- Free tier also limited to 3,000 DAU.
- Identity Platform upgrade needed for SAML/OIDC, multi-tenancy, blocking functions.

### Self-Hosting
- **No. Firebase Auth is a Google Cloud managed service.**
- Firebase Auth Emulator exists for local development but is NOT for production.
- Emulator can run locally without internet for testing.

### Complexity to Integrate (Next.js + FastAPI)
- **Frontend:** Firebase JS SDK. Simple client-side integration. Google sign-in, email/password, anonymous, phone all built-in.
- **Backend (FastAPI):** Verify Firebase ID tokens using Firebase Admin SDK (Python via `firebase-admin`). Simple: `auth.verify_id_token(token)`.
- Tightly coupled to Google ecosystem; adding to non-Firebase stack adds complexity.

### JWT/Session Support
- Firebase ID tokens (JWTs) with 1-hour expiry. Refresh tokens handled by Firebase SDK.
- Custom claims supported (1000-byte limit).
- Anonymous auth, account linking, social providers.

### Gotchas for Local-Only Deployment
- **Cannot work offline in production.** Firebase Auth Emulator is dev-only.
- Free tier has hard limits (3K DAU, 50K MAU) — exceeding them shuts off auth for the rest of the month.
- Custom OIDC/SAML providers require Blaze plan + Identity Platform.
- Google ecosystem lock-in.
- Phone auth requires Blaze plan (no free SMS).
- For Trestle: Emulator could work for local dev, but production requires cloud.

---

## 6. Keycloak (Self-Hosted)

### Pricing Breakdown
- **Completely free and open source (Apache 2.0).**
- No per-user fees, no MAU limits. Pay only for your infrastructure.
- Red Hat Build of Keycloak (enterprise support) available at additional cost.
- Managed Keycloak services (Inteca, Skycloak) exist but are separate from the OSS project.

### Self-Hosting
- **Yes, designed for self-hosting.** Docker Compose with PostgreSQL is the standard deployment.
- 2 containers: Keycloak (Quarkus/Java) + PostgreSQL.
- RAM: ~1-2 GB (JVM overhead). Startup: 30-60 seconds.
- Supports Kubernetes, behind reverse proxy (Nginx/Caddy), HA setups.
- Production mode requires HTTPS setup.

### Complexity to Integrate (Next.js + FastAPI)
- **Frontend (Next.js):** Use `next-auth` with Keycloak provider, or use `keycloak-js` adapter. Or use generic OIDC client (`openid-client`). Moderate complexity.
- **Backend (FastAPI):** Excellent. FastAPI + Keycloak is a well-documented pattern. Use `PyJWT` to validate tokens against Keycloak's JWKS endpoint. FastAPI dependency injection maps naturally to Keycloak's token structure.
- Admin console for user management, realm configuration, role assignment.
- Overall: Setup is moderate (Docker Compose + realm config), but integration is straightforward once running.

### JWT/Session Support
- Full OAuth 2.0 / OIDC / SAML 2.0 support.
- JWT access tokens (RS256 by default) + refresh tokens.
- JWKS endpoint for local token validation (no round-trip to Keycloak per request).
- Session management, SSO, identity brokering, user federation (LDAP/AD), social login.
- Fine-grained authorization (RBAC, ABAC, UMA).

### Gotchas for Local-Only Deployment
- Resource-heavy: 1-2 GB RAM + PostgreSQL. Adds significant overhead to Docker Compose.
- Java startup time: 30-60 seconds before ready. Slows down `docker compose up`.
- Configuration complexity: Realms, clients, roles, scopes — steep learning curve.
- No visual flow designer (Authentik has one).
- Overkill for a single-application local-first setup.
- Best for: when you need enterprise-grade IAM or plan to scale to multiple services.

---

## 7. Ory Kratos (Self-Hosted)

### Pricing Breakdown
| Option | Cost | Limits |
|--------|------|--------|
| **Open Source (self-hosted)** | $0 | Unlimited users, Apache 2.0 license |
| Ory Network Production (managed) | $770/year | Up to ~10K DAU |
| Ory Network Growth (managed) | $9,350/year | Up to ~20K DAU |
| Ory Network Enterprise | Custom | Custom |
| Ory Enterprise License (self-hosted + support) | Custom | Self-hosted with SLAs |

### Self-Hosting
- **Yes, designed for it.** Go binary, single static executable. No heavy runtime dependencies.
- Database: PostgreSQL, MySQL, SQLite, or CockroachDB.
- Docker Compose quickstart available (2-3 containers: Kratos + DB + mail server).
- Stateless, horizontally scalable. Cloud-native (Kubernetes-ready).
- RAM: Significantly lighter than Keycloak (~200-500 MB).

### Complexity to Integrate (Next.js + FastAPI)
- **Frontend:** Ory Kratos is API-only — no UI. You must build your own login/registration/settings pages. Ory provides SDKs and React components, but you do more custom work than with Clerk/Supabase.
- **Backend (FastAPI):** Kratos provides session validation APIs. FastAPI can validate Kratos session cookies or JWTs via Kratos' `/sessions/whoami` endpoint. Or validate Ory Hydra OAuth2 tokens if using Hydra.
- Significant self-service UI to build (login, registration, settings, verification, recovery).
- Overall: Most engineering work of all options, but most flexible.

### JWT/Session Support
- Cookie-based sessions with anti-CSRF tokens.
- OIDC/OAuth2 via Ory Hydra (separate component).
- Passwords, passkeys, passwordless, social sign-in, MFA (TOTP), SMS verification.
- Account recovery, verification flows.
- No admin UI in open source — managed via API/CLI.

### Gotchas for Local-Only Deployment
- **API-only — no UI.** Must build all user-facing auth pages yourself (or use Ory Network which provides pre-built pages).
- Open source lacks: admin UI, analytics, multi-tenancy, B2B SSO, organizations (those are Ory Network only).
- Self-hosted requires you to handle email delivery (SMTP server), SMS gateway, infrastructure.
- Excellent for local-first if you accept the UI build cost; very lightweight in Docker Compose.
- Documentation is good but oriented toward cloud-native/Kubernetes.

---

## 8. Authentik (Self-Hosted)

### Pricing Breakdown
| Plan | Cost | Features |
|------|------|----------|
| Open Source | $0 | Full identity provider, MIT license, unlimited users |
| Enterprise | $5/user/month | Google Workspace, Entra ID, mTLS, compliance reports |
| Enterprise Plus | Starting $20K/year | Custom SLAs, FIPS compliance, dedicated support |

### Self-Hosting
- **Yes, designed for self-hosting.** Docker Compose with 3-4 containers: server, worker, PostgreSQL, Redis.
- RAM: ~800 MB idle, 1-1.5 GB active.
- Modern web UI (React SPA) with admin dashboard and visual flow designer.
- Outposts for LDAP, RADIUS, proxy.
- Supports OIDC, SAML 2.0, LDAP, SCIM, social login, MFA (TOTP, WebAuthn, SMS).

### Complexity to Integrate (Next.js + FastAPI)
- **Frontend:** OIDC standard — use any OIDC client library. `next-auth` with generic OIDC provider works. Or Authentik's own SDKs.
- **Backend (FastAPI):** Standard OIDC Relying Party pattern. Validate JWTs against Authentik's JWKS endpoint. Well-supported.
- Admin UI makes configuration easier than Keycloak.
- Visual flow designer for auth workflows.
- Overall: Easier setup than Keycloak, slightly heavier resource usage due to Python/Django + Redis.

### JWT/Session Support
- Standard OIDC/OAuth2 JWT tokens.
- Sessions managed via Authentik.
- MFA, passkeys, social login, LDAP federation, SAML, SCIM.
- Application proxy for legacy apps without SSO support.

### Gotchas for Local-Only Deployment
- Resource usage: 3-4 containers, ~1 GB RAM. Heavier than Ory Kratos but lighter than Keycloak.
- Redis is required (Ory Kratos doesn't need Redis).
- SAML support is newer/less mature than Keycloak's.
- Docker socket mount needed for outpost management (security consideration).
- Excellent balance of features + usability for self-hosted; good fit for Docker Compose local setup.

---

## Summary Comparison Matrix

| Solution | Free Tier (Cloud) | Self-Host | Offline Local-Only | Next.js DX | FastAPI DX | Setup Time | Resource Usage | Best For |
|----------|-------------------|-----------|-------------------|------------|------------|------------|----------------|----------|
| **Supabase Auth** | 50K MAU | Yes (Docker) | Yes (self-hosted) | Excellent | Good | 15-30 min | Heavy (6+ containers) | Full Supabase stack users |
| **Clerk** | 50K MRU | No | No (cloud only) | Excellent | Moderate | 5-15 min | Zero (SaaS) | Fastest ship, Next.js apps |
| **Auth0** | 25K MAU | No | No (cloud only) | Good | Good | 30-60 min | Zero (SaaS) | Enterprise, compliance-heavy |
| **NextAuth.js v5** | Free (OSS) | Yes (in-app) | **Yes** | Excellent | Challenging | 30-60 min | Minimal | **Local-first, zero deps** |
| **Firebase Auth** | 50K MAU | No (emulator dev-only) | No (cloud only) | Good | Good | 30-45 min | Zero (SaaS) | Google ecosystem, mobile |
| **Keycloak** | Free (OSS) | **Yes** | **Yes** | Moderate | Excellent | 1-2 hours | Heavy (1-2 GB) | Enterprise IAM, multiple services |
| **Ory Kratos** | 25K MAU (Network) | **Yes** | **Yes** | Moderate | Moderate | 2-4 hours | Medium (200-500 MB) | Cloud-native, API-first |
| **Authentik** | Free (OSS) | **Yes** | **Yes** | Moderate | Good | 1-2 hours | Medium (800 MB-1 GB) | Self-hoster friendly, visual UI |

---

## Recommendations for Trestle

### Tier 1: Best for Local-First (Zero Cloud Dependency)
**NextAuth.js v5 + Credentials Provider**

- Add `next-auth@5` to `frontend/`, configure with Credentials provider.
- Store users in your existing PostgreSQL (already in Docker Compose).
- FastAPI validates JWTs by sharing `AUTH_SECRET` — decode in FastAPI with `PyJWT`.
- Zero external dependencies. Works completely offline.
- Build email verification, password reset, rate limiting yourself.
- If you later deploy to cloud, swap Credentials for OAuth providers (Google, GitHub).

### Tier 2: Good Balance (Some Cloud, Generous Free Tier)
**Clerk (Hobby Plan)**

- 50,000 MRU free. Excellent Next.js 15 integration.
- FastAPI validates Clerk JWTs via JWKS endpoint.
- Requires internet, but free tier is extremely generous.
- If you're okay with cloud dependency during local dev, this is the fastest path.
- Pro plan at $25/mo adds MFA, custom session lifetimes, branding removal.

### Tier 3: Self-Hosted IAM (If You Want Full Control)
**Authentik** (over Keycloak for this project)

- Docker Compose: add 3-4 containers (server, worker, Redis, + existing PostgreSQL).
- Full admin UI. Visual flow designer. OIDC standard.
- Next.js uses generic OIDC client. FastAPI validates OIDC tokens.
- Free, unlimited users, no cloud dependency.
- Lighter than Keycloak, better UI than Ory Kratos.

### Not Recommended for Trestle
- **Auth0:** Cloud-only, "growth penalty" pricing, historical security concerns.
- **Firebase Auth:** Cloud-only (emulator not for production), ecosystem lock-in.
- **Ory Kratos:** Excellent but API-only — too much custom UI to build for a solo project.
- **Supabase Auth (cloud free tier):** Projects pause after 1 week of inactivity.
- **Supabase Auth (self-hosted):** Brings entire Supabase platform when you only need auth.

---

## FastAPI JWT Validation Pattern (Shared)

For solutions using OIDC/OAuth2 (Keycloak, Authentik, Clerk, Supabase), the FastAPI pattern is consistent:

```python
# auth.py - FastAPI dependency
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient
from functools import lru_cache

security = HTTPBearer()

@lru_cache()
def get_jwks_client(jwks_url: str):
    return PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    token = credentials.credentials
    jwks_client = get_jwks_client("http://auth:8080/realms/trestle/protocol/openid-connect/certs")
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    try:
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="trestle-api",
            options={"verify_exp": True},
        )
        return payload
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
```

For NextAuth.js with Credentials (JWT strategy, HS256):

```python
# FastAPI validates NextAuth.js JWTs by sharing AUTH_SECRET
import jwt

AUTH_SECRET = os.environ["AUTH_SECRET"]  # Same as Next.js side

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, AUTH_SECRET, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

Frontend sends: `Authorization: Bearer <nextauth-session-jwt>`

