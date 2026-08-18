from pathlib import Path

from config.settings import BASE_DIR

WORKSPACE_DIR = BASE_DIR / "workspace"
WORKSPACE_DIR.mkdir(exist_ok=True)

MAX_READ_CHARS = 50_000


def _resolve(rel_path: str) -> Path:
    candidate = (WORKSPACE_DIR / rel_path).resolve()
    if not candidate.is_relative_to(WORKSPACE_DIR.resolve()):
        raise ValueError(f"Path '{rel_path}' escapes the workspace sandbox")
    return candidate


def read_file(path: str) -> str:
    target = _resolve(path)
    if not target.is_file():
        raise FileNotFoundError(f"No such file: {path}")
    text = target.read_text(encoding="utf-8", errors="replace")
    if len(text) > MAX_READ_CHARS:
        text = text[:MAX_READ_CHARS] + "\n...[truncated]"
    return text


def write_file(path: str, content: str) -> str:
    target = _resolve(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} chars to {path}"


def list_dir(path: str = ".") -> list[dict]:
    target = _resolve(path)
    if not target.is_dir():
        raise NotADirectoryError(f"No such directory: {path}")
    entries = []
    for entry in sorted(target.iterdir()):
        entries.append(
            {
                "name": entry.name,
                "type": "dir" if entry.is_dir() else "file",
                "size": entry.stat().st_size if entry.is_file() else None,
            }
        )
    return entries


# --- Unrestricted variants: real paths anywhere on the machine, not just
# workspace/. Distinct names and always approval-required (unlike the
# sandboxed versions above, which are auto-exec specifically because the
# workspace sandbox makes them low-risk) — reading/writing arbitrary
# locations (browser profiles, SSH keys, system files) needs a human to
# actually see and confirm it first, every time. ---


def read_any_file(path: str) -> str:
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise FileNotFoundError(f"No such file: {path}")
    text = target.read_text(encoding="utf-8", errors="replace")
    if len(text) > MAX_READ_CHARS:
        text = text[:MAX_READ_CHARS] + "\n...[truncated]"
    return text


def write_any_file(path: str, content: str) -> str:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} chars to {target}"


def list_any_dir(path: str) -> list[dict]:
    target = Path(path).expanduser().resolve()
    if not target.is_dir():
        raise NotADirectoryError(f"No such directory: {path}")
    entries = []
    for entry in sorted(target.iterdir()):
        try:
            entries.append(
                {
                    "name": entry.name,
                    "type": "dir" if entry.is_dir() else "file",
                    "size": entry.stat().st_size if entry.is_file() else None,
                }
            )
        except OSError:
            continue  # unreadable entry (permissions, broken link) — skip rather than fail the whole listing
    return entries
