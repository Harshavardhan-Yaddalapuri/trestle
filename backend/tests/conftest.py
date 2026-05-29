"""Shared test fixtures for Trestle v1 backend tests."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def mock_settings_env(monkeypatch):
    """Override settings so tests don't need a real .env file."""
    monkeypatch.setenv("SUPABASE_URL", "https://test-project.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "test-model")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")


def _make_fresh_mock_supabase():
    """Create a fresh supabase mock with chainable API."""
    mock = MagicMock()
    mock_execute = MagicMock()
    mock_execute.data = []
    mock_execute.count = 0

    def _chain(*args, **kwargs):
        return mock

    mock.table = MagicMock(side_effect=_chain)
    mock.select = MagicMock(return_value=mock)
    mock.insert = MagicMock(return_value=mock)
    mock.update = MagicMock(return_value=mock)
    mock.delete = MagicMock(return_value=mock)
    mock.eq = MagicMock(return_value=mock)
    mock.neq = MagicMock(return_value=mock)
    mock.is_ = MagicMock(return_value=mock)
    mock.limit = MagicMock(return_value=mock)
    mock.order = MagicMock(return_value=mock)
    mock.range = MagicMock(return_value=mock)
    mock.single = MagicMock(return_value=mock)
    mock.execute = MagicMock(return_value=mock_execute)
    mock.rpc = MagicMock(return_value=mock_execute)
    return mock


@pytest.fixture(autouse=True)
def mock_supabase_client():
    """Globally mock the supabase client so no real DB calls are made.

    Patches both the source module AND any module that imported supabase
    via ``from app.database import supabase`` (which creates a local
    reference that won't see the source patch).  Each call returns a
    fresh mock to avoid state leakage across tests.

    Applied AUTOMATICALLY to every test — no test should ever make real
    Supabase calls. Tests that need specific DB responses configure the
    mock's return values before executing.
    """
    fresh = _make_fresh_mock_supabase()
    with patch("app.database.supabase", fresh), \
         patch("app.routers.auth.supabase", fresh), \
         patch("app.main.supabase", fresh):
        yield fresh


# ─── Auth helpers ────────────────────────────────────────────────────────────

VALID_USER_UUID = UUID("12345678-1234-1234-1234-123456789abc")
VALID_SUPABASE_UID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
VALID_EMAIL = "test@example.com"


@pytest.fixture
def mock_successful_jwt_verification():
    """Patch verify_supabase_jwt to return a valid user."""
    with patch(
        "app.middleware.auth.verify_supabase_jwt",
        new_callable=AsyncMock,
    ) as mock_verify:
        mock_verify.return_value = (VALID_SUPABASE_UID, VALID_EMAIL)
        yield mock_verify


@pytest.fixture
def mock_supabase_httpx_signup_success():
    """Mock httpx.AsyncClient.post for signup returning success."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            "id": str(VALID_SUPABASE_UID),
            "email": VALID_EMAIL,
        }
        mock_post.return_value = mock_resp
        yield mock_post


@pytest.fixture
def mock_supabase_httpx_login_success():
    """Mock httpx.AsyncClient.post for login returning success."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "fake-access-token",
            "refresh_token": "fake-refresh-token",
            "expires_in": 3600,
            "user": {
                "id": str(VALID_SUPABASE_UID),
                "email": VALID_EMAIL,
            },
        }
        mock_post.return_value = mock_resp
        yield mock_post


@pytest.fixture
def mock_supabase_httpx_magiclink_success():
    """Mock httpx.AsyncClient.post for magic link sending."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_post.return_value = mock_resp
        yield mock_post


@pytest.fixture(autouse=True)
def mock_all_httpx():
    """Mock ALL httpx.AsyncClient methods to prevent actual network calls.

    Applied AUTOMATICALLY to every test. Tests that need SPECIFIC
    httpx responses (signup, login, magic link) use their own fixtures
    that override this one via nested patching.

    The default mock returns a generic 200 with a json body that is
    structured enough to not crash the most common auth endpoints
    (signup needs ``id``, login needs ``user.id``).
    """
    def _make_generic_response():
        mock = MagicMock()
        mock.status_code = 200
        mock.json.return_value = {
            "id": str(VALID_SUPABASE_UID),
            "email": VALID_EMAIL,
            "user": {
                "id": str(VALID_SUPABASE_UID),
                "email": VALID_EMAIL,
            },
            "access_token": "fake-access-token",
            "refresh_token": "fake-refresh-token",
            "expires_in": 3600,
        }
        return mock

    async def mock_post_success(*args, **kwargs):
        return _make_generic_response()

    async def mock_get_success(*args, **kwargs):
        return _make_generic_response()

    with patch("httpx.AsyncClient.post", new=mock_post_success), \
         patch("httpx.AsyncClient.get", new=mock_get_success):
        yield


# ─── TestClient ──────────────────────────────────────────────────────────────


@pytest.fixture
def client(mock_settings_env):
    """FastAPI TestClient for integration-style tests."""
    from app.main import app

    return TestClient(app)
