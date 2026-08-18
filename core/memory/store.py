import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from config.settings import ACCESS_CODE, DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    code_hash TEXT NOT NULL,
    code_salt TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'standard')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS face_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    embedding BLOB NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_face_embeddings_user ON face_embeddings(user_id);

-- Standing behavioral instructions/corrections ("always keep replies short",
-- "call me boss", a correction after Javi got something wrong) — distinct
-- from core/memory/knowledge.py's javi_knowledge (looked-up FACTS, recalled
-- by semantic similarity to the current message). Preferences are few,
-- durable, and meant to apply UNCONDITIONALLY, so they're injected into
-- every conversation's context in full rather than semantically retrieved.
CREATE TABLE IF NOT EXISTS preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Global (not per-session/per-user) — this is a single-household assistant,
-- and "remind me" naturally means "tell whoever's listening when it's
-- due," not "only the browser tab that set it." due_at/created_at are UTC
-- ISO strings, matching every other timestamp in this file. delivered is
-- set once /reminders/due has actually returned it, so a reminder fires
-- exactly once even if multiple clients are polling concurrently (see
-- list_due_undelivered_reminders below, which marks-and-returns atomically).
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    due_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    delivered INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(due_at) WHERE delivered = 0;

-- Persistent named lists (shopping list, to-do list, whatever the user
-- calls it) — global like reminders/preferences above, for the same
-- single-household reason. Distinct from preferences (behavioral
-- instructions Javi follows) and reminders (time-triggered) — this is
-- just plain content the user wants to keep track of, recalled only when
-- asked, never injected unconditionally.
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    list_name TEXT NOT NULL DEFAULT 'general',
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_notes_list ON notes(list_name);
"""


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _connect() as conn:
        conn.executescript(_SCHEMA)
    _ensure_bootstrap_admin()


def _ensure_bootstrap_admin():
    """First boot after adding multi-user support: if the users table is
    empty, create a bootstrap admin whose code is the existing single-user
    ACCESS_CODE (persisted in .access_code / .env), so a phone that already
    has that code saved doesn't get locked out by this upgrade."""
    from core.auth.users import hash_new_code

    with _connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count:
            return
        code_hash, code_salt = hash_new_code(ACCESS_CODE)
        conn.execute(
            "INSERT INTO users (username, code_hash, code_salt, role, created_at) "
            "VALUES ('admin', ?, ?, 'admin', ?)",
            (code_hash, code_salt, datetime.now(timezone.utc).isoformat()),
        )


def add_message(session_id: str, role: str, content: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, datetime.now(timezone.utc).isoformat()),
        )


def get_history(session_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in rows]


def create_user(username: str, code_hash: str, code_salt: str, role: str) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, code_hash, code_salt, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, code_hash, code_salt, role, datetime.now(timezone.utc).isoformat()),
        )
        return cur.lastrowid


def list_users() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, username, role, created_at FROM users ORDER BY id ASC"
        ).fetchall()
    return [{"id": r[0], "username": r[1], "role": r[2], "created_at": r[3]} for r in rows]


def add_face_embedding(user_id: int, embedding: bytes) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO face_embeddings (user_id, embedding, created_at) VALUES (?, ?, ?)",
            (user_id, embedding, datetime.now(timezone.utc).isoformat()),
        )
        return cur.lastrowid


def get_face_embeddings(user_id: int) -> list[bytes]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT embedding FROM face_embeddings WHERE user_id = ?", (user_id,)
        ).fetchall()
    return [r[0] for r in rows]


def has_face_embeddings(user_id: int) -> bool:
    with _connect() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM face_embeddings WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
    return count > 0


def find_user_by_code(code: str) -> dict | None:
    """Linear scan verifying `code` against every stored hash — codes are
    salted per-user, so there's no indexable lookup by code value. Fine at
    the user counts this is meant for (a handful of household/team accounts,
    not a multi-tenant SaaS)."""
    from core.auth.users import verify_code

    if not code:
        return None
    with _connect() as conn:
        rows = conn.execute("SELECT id, username, code_hash, code_salt, role FROM users").fetchall()
    for user_id, username, code_hash, code_salt, role in rows:
        if verify_code(code, code_salt, code_hash):
            return {"id": user_id, "username": username, "role": role}
    return None


def add_preference(text: str) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO preferences (text, created_at) VALUES (?, ?)",
            (text, datetime.now(timezone.utc).isoformat()),
        )
        return cur.lastrowid


def list_preferences() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, text, created_at FROM preferences ORDER BY id ASC"
        ).fetchall()
    return [{"id": r[0], "text": r[1], "created_at": r[2]} for r in rows]


def delete_preference(pref_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM preferences WHERE id = ?", (pref_id,))
        return cur.rowcount > 0


def create_reminder(text: str, due_at: str) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO reminders (text, due_at, created_at, delivered) VALUES (?, ?, ?, 0)",
            (text, due_at, datetime.now(timezone.utc).isoformat()),
        )
        return cur.lastrowid


def list_pending_reminders() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, text, due_at, created_at FROM reminders WHERE delivered = 0 ORDER BY due_at ASC"
        ).fetchall()
    return [{"id": r[0], "text": r[1], "due_at": r[2], "created_at": r[3]} for r in rows]


def list_due_undelivered_reminders() -> list[dict]:
    """Atomically marks-and-returns every undelivered reminder whose due_at
    has passed, within one connection/transaction — so a reminder fires
    exactly once even if it's polled from more than one client around the
    same moment, rather than a plain SELECT-then-UPDATE racing across two
    separate connections."""
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, text, due_at, created_at FROM reminders WHERE delivered = 0 AND due_at <= ? ORDER BY due_at ASC",
            (now,),
        ).fetchall()
        if rows:
            ids = [r[0] for r in rows]
            conn.execute(
                f"UPDATE reminders SET delivered = 1 WHERE id IN ({','.join('?' * len(ids))})", ids
            )
    return [{"id": r[0], "text": r[1], "due_at": r[2], "created_at": r[3]} for r in rows]


def cancel_reminder(id_or_text: str) -> int:
    text = str(id_or_text).strip()
    with _connect() as conn:
        if text.isdigit():
            cur = conn.execute("DELETE FROM reminders WHERE id = ? AND delivered = 0", (int(text),))
        else:
            cur = conn.execute(
                "DELETE FROM reminders WHERE delivered = 0 AND text LIKE ?", (f"%{text}%",)
            )
        return cur.rowcount


def add_note(text: str, list_name: str = "general") -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO notes (list_name, text, created_at) VALUES (?, ?, ?)",
            (list_name, text, datetime.now(timezone.utc).isoformat()),
        )
        return cur.lastrowid


def list_notes(list_name: str | None = None) -> list[dict]:
    with _connect() as conn:
        if list_name is None:
            rows = conn.execute(
                "SELECT id, list_name, text, created_at FROM notes ORDER BY list_name ASC, id ASC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, list_name, text, created_at FROM notes WHERE list_name = ? ORDER BY id ASC",
                (list_name,),
            ).fetchall()
    return [{"id": r[0], "list_name": r[1], "text": r[2], "created_at": r[3]} for r in rows]


def remove_note(id_or_text: str, list_name: str | None = None) -> int:
    text = str(id_or_text).strip()
    with _connect() as conn:
        if text.isdigit():
            cur = conn.execute("DELETE FROM notes WHERE id = ?", (int(text),))
        elif list_name is None:
            cur = conn.execute("DELETE FROM notes WHERE text LIKE ?", (f"%{text}%",))
        else:
            cur = conn.execute(
                "DELETE FROM notes WHERE list_name = ? AND text LIKE ?", (list_name, f"%{text}%")
            )
        return cur.rowcount


def clear_list(list_name: str) -> int:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM notes WHERE list_name = ?", (list_name,))
        return cur.rowcount
