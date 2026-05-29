# Trestle v1 — API Reference

**Base URL:** `http://localhost:8000`  
**Version:** 0.1.0  
**Auth:** Supabase Auth (JWT Bearer tokens)

---

## Quick Start

### Auth Flow
1. `POST /api/auth/signup` → creates account
2. `POST /api/auth/login` → returns `access_token` + `refresh_token`
3. Use `access_token` in `Authorization: Bearer <token>` for private endpoints
4. `POST /api/auth/logout` → discard token (stateless JWT, client-side)

### Anonymous Flow
1. `POST /api/auth/anonymous-session` → creates session, sets cookie
2. Use app without account (conversations tracked under session)
3. When ready to sign up: `POST /api/auth/signup`
4. `POST /api/auth/merge-session` → migrates anonymous data to account

---

## Endpoints

### Health (Public)

```
GET /health
```
**Response 200:**
```json
{
  "status": "healthy",
  "database": "connected",
  "supabase": "connected",
  "version": "0.1.0"
}
```

```
GET /health/deep
```
**Response 200:**
```json
{
  "status": "deep_check_complete",
  "results": {
    "database": "connected",
    "supabase_jwks": "reachable"
  }
}
```

---

### Auth — Signup (Public)

```
POST /api/auth/signup
```
**Request:**
```json
{
  "email": "founder@example.com",
  "password": "securepassword123",
  "name": "Jane Founder"
}
```
**Response 201:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "founder@example.com",
  "supabase_uid": "abc123...",
  "message": "Account created successfully."
}
```
**Errors:** 400 (weak password), 409 (email exists)

---

### Auth — Login (Public)

```
POST /api/auth/login
```
**Request:**
```json
{
  "email": "founder@example.com",
  "password": "securepassword123"
}
```
**Response 200:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "founder@example.com",
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "dGhpcyBpcyBh...",
  "expires_in": 3600,
  "token_type": "bearer"
}
```
**Errors:** 401 (invalid credentials)

---

### Auth — Magic Link (Public)

```
POST /api/auth/magic-link/send
```
**Request:**
```json
{
  "email": "founder@example.com",
  "anon_session_id": "optional-uuid"
}
```
**Response 200:**
```json
{
  "queued": true
}
```

```
GET /api/auth/magic-link/verify?token_hash=<hash>&type=magiclink&anon_session_id=<optional>
```
**Response 200:**
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "dGhpcyBp...",
  "user_id": "550e8400-...",
  "email": "founder@example.com"
}
```
**Errors:** 400 (invalid/expired token)

---

### Auth — Logout (Private)

```
POST /api/auth/logout
Authorization: Bearer <access_token>
```
**Response 200:**
```json
{
  "message": "Logged out successfully."
}
```
**Errors:** 401 (no token), 401 (invalid/expired token)

---

### Auth — Profile (Private)

```
GET /api/auth/me
Authorization: Bearer <access_token>
```
**Response 200:**
```json
{
  "user_id": "550e8400-...",
  "email": "founder@example.com",
  "name": "Jane Founder",
  "email_verified": true,
  "company_name": "Acme Biomed",
  "industry_tags": ["medtech", "biotech"],
  "team_size": 4,
  "location_city": "Detroit",
  "location_state": "Michigan",
  "location_country": "US",
  "data_status": "benchtop",
  "regulatory_pathway": "510k",
  "completeness_score": 0.65,
  "created_at": "2026-05-25T00:00:00Z"
}
```
**Errors:** 401 (no token), 404 (user not found)

---

### Auth — Anonymous Session (Public)

```
POST /api/auth/anonymous-session
```
**Request (all fields optional):**
```json
{
  "ip_address": null,
  "user_agent": null,
  "fingerprint": null
}
```
**Response 201:**
```json
{
  "session_id": "660e8400-e29b-41d4-a716-446655440001",
  "expires_at": "2026-06-24T00:00:00Z",
  "created_at": "2026-05-25T00:00:00Z"
}
```
Sets cookie `trestle_anon_session` (httponly, secure, samesite=lax, 30-day expiry).

```
GET /api/auth/anon-session
Cookie: trestle_anon_session=<session_id>
```
**Response 200:** Same as above. **Response 200/null:** if no cookie or session not found.

---

### Auth — Merge Session (Private)

```
POST /api/auth/merge-session
Authorization: Bearer <access_token>
```
**Request:**
```json
{
  "anon_session_id": "660e8400-e29b-41d4-a716-446655440001"
}
```
**Response 200:**
```json
{
  "merged": true,
  "conversations_migrated": 3,
  "grants_migrated": 0,
  "message": "Merged 3 conversation(s) into your account."
}
```
**Errors:** 401 (no token), 400 (session not found/expired/already merged)

---

## Security

| Control | Status |
|---------|--------|
| Private endpoints require Bearer token | ✅ Enforced via `Depends(get_current_user)` |
| JWT verified against Supabase JWKS | ✅ Cached, auto-refreshed |
| CORS restricted to frontend origin | ✅ `localhost:3000` + `FRONTEND_URL` |
| Passwords never returned in responses | ✅ Tokens only; password field excluded from all schemas |
| Cookies: httponly + secure + samesite | ✅ Anonymous session cookie |
| Input validation | ✅ Pydantic models with EmailStr, min_length, UUID parsing |

### ⚠️ Production Hardening Needed

- Add rate limiting on `/signup` to prevent mass account creation
- Implement cron job to purge expired anonymous sessions
- Set `secure=True` on cookies requires HTTPS (ensure in deploy)
- Consider adding email verification step before account activation
