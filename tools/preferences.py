from core.memory.store import add_preference, delete_preference, list_preferences


def remember_preference(text: str) -> str:
    pref_id = add_preference(text.strip())
    return f"Remembered (#{pref_id}): {text.strip()}"


def recall_preferences() -> list[dict]:
    return list_preferences()


def forget_preference(text_or_id: str) -> str:
    """Accepts either a numeric preference id, or a substring to match
    against stored preference text (case-insensitive) — mirrors
    kill_process's PID-or-name-substring UX so the user doesn't need to
    know an internal id to say "forget that I said X"."""
    text = str(text_or_id).strip()
    prefs = list_preferences()

    if text.isdigit():
        matches = [p for p in prefs if p["id"] == int(text)]
    else:
        needle = text.lower()
        matches = [p for p in prefs if needle in p["text"].lower()]

    if not matches:
        return f"No stored preference matches '{text_or_id}'"

    for p in matches:
        delete_preference(p["id"])
    return f"Forgot {len(matches)} preference(s): {[p['text'] for p in matches]}"
