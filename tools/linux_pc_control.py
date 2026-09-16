"""Best-effort desktop control on Linux/macOS. Windows stays on windows_pc_control."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import webbrowser
from urllib.parse import urlparse


def _looks_like_url(name: str) -> bool:
    parsed = urlparse(name)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def open_app(name: str) -> str:
    name = (name or "").strip()
    if not name:
        raise ValueError("Nothing to open")
    if _looks_like_url(name):
        webbrowser.open(name)
        return f"Opened {name} in the browser"

    opener = shutil.which("xdg-open") or shutil.which("open")
    if opener:
        subprocess.Popen([opener, name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Launched '{name}'"
    webbrowser.open(name)
    return f"Tried to open '{name}'"


def _wmctrl_list() -> list[tuple[str, str]]:
    wmctrl = shutil.which("wmctrl")
    if not wmctrl:
        return []
    result = subprocess.run([wmctrl, "-l"], capture_output=True, text=True, timeout=5)
    rows = []
    for line in result.stdout.splitlines():
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        rows.append((parts[0], parts[3]))
    return rows


def list_windows() -> list[str]:
    titles = [title for _, title in _wmctrl_list() if title.strip()]
    if titles:
        return titles
    return ["Window listing needs wmctrl on this OS (`sudo apt install wmctrl`)"]


def _matching(title_substring: str) -> list[tuple[str, str]]:
    needle = title_substring.lower()
    return [(wid, title) for wid, title in _wmctrl_list() if needle in title.lower()]


def close_app(title_substring: str) -> str:
    title_substring = (title_substring or "").strip()
    if not title_substring:
        raise ValueError("Need a window title to close")
    matches = _matching(title_substring)
    if not matches:
        return f"No open window matches '{title_substring}'"
    wmctrl = shutil.which("wmctrl")
    for wid, _title in matches:
        subprocess.run([wmctrl, "-ic", wid], capture_output=True, text=True, timeout=5)
    return f"Closed {len(matches)} window(s) matching '{title_substring}'"


def focus_window(title_substring: str) -> str:
    title_substring = (title_substring or "").strip()
    if not title_substring:
        raise ValueError("Need a window title to focus")
    matches = _matching(title_substring)
    if not matches:
        return f"No open window matches '{title_substring}'"
    wmctrl = shutil.which("wmctrl")
    wid, title = matches[0]
    subprocess.run([wmctrl, "-ia", wid], capture_output=True, text=True, timeout=5)
    return f"Focused '{title}'"


def screenshot_cli_candidates(path: str) -> list[list[str]]:
    return [
        ["grim", path],
        ["gnome-screenshot", "-f", path],
        ["scrot", "--overwrite", path],
        ["screencapture", "-x", path],
        ["import", "-window", "root", path],
    ]


def take_screenshot() -> str:
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    errors: list[str] = []

    try:
        import mss

        with mss.mss() as sct:
            sct.shot(output=path)
        if os.path.getsize(path) > 0:
            return path
    except Exception as exc:
        errors.append(f"mss: {exc}")

    try:
        from PIL import ImageGrab

        ImageGrab.grab().save(path)
        if os.path.getsize(path) > 0:
            return path
    except Exception as exc:
        errors.append(f"ImageGrab: {exc}")

    for args in screenshot_cli_candidates(path):
        binary = shutil.which(args[0])
        if not binary:
            continue
        cmd = [binary, *args[1:]]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if result.returncode == 0 and os.path.exists(path) and os.path.getsize(path) > 0:
            return path
        errors.append(f"{args[0]}: {result.stderr.strip() or result.returncode}")

    if os.path.exists(path):
        os.remove(path)
    raise RuntimeError(
        "Screenshot failed. Install grim, gnome-screenshot, scrot, or ImageMagick. "
        + "; ".join(errors[-3:])
    )
