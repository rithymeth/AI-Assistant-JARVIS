import secrets
import threading
import time

# Session-scoped per the plan's default: verify once, get a token good for
# ~12h, rather than a face check on every single gated request.
SESSION_TTL_SECONDS = 12 * 60 * 60

# In-memory, ephemeral by design — lost on server restart, same tradeoff as
# core/brain/agent.py's PENDING_ACTIONS. Re-verifying after a restart is a
# minor inconvenience, not a bug.
_lock = threading.Lock()
_sessions: dict[str, dict] = {}  # token -> {"user_id": int, "expires_at": float}


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with _lock:
        _sessions[token] = {"user_id": user_id, "expires_at": time.time() + SESSION_TTL_SECONDS}
    return token


def verify_session(token: str, user_id: int) -> bool:
    """True only if `token` is a valid, unexpired face-session minted for
    exactly this user_id — a token issued to one user must never authorize
    a different one, even if somehow replayed."""
    if not token:
        return False
    with _lock:
        entry = _sessions.get(token)
        if entry is None:
            return False
        if entry["expires_at"] < time.time():
            del _sessions[token]
            return False
        return entry["user_id"] == user_id
