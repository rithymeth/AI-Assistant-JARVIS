from datetime import datetime, timedelta, timezone

from core.memory.store import cancel_reminder as _cancel_reminder
from core.memory.store import create_reminder, list_pending_reminders
from tools.worldclock import format_local_clock

# Small local models are unreliable at absolute date/time arithmetic —
# the tool takes a relative delay or a bare clock time and does the math here.
_AT_TIME_FORMATS = ("%H:%M", "%I:%M %p", "%I:%M%p", "%I %p")


def _resolve_at_time(at_time: str) -> datetime:
    """HH:MM or 3:00 PM -> next future occurrence of that clock time."""
    text = at_time.strip()
    parsed_time = None
    for fmt in _AT_TIME_FORMATS:
        try:
            parsed_time = datetime.strptime(text, fmt).time()
            break
        except ValueError:
            continue
    if parsed_time is None:
        raise ValueError(f"Couldn't understand the time '{at_time}' — try e.g. '15:00' or '3:00 PM'")

    now = datetime.now().astimezone()
    candidate = now.replace(hour=parsed_time.hour, minute=parsed_time.minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def set_reminder(text: str, delay_minutes: int | None = None, at_time: str | None = None) -> str:
    if not text or not text.strip():
        raise ValueError("Reminder text can't be empty")
    if (delay_minutes is None) == (at_time is None):
        raise ValueError("Provide exactly one of delay_minutes or at_time")

    if delay_minutes is not None:
        due = datetime.now(timezone.utc) + timedelta(minutes=max(0, int(delay_minutes)))
    else:
        due = _resolve_at_time(at_time).astimezone(timezone.utc)

    create_reminder(text.strip(), due.isoformat())
    clock = format_local_clock(due.astimezone())
    return f"Reminder set for {clock['time']}: {text.strip()}"


def list_reminders() -> list[dict]:
    return list_pending_reminders()


def cancel_reminder(text_or_id: str) -> str:
    count = _cancel_reminder(text_or_id)
    if count == 0:
        return f"No pending reminder matches '{text_or_id}'"
    return f"Cancelled {count} reminder(s)"
