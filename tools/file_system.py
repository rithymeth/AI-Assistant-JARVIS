from pathlib import Path

from config.settings import BASE_DIR

WORKSPACE_DIR = BASE_DIR / "workspace"
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

MAX_READ_CHARS = 50_000
MAX_LIST_ENTRIES = 80


def _clean_path(path: str) -> str:
    if path is None or not str(path).strip():
        raise ValueError("Path is required")
    return str(path).strip()


def _resolve(rel_path: str) -> Path:
    rel_path = _clean_path(rel_path)
    candidate = (WORKSPACE_DIR / rel_path).resolve()
    if not candidate.is_relative_to(WORKSPACE_DIR.resolve()):
        raise ValueError(f"Path '{rel_path}' escapes the workspace sandbox")
    return candidate


def cap_dir_entries(entries: list[dict], limit: int = MAX_LIST_ENTRIES) -> list[dict]:
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = MAX_LIST_ENTRIES
    limit = max(1, min(limit, MAX_LIST_ENTRIES))
    if len(entries) <= limit:
        return entries
    return entries[:limit] + [{"name": f"...and {len(entries) - limit} more", "type": "truncated", "size": None}]


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
    if target == WORKSPACE_DIR.resolve() or target.is_dir():
        raise ValueError(f"'{path}' is a directory, not a file")
    target.parent.mkdir(parents=True, exist_ok=True)
    text = "" if content is None else str(content)
    target.write_text(text, encoding="utf-8")
    return f"Wrote {len(text)} chars to {path}"


def list_dir(path: str = ".") -> list[dict]:
    target = _resolve(path or ".")
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
    return cap_dir_entries(entries)


def read_any_file(path: str) -> str:
    target = Path(_clean_path(path)).expanduser().resolve()
    if not target.is_file():
        raise FileNotFoundError(f"No such file: {path}")
    text = target.read_text(encoding="utf-8", errors="replace")
    if len(text) > MAX_READ_CHARS:
        text = text[:MAX_READ_CHARS] + "\n...[truncated]"
    return text


def write_any_file(path: str, content: str) -> str:
    target = Path(_clean_path(path)).expanduser().resolve()
    if target.is_dir():
        raise ValueError(f"'{path}' is a directory, not a file")
    target.parent.mkdir(parents=True, exist_ok=True)
    text = "" if content is None else str(content)
    target.write_text(text, encoding="utf-8")
    return f"Wrote {len(text)} chars to {target}"


def list_any_dir(path: str) -> list[dict]:
    target = Path(_clean_path(path)).expanduser().resolve()
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
            continue
    return cap_dir_entries(entries)
