from datetime import datetime
from zoneinfo import ZoneInfo

from tools._geo import format_place_name, geocode


def get_time_in(location: str) -> dict:
    """The model has no reliable live clock/DST awareness, and current
    time-in-a-place isn't something to guess at — geocode the place to its
    real IANA timezone (Open-Meteo's geocoding response includes it
    directly, no separate timezone lookup needed) and compute the actual
    DST-aware local time via Python's stdlib zoneinfo."""
    if not location or not location.strip():
        raise ValueError("Need a location to look up the time for")

    place = geocode(location.strip())
    tz_name = place.get("timezone")
    if not tz_name:
        raise ValueError(f"Found '{location}' but it has no known timezone")

    now = datetime.now(ZoneInfo(tz_name))
    return {
        "location": format_place_name(place),
        "timezone": tz_name,
        # %#I not %-I — Windows' strftime no-leading-zero flag differs from
        # Linux/macOS (a real bug caught and fixed once already this session).
        "time": now.strftime("%#I:%M %p"),
        "date": now.strftime("%A, %B %#d"),
        "utc_offset": now.strftime("%z"),
    }
