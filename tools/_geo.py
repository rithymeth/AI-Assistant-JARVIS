"""Shared city-name geocoding for weather and worldclock."""

import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
TIMEOUT_SECONDS = 10


def geocode(location: str) -> dict:
    """Raises ValueError if nothing matches."""
    location = (location or "").strip()
    if not location:
        raise ValueError("Need a place name to look up")
    try:
        resp = requests.get(
            GEOCODE_URL,
            params={"name": location, "count": 1},
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Place lookup failed: {exc}") from exc
    results = payload.get("results") or []
    if not results:
        raise ValueError(f"Couldn't find a place called '{location}'")
    return results[0]


def format_place_name(place: dict) -> str:
    return ", ".join(p for p in (place.get("name"), place.get("admin1"), place.get("country")) if p)
