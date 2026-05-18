"""Source router — maps founder intent to scrapable URL patterns."""
from __future__ import annotations
from typing import Dict, List, Optional
from app.models.schemas import IntentResult

# Registry: each source has search URL template + human name
SOURCES: Dict[str, Dict] = {
    "medc": {
        "name": "Michigan Economic Development Corporation",
        "base_url": "https://www.michiganbusiness.org",
        "search_template": "https://www.michiganbusiness.org/ofme/projects-and-programs/",
        "type_match": {"grant", "accelerator", "event"},
        "region": "Michigan",
    },
    "techstars_detroit": {
        "name": "Techstars Detroit",
        "base_url": "https://www.techstars.com/accelerators/detroit",
        "search_template": "https://www.techstars.com/accelerators/",
        "type_match": {"accelerator"},
        "region": "Michigan",
    },
    "pitchmi": {
        "name": "PitchMI Startup Competition",
        "base_url": "https://msufoundation.org/pitchmi",
        "type_match": {"pitch_competition"},
        "region": "Michigan",
    },
    "hatch_detroit": {
        "name": "Hatch Detroit Contest",
        "base_url": "https://hatchdetroit.com",
        "type_match": {"grant"},
        "region": "Michigan",
    },
    "startdtw": {
        "name": "Start Detroit Events",
        "base_url": "https://startdtw.com",
        "type_match": {"event", "coworking"},
        "region": "Michigan",
    },
    "bullish_chicago": {
        "name": "Bullish on Chicago",
        "base_url": "https://bullishonchicago.com",
        "type_match": {"grant", "accelerator", "event", "coworking"},
        "region": "Illinois",
    },
    "ohio_startup": {
        "name": "Ohio Startup Network",
        "base_url": "https://luma.io",
        "search_template": "https://lu.ma/ohio-startup",
        "type_match": {"event", "networking"},
        "region": "Ohio",
    },
    "eventbrite": {
        "name": "Eventbrite",
        "base_url": "https://www.eventbrite.com",
        "search_template": "https://www.eventbrite.com/d/{state}/{query}/",
        "type_match": {"event"},
        "region": None,  # config-driven
    },
    "meetup": {
        "name": "Meetup",
        "base_url": "https://www.meetup.com",
        "search_template": "https://www.meetup.com/find/?keywords={query}&location={location}",
        "type_match": {"event", "networking"},
        "region": None,
    },
    "google_search": {
        "name": "Google Search",
        "base_url": "https://www.google.com",
        "type_match": set(),  # catch-all
        "region": None,
    },
}


def select_sources(intent: IntentResult, max_sources: int = 5) -> List[str]:
    """Return list of source keys to query for this intent."""
    selected: List[str] = []
    state = (intent.state or "").lower()
    need_type = intent.need_type or ""

    # 1. State-specific sources
    for key, src in SOURCES.items():
        if src["region"] and src["region"].lower() == state:
            if not need_type or not src["type_match"] or need_type in src["type_match"]:
                selected.append(key)

    # 2. Type-specific sources that match
    for key, src in SOURCES.items():
        if key in selected:
            continue
        if need_type and src["type_match"] and need_type in src["type_match"]:
            selected.append(key)

    # 3. Fallback: always try eventbrite for events, meetup for networking
    if intent.need_type == "event" and "eventbrite" not in selected:
        selected.append("eventbrite")
    if intent.need_type in {"event", "networking", "coworking"} and "meetup" not in selected:
        selected.append("meetup")

    # 4. Catch-all: Google search for everything else
    if len(selected) < 2:
        selected.append("google_search")

    return selected[:max_sources]


def build_search_url(source_key: str, intent: IntentResult) -> Optional[str]:
    """Build a search URL for a source given intent."""
    src = SOURCES.get(source_key)
    if not src:
        return None
    template = src.get("search_template")
    if not template:
        return src["base_url"]

    location = intent.location or intent.state or ""
    query = " ".join(filter(None, [intent.need_type, intent.stage] + (intent.keywords or [])))

    return template.format(
        location=location,
        state=(intent.state or "").lower().replace(" ", "-"),
        query=query.replace(" ", "+"),
    )
