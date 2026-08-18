from core.memory.store import add_note as _add_note
from core.memory.store import clear_list as _clear_list
from core.memory.store import list_notes as _list_notes
from core.memory.store import remove_note as _remove_note

DEFAULT_LIST = "general"


def add_note(text: str, list_name: str = DEFAULT_LIST) -> str:
    if not text or not text.strip():
        raise ValueError("Note text can't be empty")
    list_name = (list_name or DEFAULT_LIST).strip().lower()
    _add_note(text.strip(), list_name)
    return f"Added to your {list_name} list: {text.strip()}"


def list_notes(list_name: str | None = None) -> list[dict]:
    return _list_notes(list_name.strip().lower() if list_name else None)


def remove_note(text_or_id: str, list_name: str | None = None) -> str:
    """Same substring-or-id UX as forget_preference/cancel_reminder. If
    list_name is omitted, matches by text across every list — fine for a
    single household's small lists, where the same item rarely appears on
    two different lists at once."""
    normalized_list = list_name.strip().lower() if list_name else None
    count = _remove_note(text_or_id, normalized_list)
    if count == 0:
        return f"No note matches '{text_or_id}'" + (f" on your {normalized_list} list" if normalized_list else "")
    return f"Removed {count} item(s) matching '{text_or_id}'"


def clear_list(list_name: str) -> str:
    if not list_name or not list_name.strip():
        raise ValueError("list_name can't be empty")
    normalized = list_name.strip().lower()
    count = _clear_list(normalized)
    return f"Cleared your {normalized} list ({count} item(s) removed)"
