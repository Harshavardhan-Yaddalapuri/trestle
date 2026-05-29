# Trestle v1 Backend — Security Audit Report

**Date:** 2026-05-25  
**Scope:** `/Users/harshavardhan/trestle/backend/` — all auth endpoints, middleware, configuration, and deployment files  
**Branch:** `conversational-v1`  
**Auditor:** Hermes Agent (automated)

---

## Executive Summary

**Overall Risk Level: HIGH**

The Trestle v1 backend has a clean, well-structured codebase with solid test coverage and intentional auth design. However, four critical findings demand immediate remediation before any production or public-facing deployment:

1. **Service role key used for all database operations** — bypasses all Row Level Security
2. **Zero rate limiting** — signup, login, magic-link, and anonymous session endpoints are unprotected against abuse
3. **Container runs as root** — Dockerfile lacks a non-root user
4. **`--reload` flag in Docker CMD** — dangerous in any non-development context

These issues are architectural, not bugs. They reflect a v1/development posture. The auth middleware itself is sound — token validation handles edge cases correctly, public/private endpoint gating is correctly applied, and cookie configuration follows best practices for the most part.

---

## Checklist Summary

| # | Category | Status | Details |
|---|----------|--------|---------|
| 1 | Credential exposure | ❌ FAIL | Service role key used everywhere; see CV-1 |
| 2 | Auth — public endpoints accessible | ✅ PASS | Correctly gated |
| 3 | Auth — private endpoints reject | ✅ PASS | All protected endpoints use `Depends(get_current_user)` |
| 4 | Auth — token edge cases | ✅ PASS | Missing, expired, malformed, wrong scheme all → 401 |
| 5 | Auth — bypass attempts | ✅ PASS | No bypass discovered |
| 6 | Injection — SQL | ✅ PASS | All queries via Supabase client (parameterized) |
| 7 | Injection — XSS | ⚠️ WARN | `user_agent`/`fingerprint` stored unsanitized |
| 8 | CORS — wildcard origins | ✅ PASS | Explicit origins configured |
| 9 | CORS — credentials | ✅ PASS | `allow_credentials=True` with explicit origins |
| 10 | Security headers | ❌ FAIL | Missing X-Content-Type-Options, X-Frame-Options, HSTS, CSP |
| 11 | Rate limiting | ❌ FAIL | None configured anywhere |
| 12 | Cookie — httponly/secure/samesite | ✅ PASS | All three set correctly |
| 13 | Cookie — prefix/domain/path | ⚠️ WARN | No `__Secure-` prefix, no explicit path/domain |
| 14 | Session ID predictability | ✅ PASS | UUID v4 (122 bits entropy) |
| 15 | Dependencies — pinned versions | ❌ FAIL | All `>=` floating; no lockfile |
| 16 | Docker — non-root user | ❌ FAIL | Runs as root |
| 17 | Docker — unnecessary ports | ✅ PASS | Only 8000, 3000, 6379 exposed |
| 18 | Docker — --reload flag | ❌ FAIL | Present in production CMD |
| 19 | Redis — authentication | ❌ FAIL | No password configured |
| 20 | .env in .gitignore | ✅ PASS | `.env`, `.env.local`, `.env.production` all ignored |

---

## Vulnerability List (Ordered by Severity)

---

### CV-1: Service Role Key Used for All Database Operations

**Severity:** 🔴 CRITICAL  
**Category:** Credential Exposure / Authorization Bypass  
**Affected Files:** `backend/app/database.py:7-10`

**Description:**

The global Supabase client is initialized with `settings.supabase_service_key` — the Supabase **service_role** key, which has unrestricted, admin-level access to the entire database, bypassing all Row Level Security (RLS) policies.

```python
# database.py line 7-10
supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_service_key,  # ⚠️ SERVICE ROLE KEY
)
```

This client is used for **every database operation** in the application:
- User lookups (`get_user_with_profile`, `me`, login)
- Profile creation/updates
- Anonymous session creation and queries
- Conversation merging
- Health check queries

The service role key should **only** be used for the signup admin API call (`auth.py:119`). Every other database operation should use either:
- The anon key (for public endpoints with RLS policies)
- An authenticated user JWT (for user-scoped operations)

**Remediation:**
1. Create a second Supabase client with the `supabase_anon_key` for general queries
2. Keep the service role client only for admin operations (signup, and the JWKS call)
3. Or, use the authenticated user's JWT for user-scoped queries by passing it to `create_client` per-request

**Exploitation Scenario:** If an attacker gains access to the application's database connection (e.g., via a SSRF or dependency compromise), they have full admin access to all tables, including the ability to read/modify/delete all user data.

---

### CV-2: No Rate Limiting on Any Endpoint

**Severity:** 🔴 CRITICAL  
**Category:** Denial of Service / Abuse  
**Affected Files:** `backend/app/main.py` (entire app lacks rate limiting), `backend/app/routers/auth.py` (all auth endpoints)

**Description:**

There is zero rate limiting configured anywhere in the application. No `slowapi` middleware, no custom rate limiter, no Redis-backed rate limiting. Every endpoint is wide open:

| Endpoint | Abuse Vector |
|----------|-------------|
| `POST /api/auth/signup` | Create unlimited accounts; exhaust DB storage |
| `POST /api/auth/login` | Brute-force password attempts |
| `POST /api/auth/magic-link/send` | Exhaust Supabase email quota; spam arbitrary emails |
| `POST /api/auth/anonymous-session` | Fill database with junk sessions |
| `GET /api/auth/anon-session` | DB load via repeated lookups |
| `GET /api/auth/magic-link/verify` | Token hash brute-force |
| `GET /health/deep` | Amplification attack (JWKS + DB call per request) |

**Remediation:**
1. Add `slowapi` (or equivalent) middleware with Redis backend
2. Rate-limit per IP: signup (5/hour), login (10/minute), magic-link (3/hour per email), anonymous-session (20/minute)
3. `GET /health/deep` should be protected or at minimum rate-limited

---

### CV-3: Container Runs as Root

**Severity:** 🔴 CRITICAL  
**Category:** Container Security  
**Affected Files:** `backend/Dockerfile:1-13`

**Description:**

The Dockerfile has no `USER` directive. The container runs all processes as `root`. If the application is compromised (RCE via dependency vulnerability, etc.), the attacker has root access inside the container.

Additionally, `docker-compose.yml` bind-mounts `./backend:/app`, meaning code modifications inside the container could write to the host filesystem.

**Remediation:**
```dockerfile
# Add after COPY . .
RUN addgroup --system app && adduser --system --ingroup app app
USER app
```

---

### CV-4: `--reload` Flag in Docker CMD

**Severity:** 🔴 CRITICAL  
**Category:** Production Misconfiguration  
**Affected Files:** `backend/Dockerfile:13`

**Description:**

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

The `--reload` flag enables hot-reloading, which spawns a file-watcher subprocess. In production, this:
- Consumes extra resources
- Increases attack surface (file-watching subsystem)
- May cause instability under load
- Is explicitly warned against in Uvicorn docs for production

**Remediation:**
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
Use environment-based gating: `--reload` only when `ENV=development`.

---

### HV-1: No Security Headers

**Severity:** 🟠 HIGH  
**Category:** HTTP Security  
**Affected Files:** `backend/app/main.py` (no middleware adds security headers)

**Description:**

FastAPI does not add security headers by default. The application sends no:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy`

This leaves the API vulnerable to MIME sniffing attacks and clickjacking (if API responses are ever rendered in a browser).

**Remediation:**
Add a middleware that injects these headers, or use `secure` (a small FastAPI middleware package), or add them manually:
```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

---

### HV-2: Missing `iss` (Issuer) Validation in JWT Verification

**Severity:** 🟠 HIGH  
**Category:** Authentication Bypass Risk  
**Affected Files:** `backend/app/middleware/auth.py:86-93`

**Description:**

The JWT verification in `verify_supabase_jwt` checks `audience="authenticated"` but does **not** validate the `iss` (issuer) claim:

```python
payload = jwt.decode(
    token,
    key_data,
    algorithms=["RS256"],
    audience="authenticated",
    options={"verify_exp": True},
    # ⚠️ No 'issuer' parameter
)
```

While Supabase JWKS endpoints are project-specific (reducing practical risk), if an attacker could:
1. Compromise or spoof the JWKS endpoint
2. Or if another Supabase project's key somehow signs a token accepted by this app's JWKS

…the token would be accepted since the issuer is not checked.

**Remediation:**
```python
payload = jwt.decode(
    token,
    key_data,
    algorithms=["RS256"],
    audience="authenticated",
    issuer=settings.supabase_url.rstrip("/") + "/auth/v1",  # or similar
    options={"verify_exp": True},
)
```

---

### HV-3: No Email Verification on Signup

**Severity:** 🟠 HIGH  
**Category:** Account Integrity  
**Affected Files:** `backend/app/routers/auth.py:110-175`

**Description:**

The signup endpoint sets `email_confirm=True` which tells Supabase to auto-confirm emails:

```python
json={
    "email": body.email,
    "password": body.password,
    "email_confirm": True,  # ⚠️ Auto-confirms without verification
    ...
}
```

Anyone can sign up with any email address without proving ownership. This enables:
- Impersonation (create account with someone else's email)
- Spam account creation
- No barrier to abuse

**Remediation:**
Set `email_confirm=False` (or remove the field to use Supabase's default). This sends a verification email. Only after verification should the account be active.

---

### HV-4: `allow_headers=["*"]` in CORS Configuration

**Severity:** 🟠 HIGH  
**Category:** CORS Overly Permissive  
**Affected Files:** `backend/app/main.py:46`

**Description:**

```python
allow_headers=["*"],
```

While `allow_origins` is properly restricted, `allow_headers=["*"]` allows any custom header to be sent in cross-origin requests. Combined with `allow_credentials=True`, this broadens the attack surface unnecessarily.

**Remediation:**
```python
allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
```

---

### MV-1: No Redis Authentication

**Severity:** 🟡 MEDIUM  
**Category:** Infrastructure Security  
**Affected Files:** `backend/app/config.py:19`, `docker-compose.yml:40-46`

**Description:**

Redis is configured without a password:
```python
redis_url: str = "redis://redis:6379/0"  # No auth
```

And the Redis port is exposed to the host:
```yaml
ports:
  - "6379:6379"
```

Anyone who can reach port 6379 on the host can read/write to Redis. Even within the Docker network, there's no authentication barrier.

**Remediation:**
1. Add `requirepass` to Redis config
2. Update `redis_url` to include credentials: `redis://:password@redis:6379/0`
3. Remove the port mapping in production (internal Docker network only)

---

### MV-2: Error Details Forwarded from Supabase to Client

**Severity:** 🟡 MEDIUM  
**Category:** Information Disclosure  
**Affected Files:** `backend/app/routers/auth.py:131-138, 199-206, 258-264, 292-298`

**Description:**

Error responses from Supabase are forwarded directly to the client:

```python
detail = error_body.get("msg") or error_body.get("message") or detail
raise HTTPException(status_code=resp.status_code, detail=detail)
```

Supabase error messages may contain internal details about the database schema, constraint names, or service configuration. This leaks implementation details to potential attackers.

**Remediation:**
Log the full Supabase error server-side, but return a sanitized, generic message to the client:
```python
logger.error("Supabase error: %s", resp.text)
raise HTTPException(status_code=resp.status_code, detail="Authentication service error")
```

---

### MV-3: All Dependency Versions Floating (`>=`)

**Severity:** 🟡 MEDIUM  
**Category:** Supply Chain  
**Affected Files:** `backend/requirements.txt`

**Description:**

Every dependency uses `>=` version constraints with no upper bound and no lockfile:

```
fastapi>=0.109.0
supabase>=2.0.0
python-jose[cryptography]>=3.3.0
...
```

This means:
- Builds are non-deterministic
- A new release with a vulnerability or breaking change could be pulled in
- No way to reproduce the exact environment

Additionally, `python-jose` is less actively maintained than `PyJWT`. Consider migrating.

**Remediation:**
1. Pin all versions: `fastapi==0.115.6`
2. Add a `requirements.lock` or use `poetry`/`pip-tools` for lockfile generation
3. Consider replacing `python-jose` with `PyJWT` which is actively maintained

---

### MV-4: No CSRF Protection for State-Changing Endpoints

**Severity:** 🟡 MEDIUM  
**Category:** CSRF  
**Affected Files:** `backend/app/routers/auth.py` (all POST endpoints)

**Description:**

State-changing endpoints (`signup`, `login`, `logout`, `merge-session`, `anonymous-session`) have no CSRF protection. While the API is primarily consumed by a SPA with token-based auth (which partially mitigates CSRF), `allow_credentials=True` in CORS plus the cookie-based anonymous session makes CSRF a concern.

The anonymous session cookie (`trestle_anon_session`) uses `samesite="lax"` which provides partial protection, but:
- `SameSite=Lax` allows cookies on top-level navigation GET requests
- State-changing POST endpoints could still be targeted in some scenarios

**Remediation:**
1. Add CSRF token middleware for cookie-authenticated state changes
2. Or use `SameSite=Strict` (evaluate impact on UX)
3. Or implement double-submit cookie pattern

---

### MV-5: Bind Mount of Entire Backend in Docker Compose

**Severity:** 🟡 MEDIUM  
**Category:** Container Security  
**Affected Files:** `docker-compose.yml:17-18`

**Description:**

```yaml
volumes:
  - ./backend:/app
```

This mounts the entire backend source directory into the container. In production, this means:
- Source code changes on the host are reflected in the container (unpredictable behavior)
- Container compromise → host filesystem write access
- Inconsistent with immutable infrastructure principles

**Remediation:**
Remove the bind mount for production. Use the Dockerfile `COPY . .` instruction and build the image.

---

### MV-6: `get_optional_user` Silently Swallows All Errors

**Severity:** 🟡 MEDIUM  
**Category:** Auth Design  
**Affected Files:** `backend/app/middleware/auth.py:144-161`

**Description:**

```python
async def get_optional_user(...):
    if credentials is None:
        return None
    try:
        supabase_uid, email = await verify_supabase_jwt(credentials.credentials)
    except ValueError:
        return None  # ⚠️ Swallows ALL ValueError types
```

This catches ALL `ValueError` exceptions identically — whether the token is expired, malformed, or genuinely missing. For `get_optional_user`, this is somewhat intentional (it's meant to be best-effort), but:
- Expired tokens are silently ignored rather than informing the caller
- Debugging is harder because the specific failure reason is lost
- If `get_optional_user` is used in a context where the distinction matters, this is a bug

**Remediation:**
At minimum, log the specific error. Consider passing through token expiry information:
```python
except ValueError as exc:
    logger.debug("Optional auth failed: %s", exc)
    return None
```

---

### LV-1: JWKS URL Logged

**Severity:** 🔵 LOW  
**Category:** Information Disclosure  
**Affected Files:** `backend/app/middleware/auth.py:53`

**Description:**

```python
logger.info("Fetched JWKS from %s", SUPABASE_JWKS_URL)
```

This logs the full JWKS URL, which includes the Supabase project URL. While the URL alone is not a secret, it reveals the Supabase project identifier in logs.

**Remediation:**
Omit the URL or log only a sanitized version at INFO level. Move the full URL to DEBUG level.

---

### LV-2: Missing `__Secure-` Cookie Prefix

**Severity:** 🔵 LOW  
**Category:** Cookie Security  
**Affected Files:** `backend/app/routers/auth.py:384-391`

**Description:**

The anonymous session cookie is named `trestle_anon_session`. Best practice for cookies with `Secure` and `SameSite` flags is to use the `__Secure-` prefix, which browsers enforce to only allow the cookie with `Secure` set.

```python
ANON_COOKIE_KEY = "trestle_anon_session"  # Should be __Secure-trestle_anon_session
```

**Remediation:**
```python
ANON_COOKIE_KEY = "__Secure-trestle_anon_session"
```

---

### LV-3: No Explicit Cookie `path` or `domain`

**Severity:** 🔵 LOW  
**Category:** Cookie Security  
**Affected Files:** `backend/app/routers/auth.py:384-391`

**Description:**

The `set_cookie` call sets no `path` or `domain` parameter. FastAPI/Starlette defaults to the request path. This means if the cookie is set from `/api/auth/anonymous-session`, it might only be sent to that path. Similarly, no domain restriction means the cookie is sent to all subdomains.

**Remediation:**
```python
response.set_cookie(
    key=ANON_COOKIE_KEY,
    value=str(session_id),
    max_age=ANON_COOKIE_MAX_AGE,
    httponly=True,
    secure=True,
    samesite="lax",
    path="/",     # Available to all paths
    domain=None,  # Explicit default
)
```

---

### LV-4: `python-jose` Instead of `PyJWT`

**Severity:** 🔵 LOW  
**Category:** Dependency Freshness  
**Affected Files:** `backend/requirements.txt:6`

**Description:**

`python-jose` has been largely superseded by `PyJWT`, which is more actively maintained and has faster security patches. The `jose` library wraps `PyJWT` under the hood but adds an extra layer of dependency risk.

**Remediation:**
Replace `python-jose` with `PyJWT`. The API is similar:
```python
# Instead of: from jose import jwt
# Use: import jwt
```

---

### LV-5: `deep/health` Endpoint Hits External Services Unauthenticated

**Severity:** 🔵 LOW  
**Category:** Resource Consumption  
**Affected Files:** `backend/app/main.py:80-107`

**Description:**

The `/health/deep` endpoint makes two external calls (JWKS fetch and DB query) without any auth requirement. This is an amplification vector — each request triggers multiple upstream calls. The docstring says "Requires authentication in production (v2)" but v1 currently has it open.

**Remediation:**
Either rate-limit this endpoint heavily or add authentication (even a simple shared key).

---

## Recommendations for Production Hardening

### Immediate (before any public deployment):

1. **Split the Supabase client:** Anon key for user queries, service role for admin ops only
2. **Add rate limiting** — at minimum on signup, login, and magic-link endpoints
3. **Remove `--reload`** from Dockerfile CMD; gate with env var
4. **Add non-root user** to Dockerfile
5. **Add security headers** middleware

### Short-term (within first production sprint):

6. Add `iss` validation to JWT verification
7. Enable email verification on signup (`email_confirm=False`)
8. Restrict `allow_headers` in CORS to known headers
9. Add Redis password and remove port exposure
10. Pin all dependency versions; add lockfile
11. Sanitize error messages from Supabase before returning to client

### Medium-term:

12. Add CSRF protection for cookie-based sessions
13. Replace `python-jose` with `PyJWT`
14. Add `__Secure-` cookie prefix
15. Move `/health/deep` behind auth
16. Add HSTS header (after confirming HTTPS everywhere)
17. Implement JWT deny-list for logout (currently stateless)
18. Add automated dependency vulnerability scanning (Dependabot/Snyk)

---

## Pass Items (What's Done Well)

- ✅ `.env` files are properly gitignored
- ✅ No hardcoded secrets in source code
- ✅ All DB queries use Supabase client (parameterized — no SQL injection)
- ✅ UUID inputs are validated before use in queries
- ✅ JWT verification uses RS256 with JWKS key lookup
- ✅ Token edge cases handled correctly (missing, expired, malformed, wrong scheme)
- ✅ Public/private endpoint gating is correct
- ✅ CORS origins are explicit (not wildcard)
- ✅ Cookie security flags are set (httponly, secure, samesite)
- ✅ Session IDs use UUID v4
- ✅ Pydantic models validate all input shapes and types
- ✅ Comprehensive test suite covers auth edge cases
- ✅ Soft-delete pattern (`deleted_at` checks) used throughout

---

## Test Coverage Notes

The test suite is comprehensive and covers:
- ✅ Public endpoint accessibility
- ✅ Private endpoint rejection (no token, expired, malformed, missing Bearer prefix)
- ✅ CORS headers on preflight and normal responses
- ✅ Cookie security (httponly, secure, samesite)
- ✅ Magic link verify edge cases (invalid hash, missing user, valid flow)
- ✅ Merge session paths (not found, already merged, expired, successful)
- ✅ Auth bypass attempts

Tests do **not** cover:
- ❌ Rate limiting (no implementation to test)
- ❌ Security headers (not implemented)
- ❌ Issuer validation (not implemented)
- ❌ Service role key vs anon key distinction
