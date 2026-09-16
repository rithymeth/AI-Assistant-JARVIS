from datetime import datetime
from zoneinfo import ZoneInfo

from tools._geo import format_place_name, geocode


def format_local_clock(now: datetime) -> dict:
    """Portable 12-hour clock strings. Avoid Windows-only %#I / %#d flags."""
    hour = now.strftime("%I").lstrip("0") or "12"
    return {
        "time": f"{hour}:{now.strftime('%M %p')}",
        "date": f"{now.strftime('%A, %B')} {now.day}",
        "utc_offset": now.strftime("%z"),
    }


def get_time_in(location: str | None = None) -> dict:
    """The model has no reliable live clock/DST awareness.

    Omit location to use this machine's local timezone.
    """
    if not location or not str(location).strip():
        now = datetime.now().astimezone()
        tz_name = now.tzname() or str(now.tzinfo)
        payload = format_local_clock(now)
        payload.update({"location": "this machine", "timezone": tz_name})
        return payload

    place = geocode(location.strip())
    tz_name = place.get("timezone")
    if not tz_name:
        raise ValueError(f"Found '{location}' but it has no known timezone")

    now = datetime.now(ZoneInfo(tz_name))
    payload = format_local_clock(now)
    payload.update({"location": format_place_name(place), "timezone": tz_name})
    return payload
