"""Shared city-name geocoding, used by both weather.py and worldclock.py —
one free, no-API-key service (Open-Meteo) doing double duty rather than
each tool rolling its own lookup. Leading underscore: not itself a tool,
no schema/handler registration in registry.py."""

import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
TIMEOUT_SECONDS = 10


def geocode(location: str) -> dict:
    """Raises ValueError if nothing matches — callers don't need to
    separately check for an empty result."""
    resp = requests.get(GEOCODE_URL, params={"name": location, "count": 1}, timeout=TIMEOUT_SECONDS)
    resp.raise_for_status()
    results = resp.json().get("results") or []
    if not results:
        raise ValueError(f"Couldn't find a place called '{location}'")
    return results[0]


def format_place_name(place: dict) -> str:
    return ", ".join(p for p in (place.get("name"), place.get("admin1"), place.get("country")) if p)
