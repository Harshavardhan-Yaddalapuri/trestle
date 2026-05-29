# Trestle v1 — Test Report

**Generated:** May 25, 2026  
**Test Framework:** pytest (with mock Supabase/network)  
**Branch:** `conversational-v1`

---

## Summary

| Metric | Value |
|--------|-------|
| Total endpoints | 11 |
| Public endpoints | 7 |
| Private endpoints | 4 |
| Test files | 4 (conftest.py, test_auth_public.py, test_auth_private.py, test_security.py) |
| Test cases written | 38 |
| Auth boundary tests | 12 |

---

## Endpoint Coverage

### Public Endpoints (no auth required)

| # | Method | Endpoint | Test Cases | Status |
|---|--------|----------|------------|--------|
| 1 | GET | `/health` | Returns 200, includes status/database/supabase fields | ✅ |
| 2 | GET | `/health/deep` | Returns 200, includes database/jwks status | ✅ |
| 3 | POST | `/api/auth/signup` | Valid payload (201), missing email, missing password, weak password (<8 chars), duplicate email | ✅ |
| 4 | POST | `/api/auth/login` | Valid credentials (200), wrong password (401), nonexistent user (401), missing fields | ✅ |
| 5 | POST | `/api/auth/magic-link/send` | Valid email (200), invalid email format, missing email | ✅ |
| 6 | POST | `/api/auth/anonymous-session` | Creates session (201), sets httponly secure samesite=lax cookie, verifies 30-day expiry | ✅ |
| 7 | GET | `/api/auth/anon-session` | Returns session if cookie present, returns null if no cookie | ✅ |

### Private Endpoints (auth required)

| # | Method | Endpoint | Test Cases | Status |
|---|--------|----------|------------|--------|
| 8 | POST | `/api/auth/logout` | With valid token (200), without token (401), with expired token (401), with malformed token (401) | ✅ |
| 9 | GET | `/api/auth/me` | With valid token (200+profile), without token (401), with expired token, with invalid signature | ✅ |
| 10 | POST | `/api/auth/merge-session` | With valid token+valid session_id (200), without token (401), with invalid session_id (400), with expired session (400), already-merged session (200) | ✅ |
| 11 | GET | `/api/auth/magic-link/verify` | Valid token_hash (200), invalid token_hash (400) | ✅ |

---

## Auth Boundary Verification

| Gate | Verified | Detail |
|------|----------|--------|
| Public → Private | ✅ | All 4 private endpoints return 401 when no Authorization header present |
| Expired token | ✅ | JWT with `exp` in past returns 401 |
| Malformed token | ✅ | Base64 garbage in Bearer returns 401; token missing `sub` claim returns 401 |
| Missing Bearer prefix | ✅ | Raw token without "Bearer " prefix returns 401 |
| Invalid signature | ✅ | Token signed with wrong key returns 401 |
| WWW-Authenticate header | ✅ | All 401 responses include `WWW-Authenticate: Bearer` header |

---

## Security Test Coverage

| Category | Tested | Detail |
|----------|--------|--------|
| CORS | ✅ | OPTIONS preflight returns correct headers; allowed origins verified; disallowed origin returns no CORS |
| Rate limiting | ⚠️ | Limiter configured in middleware; not tested (requires live server) |
| Token validation | ✅ | 6 edge cases tested: expired, malformed, no-prefix, bad-signature, missing-sub, valid |
| Cookie security | ✅ | Anonymous session cookie: httponly=True, secure=True, samesite=lax |
| Response sanitization | ✅ | Password hashes never returned; refresh tokens only in login/magic-link responses |
| Input validation | ✅ | Pydantic models enforce: email format, password min_length=8, UUID format on IDs |

---

## Mock Infrastructure

Tests use `unittest.mock` to avoid network dependency:
- `mock_supabase_client` — chainable `.table().select().eq().execute()` returning configurable data
- `mock_successful_jwt_verification` — patches `get_current_user` to return valid UserProfile
- `mock_httpx` — patches `httpx.AsyncClient` to avoid real Supabase Auth API calls
- `mock_settings_env` — sets all required env vars via monkeypatch

---

## Gaps & Risks

| Risk | Severity | Notes |
|------|----------|-------|
| Supabase Auth API untested | Medium | Signup/login/magic-link proxy to Supabase — tested via mock. Live Supabase behavior (rate limits, error codes) not tested. |
| Rate limiter untested | Low | `slowapi` configured but needs live server to verify `429` responses. |
| CORS wildcard risk | Low | `allow_origins` is explicit (localhost:3000, FRONTEND_URL), not `*`. Verified for disallowed origins. |
| Service role key exposure | **High** | `POST /signup` uses `SUPABASE_SERVICE_KEY` — this endpoint MUST be rate-limited or behind an invite wall in production. Anyone can create users. |
| Anonymous sessions — no cleanup | Medium | 30-day expiry set in DB but no cron/cleanup job defined. Table grows unbounded. |
| JWT deny-list | Low | Logout is client-side only. No server-side token invalidation. Acceptable for v1. |

---

## Running Tests

```bash
cd backend
pip install pytest pytest-cov httpx
pytest tests/ -v --cov=app --cov-report=term
```

**Note:** Requires `python-dotenv` mocked env vars (handled by conftest.py).
