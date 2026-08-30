"""Canonical country and U.S. state matching for inconsistent event source data."""
from __future__ import annotations

from typing import Literal

import pycountry

from backend.db.models.event import Event

LocationScope = Literal["anywhere", "state", "country"]

_COUNTRY_ALIASES = {
    "u.s.": "US",
    "u.s.a.": "US",
    "united states": "US",
    "united states of america": "US",
    "usa": "US",
    "u.k.": "GB",
    "uk": "GB",
    "great britain": "GB",
}

_US_STATE_CODES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC",
}


def normalize_country(value: str | None) -> str | None:
    """Return an ISO-3166 alpha-2 country code for a code or recognized name."""
    if not value:
        return None

    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized in _COUNTRY_ALIASES:
        return _COUNTRY_ALIASES[normalized]

    try:
        return str(pycountry.countries.lookup(value.strip()).alpha_2)
    except LookupError:
        return None


def normalize_us_state(value: str | None) -> str | None:
    """Return a USPS state code for a U.S. state code or name."""
    if not value:
        return None

    normalized = value.strip().lower()
    if normalized in _US_STATE_CODES:
        return _US_STATE_CODES[normalized]

    state_code = value.strip().upper()
    return state_code if state_code in _US_STATE_CODES.values() else None


def _event_location_parts(event: Event) -> list[str]:
    """Return every structured and comma-separated location part on an event."""
    parts = [value for value in (event.country, event.region) if value]
    if event.location_text:
        parts.extend(part.strip() for part in event.location_text.split(",") if part.strip())
    return parts


def event_is_in_country(event: Event, country_code: str | None) -> bool:
    normalized_country = normalize_country(country_code)
    return bool(
        normalized_country
        and any(normalize_country(part) == normalized_country for part in _event_location_parts(event))
    )


def event_is_in_state(
    event: Event,
    state_code: str | None,
    country_code: str | None,
) -> bool:
    """Match U.S. events by a normalized state code, rejecting non-U.S. records."""
    normalized_state = normalize_us_state(state_code)
    if normalize_country(country_code) != "US" or not normalized_state:
        return False

    event_country = normalize_country(event.country)
    if event_country is not None and event_country != "US":
        return False
    return any(normalize_us_state(part) == normalized_state for part in _event_location_parts(event))


def event_matches_location_scope(
    event: Event,
    scope: LocationScope,
    *,
    state_code: str | None,
    country_code: str | None,
) -> bool:
    """Return whether an in-person event belongs in the selected location scope."""
    if scope == "anywhere":
        return True
    if event.is_virtual:
        return False
    if scope == "state":
        return event_is_in_state(event, state_code, country_code)
    return event_is_in_country(event, country_code)
