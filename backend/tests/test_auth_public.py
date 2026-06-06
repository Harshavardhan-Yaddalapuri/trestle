"""Tests for public endpoints — no authentication required.

Endpoints tested:
  - GET  /health
  - GET  /health/deep
  - POST /api/auth/signup
  - POST /api/auth/login
  - POST /api/auth/magic-link/send
  - POST /api/auth/anonymous-session
  - GET  /api/auth/anon-session
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi import status


# ──────────────────────────────────────────────────────────────────────────────
# Health endpoints
# ──────────────────────────────────────────────────────────────────────────────


class TestHealth:
    """Public health endpoints — no auth needed."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        """GET /health should return 200 OK without any auth."""
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert "status" in body
        assert "database" in body
        assert "supabase" in body

    @pytest.mark.asyncio
    async def test_health_deep_returns_200(self, client):
        """GET /health/deep should return 200 OK without any auth."""
        response = await client.get("/health/deep")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["status"] == "deep_check_complete"
        assert "results" in body
        assert "database" in body["results"]
        assert "supabase_jwks" in body["results"]


# ──────────────────────────────────────────────────────────────────────────────
# Signup
# ──────────────────────────────────────────────────────────────────────────────


class TestSignup:
    """POST /api/auth/signup — public endpoint."""

    @pytest.mark.asyncio
    async def test_signup_success(
        self, client, mock_supabase_client, mock_supabase_httpx_signup_success
    ):
        """Signup with valid credentials returns 201 and user data."""
        mock_supabase_client.table().insert().execute().data = [
            {
                "id": "user-123",
                "email": "new@example.com",
                "supabase_uid": "supabase-uid-123",
            }
        ]

        response = await client.post(
            "/api/auth/signup",
            json={
                "email": "new@example.com",
                "password": "SecurePass123!",
                "name": "New User",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["email"] == "new@example.com"
        assert "user_id" in body

    @pytest.mark.asyncio
    async def test_signup_missing_email_returns_422(self, client):
        """Signup without email returns 422."""
        response = await client.post(
            "/api/auth/signup",
            json={"password": "SecurePass123!"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_signup_missing_password_returns_422(self, client):
        """Signup without password returns 422."""
        response = await client.post(
            "/api/auth/signup",
            json={"email": "new@example.com"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_signup_supabase_error(self, client):
        """Signup when Supabase returns error propagates the error."""
        import httpx

        async def _mock_post(*args, **kwargs):
            mock = MagicMock()
            mock.status_code = 400
            mock.json.return_value = {"msg": "User already registered"}
            return mock

        with patch.object(httpx.AsyncClient, "post", new=_mock_post):
            response = await client.post(
                "/api/auth/signup",
                json={
                    "email": "existing@example.com",
                    "password": "SecurePass123!",
                },
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()


# ──────────────────────────────────────────────────────────────────────────────
# Login
# ──────────────────────────────────────────────────────────────────────────────


class TestLogin:
    """POST /api/auth/login — public endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(
        self, client, mock_supabase_client, mock_supabase_httpx_login_success
    ):
        """Login with valid credentials returns tokens."""
        mock_supabase_client.table().select().eq().is_().limit().execute().data = [
            {"id": "user-123", "email": "test@example.com"}
        ]

        response = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpass123"},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert "expires_in" in body
        assert "user_id" in body

    @pytest.mark.asyncio
    async def test_login_missing_email_returns_422(self, client):
        """Login without email returns 422."""
        response = await client.post(
            "/api/auth/login",
            json={"password": "testpass123"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_login_missing_password_returns_422(self, client):
        """Login without password returns 422."""
        response = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client):
        """Login with wrong credentials returns 401."""
        import httpx

        async def _mock_post(*args, **kwargs):
            mock = MagicMock()
            mock.status_code = 400
            mock.json.return_value = {
                "error": "invalid_credentials",
                "error_description": "Invalid login credentials",
            }
            return mock

        with patch.object(httpx.AsyncClient, "post", new=_mock_post):
            response = await client.post(
                "/api/auth/login",
                json={"email": "wrong@example.com", "password": "wrongpass"},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid" in response.json()["detail"].lower()


# ──────────────────────────────────────────────────────────────────────────────
# Magic Link
# ──────────────────────────────────────────────────────────────────────────────


class TestMagicLink:
    """POST /api/auth/magic-link/send — public endpoint."""

    @pytest.mark.asyncio
    async def test_send_magic_link_success(self, client, mock_supabase_httpx_magiclink_success):
        """Magic link send returns 200 when Supabase succeeds."""
        response = await client.post(
            "/api/auth/magic-link/send",
            json={"email": "test@example.com"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["queued"] is True

    @pytest.mark.asyncio
    async def test_send_magic_link_missing_email_returns_422(self, client):
        """Magic link send without email returns 422."""
        response = await client.post(
            "/api/auth/magic-link/send",
            json={},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ──────────────────────────────────────────────────────────────────────────────
# Anonymous Session
# ──────────────────────────────────────────────────────────────────────────────


class TestAnonymousSession:
    """POST /api/auth/anonymous-session — public endpoint."""

    @pytest.mark.asyncio
    async def test_create_anonymous_session(self, client):
        """Anonymous session creation returns 201 with session_id."""
        response = await client.post("/api/auth/anonymous-session", json={})

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert "session_id" in body
        assert "expires_at" in body
        assert "created_at" in body

        # Verify cookie is set
        set_cookie = response.headers.get("set-cookie", "")
        assert "trestle_session_id" in set_cookie or "trestle_anon_session" in set_cookie

    @pytest.mark.asyncio
    async def test_anon_session_cookie_persists(self, client):
        """Subsequent requests carry the anonymous session cookie."""
        # First, create a session
        response = await client.post("/api/auth/anonymous-session", json={})
        assert response.status_code == status.HTTP_201_CREATED

        # Then hit anon-session endpoint which reads the cookie
        response = await client.get("/api/auth/anon-session")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert "session_id" in body

    @pytest.mark.asyncio
    async def test_get_anon_session_without_cookie(self, client):
        """GET /anon-session without cookie returns None (200 with null body)."""
        response = await client.get("/api/auth/anon-session")
        # The endpoint returns None when no session; FastAPI renders as 200 with null body
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT)

    @pytest.mark.asyncio
    async def test_get_anon_session_with_invalid_cookie(self, client):
        """GET /anon-session with malformed cookie returns None."""
        response = await client.get(
            "/api/auth/anon-session",
            headers={"X-Session-Id": "not-a-uuid"},
        )
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT)


# ──────────────────────────────────────────────────────────────────────────────
# CORS / OPTIONS preflight on public endpoints
# ──────────────────────────────────────────────────────────────────────────────


class TestCORSPreflightPublic:
    """OPTIONS preflight should work on all public auth endpoints."""

    @pytest.mark.asyncio
    async def test_options_preflight_login(self, client):
        """OPTIONS /api/auth/login returns CORS headers."""
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

    @pytest.mark.asyncio
    async def test_options_preflight_signup(self, client):
        """OPTIONS /api/auth/signup returns CORS headers."""
        response = await client.options(
            "/api/auth/signup",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access-control-allow-origin" in response.headers
