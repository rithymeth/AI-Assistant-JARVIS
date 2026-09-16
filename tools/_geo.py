"""Shared city-name geocoding for weather and worldclock."""

import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
TIMEOUT_SECONDS = 10


def format_place_name(place: dict | None) -> str:
    if not place:
        return "unknown place"
    return ", ".join(p for p in (place.get("name"), place.get("admin1"), place.get("country")) if p) or "unknown place"


def geocode(location: str) -> dict:
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
    except ValueError as exc:
        raise RuntimeError(f"Place lookup returned invalid JSON: {exc}") from exc
    results = payload.get("results") if isinstance(payload, dict) else None
    if not results:
        raise ValueError(f"Couldn't find a place called '{location}'")
    place = results[0]
    if not isinstance(place, dict) or not place.get("name"):
        raise ValueError(f"Couldn't find a place called '{location}'")
    return place
