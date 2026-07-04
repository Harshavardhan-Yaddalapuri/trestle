"""Adapter registry — maps source name to adapter class."""
from __future__ import annotations

from typing import Any

from backend.services.ingest.adapters.grantsgov import GrantsGovAdapter
from backend.services.ingest.adapters.sbirgov import SbirGovAdapter

_ADAPTERS: dict[str, type] = {
    "grantsgov": GrantsGovAdapter,
    "sbirgov": SbirGovAdapter,
}


def get_adapter(source: str) -> type | None:
    return _ADAPTERS.get(source)


def get_enabled_sources(settings: Any) -> list[str]:
    """Return names of adapters that are enabled in settings."""
    enabled: list[str] = []
    if settings.GRANTSGOV_ENABLED:
        enabled.append("grantsgov")
    if settings.SBIRGOV_ENABLED:
        enabled.append("sbirgov")
    return enabled
