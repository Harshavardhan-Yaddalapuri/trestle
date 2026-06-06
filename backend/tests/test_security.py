"""Security tests — CORS, rate limiting, token edge cases.

Tests:
  - CORS headers present on responses
  - OPTIONS preflight returns correct CORS headers
  - Token edge cases (expired, malformed, missing Bearer prefix)
  - 401 responses include WWW-Authenticate header
  - Public endpoints accessible without auth
  - Protected endpoints reject unauthenticated requests
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import status


# ──────────────────────────────────────────────────────────────────────────────
# CORS Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestCORS:
    """Verify CORS middleware is configured correctly."""

    @pytest.mark.asyncio
    async def test_options_preflight_returns_cors_headers(self, client):
        """OPTIONS request should return proper CORS headers."""
        response = await client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

    @pytest.mark.asyncio
    async def test_cors_headers_on_normal_response(self, client):
        """Regular GET response should include CORS headers."""
        response = await client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access-control-allow-origin" in response.headers
        # allow_credentials=True should set this
        assert "access-control-allow-credentials" in response.headers
        assert (
            response.headers["access-control-allow-credentials"].lower() == "true"
        )

    @pytest.mark.asyncio
    async def test_cors_allows_allowed_origin(self, client):
        """Allowed origin (localhost:3000) should be reflected."""
        response = await client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )

        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"

    @pytest.mark.asyncio
    async def test_cors_allows_127_origin(self, client):
        """Allowed origin (127.0.0.1:3000) should be reflected."""
        response = await client.get(
            "/health",
            headers={"Origin": "http://127.0.0.1:3000"},
        )

        assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"

    @pytest.mark.asyncio
    async def test_cors_post_with_credentials(self, client):
        """POST request with credentials: include should have CORS headers."""
        response = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpass123"},
            headers={
                "Origin": "http://localhost:3000",
            },
        )

        # Even 401 responses should have CORS headers
        assert "access-control-allow-origin" in response.headers

    @pytest.mark.asyncio
    async def test_options_preflight_health(self, client):
        """OPTIONS preflight on health endpoint."""
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access-control-allow-origin" in response.headers


# ──────────────────────────────────────────────────────────────────────────────
# Token Validation Edge Cases
# ──────────────────────────────────────────────────────────────────────────────


class TestTokenValidation:
    """Edge cases for JWT token validation."""

    @pytest.mark.asyncio
    async def test_no_authorization_header_at_all(self, client):
        """Protected endpoint with no Authorization header → 401."""
        response = await client.get("/api/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Not authenticated"

    @pytest.mark.asyncio
    async def test_empty_authorization_header(self, client):
        """Protected endpoint with empty Authorization header → 401."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": ""},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_bearer_with_empty_token(self, client):
        """Protected endpoint with 'Bearer ' but no token → 401."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_bearer_with_whitespace_only(self, client):
        """Protected endpoint with 'Bearer    ' whitespace → 401."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer    "},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_wrong_scheme_not_bearer(self, client):
        """Token with wrong scheme (not Bearer) → 401."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        # HTTPBearer only accepts "Bearer" scheme → credentials=None
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Not authenticated"

    @pytest.mark.asyncio
    async def test_missing_bearer_prefix(self, client):
        """Token present but missing 'Bearer ' prefix → 401."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "some-jwt-token"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Not authenticated"

    @pytest.mark.asyncio
    async def test_expired_token_mocked(self, client):
        """Expired token returns 401 with descriptive message."""
        import backend.middleware.auth as auth_mod

        def mock_verify_expired(token: str):
            raise ValueError("Token verification failed: Signature has expired")

        with patch.object(auth_mod, "_verify_token", new=mock_verify_expired):
            response = await client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer expired-jwt"},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        detail = response.json()["detail"]
        assert "Invalid token" in detail

    @pytest.mark.asyncio
    async def test_malformed_token_no_kid(self, client):
        """Token without 'kid' in header → 401."""
        import backend.middleware.auth as auth_mod

        def mock_verify_no_kid(token: str):
            raise ValueError("Token missing 'kid' header")

        with patch.object(auth_mod, "_verify_token", new=mock_verify_no_kid):
            response = await client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer token-no-kid"},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_token_with_invalid_signature(self, client):
        """Token with invalid crypto signature → 401."""
        import backend.middleware.auth as auth_mod

        def mock_verify_bad_sig(token: str):
            raise ValueError("Token verification failed: Signature verification failed")

        with patch.object(auth_mod, "_verify_token", new=mock_verify_bad_sig):
            response = await client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer bad-sig-token"},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ──────────────────────────────────────────────────────────────────────────────
# 401 WWW-Authenticate Header
# ──────────────────────────────────────────────────────────────────────────────


class TestWWWAuthenticateHeader:
    """Verify 401 responses include WWW-Authenticate header."""

    @pytest.mark.asyncio
    async def test_401_includes_www_authenticate(self, client):
        """All 401 responses from protected endpoints include WWW-Authenticate."""
        protected_endpoints = [
            ("GET", "/api/auth/me"),
            ("POST", "/api/auth/logout"),
            ("POST", "/api/auth/merge-session"),
        ]

        for method, path in protected_endpoints:
            if method == "GET":
                response = await client.get(path)
            else:
                response = await client.post(path, json={})

            assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
                f"{method} {path} did not return 401"
            )
            assert "www-authenticate" in response.headers, (
                f"{method} {path} missing WWW-Authenticate header"
            )
            assert response.headers["www-authenticate"].lower() == "bearer"

    @pytest.mark.asyncio
    async def test_public_endpoints_accessible_without_auth(self, client):
        """All public endpoints return success without any auth headers."""
        public_endpoints = [
            ("GET", "/health"),
            ("GET", "/health/deep"),
        ]

        for method, path in public_endpoints:
            response = await client.get(path)
            assert response.status_code == status.HTTP_200_OK, (
                f"Public endpoint {path} did not return 200 (got {response.status_code})"
            )


# ──────────────────────────────────────────────────────────────────────────────
# Content-Type / Security Headers
# ──────────────────────────────────────────────────────────────────────────────


class TestSecurityHeaders:
    """Verify security-related response headers."""

    @pytest.mark.asyncio
    async def test_json_content_type(self, client):
        """API responses should have Content-Type: application/json."""
        response = await client.get("/health")
        assert "application/json" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_422_validation_error_format(self, client):
        """422 responses should include detail array for validation errors."""
        response = await client.post("/api/auth/signup", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        body = response.json()
        assert "detail" in body
        # detail should be an array of validation errors
        assert isinstance(body["detail"], list)
        assert len(body["detail"]) > 0

    @pytest.mark.asyncio
    async def test_anonymous_session_cookie_httponly(self, client, mock_supabase_client):
        """Anonymous session cookie should be marked httponly."""
        response = await client.post("/api/auth/anonymous-session", json={})

        # TestClient stores cookies; we check the Set-Cookie header
        set_cookie = response.headers.get("set-cookie", "")
        assert "httponly" in set_cookie.lower() or "HttpOnly" in set_cookie
        assert "secure" in set_cookie.lower() or "Secure" in set_cookie
        assert "samesite" in set_cookie.lower() or "SameSite" in set_cookie


# ──────────────────────────────────────────────────────────────────────────────
# Auth Bypass Attempts
# ──────────────────────────────────────────────────────────────────────────────


class TestAuthBypass:
    """Test that common auth bypass techniques don't work."""

    @pytest.mark.asyncio
    async def test_no_auth_on_logout(self, client):
        """Logout without auth should fail with 401."""
        response = await client.post("/api/auth/logout")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_no_auth_on_merge(self, client):
        """Merge-session without auth should fail with 401."""
        response = await client.post(
            "/api/auth/merge-session",
            json={"anon_session_id": "12345678-1234-1234-1234-123456789abc"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_health_always_public(self, client):
        """Health endpoints should always be accessible (no auth needed)."""
        assert (await client.get("/health")).status_code == 200
        assert (await client.get("/health/deep")).status_code == 200

    @pytest.mark.asyncio
    async def test_signup_always_public(self, client):
        """Signup should be accessible without auth (but will fail validation)."""
        # Even with bad payload, it's accessible (gets 422, not 401)
        response = await client.post("/api/auth/signup", json={"email": "x@y.com"})
        assert response.status_code != 401  # Not an auth error

    @pytest.mark.asyncio
    async def test_login_always_public(self, client):
        """Login should be accessible without auth."""
        response = await client.post(
            "/api/auth/login",
            json={"email": "x@y.com", "password": "test"},
        )
        # Either 401 (bad credentials) or 422 (bad input), but never 401 from our auth middleware
        # The 401 from login comes from Supabase, not from get_current_user
        assert response.status_code != 401 or "Invalid login" in response.json().get("detail", "")

    @pytest.mark.asyncio
    async def test_anon_session_always_public(self, client, mock_supabase_client):
        """Anonymous session creation should always be public."""
        response = await client.post("/api/auth/anonymous-session", json={})
        assert response.status_code == 201
