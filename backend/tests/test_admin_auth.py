from __future__ import annotations

import pytest
from starlette.requests import Request

from backend.api.admin import _require_admin
from backend.core.config import Settings
from backend.core.config import get_settings
from backend.core.errors import AuthenticationError


def _reload_settings(monkeypatch, *, environment: str, admin_api_key: str | None):
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("CORS_ORIGINS", "[\"http://localhost:3000\"]")
    if environment.lower() in {"production", "prod"}:
        monkeypatch.setenv("AUTH_IP_HASH_PEPPER", "pepper")
    else:
        monkeypatch.delenv("AUTH_IP_HASH_PEPPER", raising=False)
    if admin_api_key is None:
        monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    else:
        monkeypatch.setenv("ADMIN_API_KEY", admin_api_key)
    get_settings.cache_clear()
    return get_settings()

def _request_with_admin_key(value: str | None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if value is not None:
        headers.append((b"x-admin-key", value.encode("utf-8")))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/admin/verification/runs",
        "headers": headers,
        "query_string": b"",
    }
    return Request(scope)


def test_admin_requires_key_outside_dev(monkeypatch):
    settings = _reload_settings(
        monkeypatch,
        environment="production",
        admin_api_key="super-secret",
    )

    with pytest.raises(AuthenticationError):
        _require_admin(_request_with_admin_key(None), settings)

    get_settings.cache_clear()


def test_admin_allows_valid_key_outside_dev(monkeypatch):
    settings = _reload_settings(
        monkeypatch,
        environment="production",
        admin_api_key="super-secret",
    )

    _require_admin(_request_with_admin_key("super-secret"), settings)

    get_settings.cache_clear()


def test_admin_allows_dev_without_key(monkeypatch):
    settings = _reload_settings(
        monkeypatch,
        environment="development",
        admin_api_key=None,
    )

    _require_admin(_request_with_admin_key(None), settings)

    get_settings.cache_clear()


def test_settings_require_admin_key_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("AUTH_IP_HASH_PEPPER", "pepper")
    monkeypatch.setenv("CORS_ORIGINS", "[\"http://localhost:3000\"]")
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="ADMIN_API_KEY"):
        Settings()
    get_settings.cache_clear()
