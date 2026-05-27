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

from fastapi import status


# ──────────────────────────────────────────────────────────────────────────────
# Health endpoints
# ──────────────────────────────────────────────────────────────────────────────


class TestHealth:
    """Public health endpoints — no auth needed."""

    def test_health_returns_200(self, client):
        """GET /health should return 200 OK without any auth."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert "status" in body
        assert "database" in body
        assert "supabase" in body

    def test_health_deep_returns_200(self, client):
        """GET /health/deep should return 200 OK without any auth."""
        response = client.get("/health/deep")
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
    """POST /api/auth/signup tests."""

    def test_signup_minimal_valid(
        self, client, mock_supabase_httpx_signup_success, mock_supabase_client
    ):
        """Minimal valid signup (email + password only) returns 201."""
        mock_supabase_client.table().insert().execute().data = [
            {"id": "12345678-1234-1234-1234-123456789abc"}
        ]

        payload = {"email": "newuser@example.com", "password": "StrongP@ss1"}
        response = client.post("/api/auth/signup", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["email"] == "newuser@example.com"
        assert "user_id" in body
        assert "supabase_uid" in body
        assert body["message"] == "Account created successfully."

    def test_signup_with_name(
        self, client, mock_supabase_httpx_signup_success, mock_supabase_client
    ):
        """Signup with optional name field."""
        mock_supabase_client.table().insert().execute().data = [
            {"id": "12345678-1234-1234-1234-123456789abc"}
        ]

        payload = {
            "email": "newuser@example.com",
            "password": "StrongP@ss1",
            "name": "Test User",
        }
        response = client.post("/api/auth/signup", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

    def test_signup_missing_email(self, client):
        """Signup without email should return 422."""
        response = client.post("/api/auth/signup", json={"password": "StrongP@ss1"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_signup_missing_password(self, client):
        """Signup without password should return 422."""
        response = client.post("/api/auth/signup", json={"email": "user@example.com"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_signup_empty_body(self, client):
        """Signup with empty body returns 422."""
        response = client.post("/api/auth/signup", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_signup_invalid_email_format(self, client):
        """Signup with invalid email returns 422."""
        response = client.post(
            "/api/auth/signup",
            json={"email": "not-an-email", "password": "StrongP@ss1"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_signup_weak_password(self, client):
        """Signup with password < 8 chars returns 422."""
        response = client.post(
            "/api/auth/signup",
            json={"email": "user@example.com", "password": "short"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_signup_duplicate_email(self, client):
        """Signup with email that Supabase rejects returns error status."""
        # Simulate Supabase admin API returning conflict
        async def mock_post_fail(*args, **kwargs):
            mock = MagicMock()
            mock.status_code = 400
            mock.json.return_value = {"msg": "A user with this email already exists"}
            return mock

        with patch("httpx.AsyncClient.post", new=mock_post_fail):
            response = client.post(
                "/api/auth/signup",
                json={"email": "existing@example.com", "password": "StrongP@ss1"},
            )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()


# ──────────────────────────────────────────────────────────────────────────────
# Login
# ──────────────────────────────────────────────────────────────────────────────


class TestLogin:
    """POST /api/auth/login tests."""

    def test_login_valid_credentials(
        self, client, mock_supabase_httpx_login_success, mock_supabase_client
    ):
        """Login with valid email + password returns 200 + tokens."""
        mock_supabase_client.table().select().eq().is_().limit().execute().data = [
            {"id": "12345678-1234-1234-1234-123456789abc"}
        ]

        response = client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "CorrectH0rse!"},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["access_token"] == "fake-access-token"
        assert body["refresh_token"] == "fake-refresh-token"
        assert body["expires_in"] == 3600
        assert "user_id" in body

    def test_login_wrong_password(self, client):
        """Login with wrong password returns 401."""
        async def mock_post_fail(*args, **kwargs):
            mock = MagicMock()
            mock.status_code = 400
            mock.json.return_value = {"error_description": "Invalid login credentials"}
            return mock

        with patch("httpx.AsyncClient.post", new=mock_post_fail):
            response = client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "WrongPass!"},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, client):
        """Login with nonexistent email returns 401."""
        async def mock_post_fail(*args, **kwargs):
            mock = MagicMock()
            mock.status_code = 400
            mock.json.return_value = {"error_description": "Invalid login credentials"}
            return mock

        with patch("httpx.AsyncClient.post", new=mock_post_fail):
            response = client.post(
                "/api/auth/login",
                json={"email": "ghost@example.com", "password": "Anything1!"},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_missing_email(self, client):
        """Login without email returns 422."""
        response = client.post("/api/auth/login", json={"password": "CorrectH0rse!"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_missing_password(self, client):
        """Login without password returns 422."""
        response = client.post("/api/auth/login", json={"email": "test@example.com"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_invalid_email(self, client):
        """Login with malformed email returns 422."""
        response = client.post(
            "/api/auth/login",
            json={"email": "bad-email", "password": "CorrectH0rse!"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ──────────────────────────────────────────────────────────────────────────────
# Magic Link
# ──────────────────────────────────────────────────────────────────────────────


class TestMagicLinkSend:
    """POST /api/auth/magic-link/send tests."""

    def test_send_magic_link_valid_email(
        self, client, mock_supabase_httpx_magiclink_success
    ):
        """Sending magic link to a valid email returns 200 with queued=True."""
        response = client.post(
            "/api/auth/magic-link/send",
            json={"email": "user@example.com"},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["queued"] is True

    def test_send_magic_link_with_anon_session(
        self, client, mock_supabase_httpx_magiclink_success
    ):
        """Magic link with attached anonymous session ID."""
        response = client.post(
            "/api/auth/magic-link/send",
            json={
                "email": "user@example.com",
                "anon_session_id": "12345678-1234-1234-1234-123456789abc",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["queued"] is True

    def test_send_magic_link_invalid_email(self, client):
        """Magic link with invalid email returns 422."""
        response = client.post(
            "/api/auth/magic-link/send",
            json={"email": "not-an-email"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_send_magic_link_missing_email(self, client):
        """Magic link without email returns 422."""
        response = client.post("/api/auth/magic-link/send", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_send_magic_link_supabase_error(self, client):
        """If Supabase returns 400+, should propagate as HTTPException."""
        async def mock_post_fail(*args, **kwargs):
            mock = MagicMock()
            mock.status_code = 429
            mock.json.return_value = {"msg": "Too many requests"}
            return mock

        with patch("httpx.AsyncClient.post", new=mock_post_fail):
            response = client.post(
                "/api/auth/magic-link/send",
                json={"email": "user@example.com"},
            )

        assert response.status_code == 429


# ──────────────────────────────────────────────────────────────────────────────
# Anonymous Session
# ──────────────────────────────────────────────────────────────────────────────


class TestAnonymousSession:
    """POST /api/auth/anonymous-session tests."""

    def test_create_anonymous_session_basic(self, client, mock_supabase_client):
        """Create anonymous session with no optional fields."""
        response = client.post("/api/auth/anonymous-session", json={})

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert "session_id" in body
        assert "expires_at" in body
        assert "created_at" in body

        # Verify UUID format
        UUID(body["session_id"])

        # Verify expiry is in the future
        expires = datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00"))
        created = datetime.fromisoformat(body["created_at"].replace("Z", "+00:00"))
        assert expires > created
        # Should expire ~30 days out
        delta = expires - created
        assert delta.days >= 29

    def test_anonymous_session_sets_cookie(self, client, mock_supabase_client):
        """Anonymous session should set a signed cookie."""
        response = client.post("/api/auth/anonymous-session", json={})

        assert response.status_code == status.HTTP_201_CREATED
        cookies = response.cookies
        assert "trestle_anon_session" in cookies
        assert len(cookies["trestle_anon_session"]) > 0

    def test_anonymous_session_with_fingerprint(self, client, mock_supabase_client):
        """Anonymous session with fingerprint and user_agent."""
        payload = {
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0 Test",
            "fingerprint": "fp_abc123",
        }
        response = client.post("/api/auth/anonymous-session", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert "session_id" in response.json()

    def test_anonymous_session_invalid_body(self, client):
        """Anonymous session with wrong field type returns 422."""
        response = client.post(
            "/api/auth/anonymous-session",
            json={"fingerprint": 12345},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ──────────────────────────────────────────────────────────────────────────────
# Get Anonymous Session
# ──────────────────────────────────────────────────────────────────────────────


class TestGetAnonSession:
    """GET /api/auth/anon-session tests."""

    def test_no_cookie_returns_null(self, client):
        """Without cookie, returns null."""
        response = client.get("/api/auth/anon-session")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() is None

    def test_invalid_cookie_returns_null(self, client):
        """With malformed cookie, returns null."""
        client.cookies.set("trestle_anon_session", "not-a-uuid")
        response = client.get("/api/auth/anon-session")
        client.cookies.clear()
        assert response.status_code == status.HTTP_200_OK
        assert response.json() is None

    def test_valid_cookie_but_session_not_found(self, client, mock_supabase_client):
        """Cookie exists but DB returns no row — returns null."""
        mock_supabase_client.table().select().eq().is_().limit().execute().data = []

        client.cookies.set(
            "trestle_anon_session",
            "12345678-1234-1234-1234-123456789abc",
        )
        response = client.get("/api/auth/anon-session")
        client.cookies.clear()

        assert response.status_code == status.HTTP_200_OK
        assert response.json() is None

    def test_valid_session_returns_data(self, client, mock_supabase_client):
        """Valid cookie + DB row returns session info."""
        now = datetime.now(timezone.utc)
        mock_supabase_client.table().select().eq().is_().limit().execute().data = [
            {
                "id": "12345678-1234-1234-1234-123456789abc",
                "expires_at": "2026-06-25T00:00:00+00:00",
                "created_at": now.isoformat(),
            }
        ]

        client.cookies.set(
            "trestle_anon_session",
            "12345678-1234-1234-1234-123456789abc",
        )
        response = client.get("/api/auth/anon-session")
        client.cookies.clear()

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body is not None
        assert body["session_id"] == "12345678-1234-1234-1234-123456789abc"
