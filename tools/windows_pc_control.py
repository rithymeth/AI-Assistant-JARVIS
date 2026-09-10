import os
import re
import tempfile

import pygetwindow as gw
import pythoncom
from PIL import ImageGrab

_UNSAFE_CHARS = re.compile(r"[&|;\n\r<>^]")


def open_app(name: str) -> str:
    if _UNSAFE_CHARS.search(name):
        raise ValueError(f"Rejected app name with unsafe characters: {name!r}")
    try:
        pythoncom.CoInitialize()
    except pythoncom.com_error:
        pass
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

