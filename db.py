"""SQLite storage for SESAME state and event history."""

import sqlite3
from datetime import datetime

from config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS lock_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            locked BOOLEAN NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            locked BOOLEAN NOT NULL,
            battery INTEGER,
            is_risky BOOLEAN NOT NULL DEFAULT 0,
            reason TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
    """)
    conn.commit()
    conn.close()


def get_last_state() -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT locked, updated_at FROM lock_state WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else None


def save_state(locked: bool) -> None:
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute(
        """INSERT INTO lock_state (id, locked, updated_at) VALUES (1, ?, ?)
           ON CONFLICT(id) DO UPDATE SET locked=excluded.locked, updated_at=excluded.updated_at""",
        (locked, now),
    )
    conn.commit()
    conn.close()


def save_event(event_type: str, locked: bool, battery: int | None,
               is_risky: bool, reason: str | None) -> None:
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO events (event_type, locked, battery, is_risky, reason, created_at) VALUES (?,?,?,?,?,?)",
        (event_type, locked, battery, is_risky, reason, now),
    )
    conn.commit()
    conn.close()


def count_recent_unlocks(seconds: int) -> int:
    """Count unlock events within the last N seconds."""
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM events WHERE event_type='unlock' AND created_at >= datetime('now', ?)",
        (f"-{seconds} seconds",),
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0
