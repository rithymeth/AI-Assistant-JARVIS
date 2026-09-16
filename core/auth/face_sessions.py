import secrets
import threading
import time

SESSION_TTL_SECONDS = 12 * 60 * 60

_lock = threading.Lock()
_sessions: dict[str, dict] = {}


def _prune_locked(now: float) -> None:
    dead = [token for token, entry in _sessions.items() if entry["expires_at"] < now]
    for token in dead:
        del _sessions[token]


def create_session(user_id: int) -> str:
    if user_id is None:
        raise ValueError("user_id is required")
    token = secrets.token_urlsafe(32)
    now = time.time()
    with _lock:
        _prune_locked(now)
        _sessions[token] = {"user_id": int(user_id), "expires_at": now + SESSION_TTL_SECONDS}
    return token


def verify_session(token: str, user_id: int) -> bool:
    if not token or user_id is None:
        return False
    now = time.time()
    with _lock:
        entry = _sessions.get(token)
        if entry is None:
            return False
        if entry["expires_at"] < now:
            del _sessions[token]
            return False
        return entry["user_id"] == user_id
