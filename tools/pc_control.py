import os
import re
import tempfile

import pygetwindow as gw
import pythoncom
from PIL import ImageGrab

# open_app runs WITHOUT approval, so even though the realistic threat here is
# an unreliable local model rather than a malicious attacker, the name is
# still rejected outright if it contains shell metacharacters rather than
# trying to escape them — defense in depth for an auto-executing tool. Not
# strictly needed for shell-injection purposes since os.startfile below never
# goes through a shell (it calls ShellExecute directly), but kept as a cheap
# extra guard against obviously-malformed input.
_UNSAFE_CHARS = re.compile(r'[&|;\n\r<>^]')


def open_app(name: str) -> str:
    if _UNSAFE_CHARS.search(name):
        raise ValueError(f"Rejected app name with unsafe characters: {name!r}")
    # os.startfile's ShellExecute is COM-based, and a thread that has never
    # initialized a COM apartment can silently drop its first call — the
    # documented cause of "the very first open_app after a fresh server
    # start sometimes does nothing" (FastAPI runs sync route handlers on
    # threadpool worker threads, and a freshly spun-up worker has never
    # touched COM). CoInitialize() is idempotent per-thread in the normal
    # case (a second call on an already-STA-initialized thread is a
    # harmless no-op), so calling it unconditionally here is cheap
    # insurance on every call, not just special-cased for the first one.
    # Only raises if this thread was already initialized with an
    # incompatible apartment model, which nothing else in this codebase does.
    try:
        pythoncom.CoInitialize()
    except pythoncom.com_error:
        pass
    # os.startfile uses the same ShellExecute mechanism as double-clicking in
    # Explorer — reliably handles apps, files, folders, and URLs alike.
    # (An earlier `cmd /c start "" name` implementation silently failed to
    # open folders on this machine despite reporting success — verified via
    # direct testing — so this is a real fix, not just a style change.)
    os.startfile(name)
    return f"Launched '{name}'"


def _matching_windows(title_substring: str):
    needle = title_substring.lower()
    return [w for w in gw.getAllWindows() if w.title.strip() and needle in w.title.lower()]


def close_app(title_substring: str) -> str:
    matches = _matching_windows(title_substring)
    if not matches:
        return f"No open window matches '{title_substring}'"
    for w in matches:
        w.close()
    return f"Closed {len(matches)} window(s) matching '{title_substring}'"


def focus_window(title_substring: str) -> str:
    matches = _matching_windows(title_substring)
    if not matches:
        return f"No open window matches '{title_substring}'"
    matches[0].activate()
    return f"Focused '{matches[0].title}'"


def list_windows() -> list[str]:
    return [w.title for w in gw.getAllWindows() if w.title.strip()]


def take_screenshot() -> str:
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    ImageGrab.grab().save(path)
    return path
