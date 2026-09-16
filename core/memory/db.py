"""Shared SQLite connection defaults for Javi's local store."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from config.settings import DB_PATH

CONNECT_TIMEOUT_SECONDS = 10


@contextmanager
def connect(path: str | None = None):
    conn = sqlite3.connect(path or DB_PATH, timeout=CONNECT_TIMEOUT_SECONDS)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
