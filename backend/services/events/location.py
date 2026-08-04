"""Parsing for the flat location labels that event APIs expose.

Providers such as Techstars publish a single human-readable string instead of a
structured address ("Panambi, Brazil", "Iowa City, IA", "Virtual"). This module
splits those into the city/region/country columns the events table stores.
"""
from __future__ import annotations

import re

from backend.services.events.taxonomy import normalize_text

_VIRTUAL_LABELS = frozenset({"virtual", "online", "remote", "worldwide", "global"})

# In a two-part label a short uppercase code is an administrative region
# ("Iowa City, IA") while a longer segment is a country ("Panambi, Brazil").
_REGION_CODE_RE = re.compile(r"^[A-Z]{2,3}$")


class ParsedLocation:
    """Structured view of a flat location label."""

    __slots__ = ("is_virtual", "text", "city", "region", "country")

    def __init__(
        self,
        *,
        is_virtual: bool = False,
        text: str | None = None,
        city: str | None = None,
        region: str | None = None,
        country: str | None = None,
    ) -> None:
        self.is_virtual = is_virtual
        self.text = text
        self.city = city
        self.region = region
        self.country = country


def parse_location_label(label: str | None) -> ParsedLocation:
    """Split a flat location label into virtual flag, city, region and country."""
    text = normalize_text(label)
    if not text:
        return ParsedLocation()

    if text.lower() in _VIRTUAL_LABELS:
        return ParsedLocation(is_virtual=True, text=text)

    parts = [part.strip() for part in text.split(",") if part.strip()]
    if not parts:
        return ParsedLocation(text=text)
    if len(parts) == 1:
        return ParsedLocation(text=text, city=parts[0])

    city = parts[0]
    tail = parts[-1]

    if len(parts) == 2:
        if _REGION_CODE_RE.match(tail):
            return ParsedLocation(text=text, city=city, region=tail)
        return ParsedLocation(text=text, city=city, country=tail)

    # Three or more segments always end with the country ("Austin, Texas, USA").
    return ParsedLocation(text=text, city=city, region=parts[1], country=tail)
