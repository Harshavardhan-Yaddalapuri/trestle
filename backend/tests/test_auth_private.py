"""Tests for protected/private endpoints — require authentication.

Endpoints tested:
  - POST /api/auth/logout      (requires auth)
  - GET  /api/auth/me           (requires auth)
  - POST /api/auth/merge-session (requires auth)
  - GET  /api/auth/magic-link/verify (public but tests edge cases)

Verifies:
  - 401 when no token provided
  - 401 when token is invalid/expired
  - 200 when valid token
  - WWW-Authenticate header on 401 responses
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID

from fastapi import status


# ──────────────────────────────────────────────────────────────────────────────
# GET /me
# ──────────────────────────────────────────────────────────────────────────────


class TestMe:
    """GET /api/auth/me — protected endpoint."""

    def test_me_with_valid_token(
        self, client, mock_successful_jwt_verification, mock_supabase_client
    ):
        """GET /me with valid token returns 200 + profile."""
        # Mock the DB query that _get_user_with_profile makes
        mock_supabase_client.table().select().eq().is_().limit().execute().data = [
            {
                "id": "12345678-1234-1234-1234-123456789abc",
                "email": "test@example.com",
                "name": "Test User",
                "email_verified": True,
                "created_at": "2026-01-01T00:00:00+00:00",
                "profiles": {
                    "company_name": "Acme Corp",
                    "industry_tags": ["saas", "healthcare"],
                    "team_size": 10,
                    "location_city": "San Francisco",
                    "location_state": "CA",
                    "location_country": "USA",
                    "data_status": "post_market",
                    "regulatory_pathway": "510k",
                    "completeness_score": 0.85,
                },
            }
        ]

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["email"] == "test@example.com"
        assert body["user_id"] == "12345678-1234-1234-1234-123456789abc"
        assert body["company_name"] == "Acme Corp"

    def test_me_without_token_returns_401(self, client):
        """GET /me without Authorization header returns 401."""
        response = client.get("/api/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Not authenticated"
        assert "www-authenticate" in response.headers

    def test_me_with_expired_token_returns_401(
        self, client, mock_supabase_client
    ):
        """GET /me with an expired JWT returns 401."""
        # Mock verify_supabase_jwt to raise ValueError (simulating expired)
        import app.middleware.auth as auth_mod

        async def mock_verify_expired(token):
            raise ValueError("Token verification failed: Signature has expired")

        with patch.object(auth_mod, "verify_supabase_jwt", new=mock_verify_expired):
            response = client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer expired-token"},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        detail = response.json()["detail"]
        assert "Invalid token" in detail or "expired" in detail.lower()

    def test_me_with_malformed_token_returns_401(self, client):
        """GET /me with a malformed JWT returns 401."""
        import app.middleware.auth as auth_mod

        async def mock_verify_malformed(token):
            raise ValueError("Invalid token header")

        with patch.object(auth_mod, "verify_supabase_jwt", new=mock_verify_malformed):
            response = client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer garbage"},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_with_missing_bearer_prefix_returns_401(self, client):
        """GET /me with token but no 'Bearer ' prefix returns 401."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "valid-token-without-bearer"},
        )

        # HTTPBearer doesn't recognize this format, credentials = None
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Not authenticated"

    def test_me_user_not_found_in_db(
        self, client, mock_successful_jwt_verification, mock_supabase_client
    ):
        """GET /me with valid token but user not in internal DB returns 404."""
        # _get_user_with_profile returns None
        mock_supabase_client.table().select().eq().is_().limit().execute().data = []

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "User not found"


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/logout
# ──────────────────────────────────────────────────────────────────────────────


class TestLogout:
    """POST /api/auth/logout — protected endpoint."""

    def test_logout_with_valid_token(self, client, mock_successful_jwt_verification):
        """Logout with valid token returns 200."""
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Logged out successfully."

    def test_logout_without_token_returns_401(self, client):
        """Logout without token returns 401."""
        response = client.post("/api/auth/logout")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Not authenticated"


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/auth/merge-session
# ──────────────────────────────────────────────────────────────────────────────


class TestMergeSession:
    """POST /api/auth/merge-session — protected endpoint."""

    ANON_SESSION_ID = "12345678-1234-1234-1234-123456789abc"

    def test_merge_session_without_auth_returns_401(self, client):
        """Merge-session without token returns 401."""
        response = client.post(
            "/api/auth/merge-session",
            json={"anon_session_id": self.ANON_SESSION_ID},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_merge_session_with_invalid_token_returns_401(self, client):
        """Merge-session with invalid token returns 401."""
        import app.middleware.auth as auth_mod

        async def mock_verify_fail(token):
            raise ValueError("Invalid token")

        with patch.object(auth_mod, "verify_supabase_jwt", new=mock_verify_fail):
            response = client.post(
                "/api/auth/merge-session",
                json={"anon_session_id": self.ANON_SESSION_ID},
                headers={"Authorization": "Bearer invalid-token"},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_merge_session_session_not_found(
        self, client, mock_successful_jwt_verification, mock_supabase_client
    ):
        """Merge-session with valid auth but nonexistent session returns 400."""
        # Session lookup returns empty
        mock_supabase_client.table().select().eq().is_().limit().execute().data = []

        response = client.post(
            "/api/auth/merge-session",
            json={"anon_session_id": self.ANON_SESSION_ID},
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not found" in response.json()["detail"].lower()

    def test_merge_session_already_merged(
        self, client, mock_successful_jwt_verification, mock_supabase_client
    ):
        """Merge-session on already-merged session returns 200 with merged=True."""
        mock_supabase_client.table().select().eq().is_().limit().execute().data = [
            {
                "id": self.ANON_SESSION_ID,
                "merged_at": "2026-01-01T00:00:00+00:00",
                "converted_user_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "expires_at": "2027-01-01T00:00:00+00:00",
                "profile_snapshot": {},
            }
        ]

        response = client.post(
            "/api/auth/merge-session",
            json={"anon_session_id": self.ANON_SESSION_ID},
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["merged"] is True
        assert body["conversations_migrated"] == 0
        assert "already merged" in body["message"].lower()

    def test_merge_session_expired(
        self, client, mock_successful_jwt_verification, mock_supabase_client
    ):
        """Merge-session with expired session returns 400."""
        mock_supabase_client.table().select().eq().is_().limit().execute().data = [
            {
                "id": self.ANON_SESSION_ID,
                "merged_at": None,
                "converted_user_id": None,
                "expires_at": "2020-01-01T00:00:00+00:00",  # in the past
                "profile_snapshot": {},
            }
        ]

        response = client.post(
            "/api/auth/merge-session",
            json={"anon_session_id": self.ANON_SESSION_ID},
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "expired" in response.json()["detail"].lower()

    def test_merge_session_success(
        self, client, mock_successful_jwt_verification, mock_supabase_client
    ):
        """Successful merge returns 200 and migrates conversations."""
        # First call (session lookup) returns valid session
        # Second call (conversations update) returns migrated rows
        # Third call (profiles lookup) we can mock too
        future = datetime(2027, 1, 1, tzinfo=timezone.utc)

        # We need different mock data for each query. Since all chains
        # share the same mock, we'll use side_effect on execute.
        call_count = [0]

        def execute_side_effect():
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                # Session lookup
                result.data = [
                    {
                        "id": self.ANON_SESSION_ID,
                        "merged_at": None,
                        "converted_user_id": None,
                        "expires_at": future.isoformat(),
                        "profile_snapshot": {"industry_tags": ["ai"]},
                    }
                ]
            elif call_count[0] == 2:
                # Conversations update
                result.data = [
                    {"id": "conv-1", "user_id": str(mock_successful_jwt_verification._mock_return_value[0])},
                ]
            elif call_count[0] == 3:
                # Profiles lookup
                result.data = [{"profile_json": {"existing": "data"}}]
            elif call_count[0] == 4:
                # Profile update
                result.data = []
            elif call_count[0] == 5:
                # Mark session merged
                result.data = []
            else:
                result.data = []
            return result

        mock_supabase_client.execute = MagicMock(side_effect=execute_side_effect)

        response = client.post(
            "/api/auth/merge-session",
            json={"anon_session_id": self.ANON_SESSION_ID},
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["merged"] is True
        assert body["conversations_migrated"] >= 1
        assert "conversation" in body["message"].lower()


# ──────────────────────────────────────────────────────────────────────────────
# Magic Link Verify (edge cases)
# ──────────────────────────────────────────────────────────────────────────────


class TestMagicLinkVerify:
    """GET /api/auth/magic-link/verify — public but tests edge cases."""

    def test_invalid_token_hash_returns_400(self, client):
        """Invalid/expired magic link token hash returns 400."""
        async def mock_get_fail(*args, **kwargs):
            mock = MagicMock()
            mock.status_code = 400
            mock.json.return_value = {"msg": "Invalid or expired magic link"}
            return mock

        with patch("httpx.AsyncClient.get", new=mock_get_fail):
            response = client.get(
                "/api/auth/magic-link/verify",
                params={"token_hash": "bad-hash", "type": "magiclink"},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
