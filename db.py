"""SQLite storage for SESAME state and event history."""

import sqlite3
from datetime import datetime, timezone, timedelta

from config import DB_PATH

JST = timezone(timedelta(hours=9))


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
            created_at TEXT NOT NULL,
            created_at_jst TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS alert_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reasons TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_risky ON events(is_risky);
        CREATE INDEX IF NOT EXISTS idx_alert_log_created ON alert_log(created_at);
    """)
    conn.commit()
    conn.close()


def _now_iso() -> str:
    return datetime.now(JST).isoformat()


def get_last_state() -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT locked, updated_at FROM lock_state WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else None


def save_state(locked: bool) -> None:
    now = _now_iso()
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
    now = _now_iso()
    conn = get_conn()
    conn.execute(
        "INSERT INTO events (event_type, locked, battery, is_risky, reason, created_at, created_at_jst) VALUES (?,?,?,?,?,?,?)",
        (event_type, locked, battery, is_risky, reason, now, now),
    )
    conn.commit()
    conn.close()


def count_recent_unlocks(seconds: int) -> int:
    """Count unlock events within the last N seconds (JST)."""
    cutoff = (datetime.now(JST) - timedelta(seconds=seconds)).isoformat()
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM events WHERE event_type='unlock' AND created_at_jst >= ?",
        (cutoff,),
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


def get_events_since(days: int, event_type: str | None = None) -> list[dict]:
    """Get events from the past N days (JST). Returns list with 'hour' field."""
    cutoff = (datetime.now(JST) - timedelta(days=days)).isoformat()
    conn = get_conn()
    query = "SELECT * FROM events WHERE created_at_jst >= ?"
    params: list = [cutoff]
    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)
    query += " ORDER BY created_at_jst ASC"
    rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    conn.close()

    # Extract hour from created_at_jst
    for r in rows:
        try:
            dt = datetime.fromisoformat(r["created_at_jst"])
            r["hour"] = dt.hour
        except (ValueError, TypeError):
            r["hour"] = 0

    return rows


def get_last_unlock_time() -> datetime | None:
    """Get the most recent unlock event time (JST)."""
    conn = get_conn()
    row = conn.execute(
        "SELECT created_at_jst FROM events WHERE event_type='unlock' ORDER BY created_at_jst DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row is None:
        return None
    try:
        return datetime.fromisoformat(row["created_at_jst"])
    except ValueError:
        return None


def get_last_alert_time() -> datetime | None:
    """Get the most recent alert time (JST)."""
    conn = get_conn()
    row = conn.execute(
        "SELECT created_at FROM alert_log ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row is None:
        return None
    try:
        return datetime.fromisoformat(row["created_at"])
    except ValueError:
        return None


def save_alert(reasons: list[str]) -> None:
    """Log an alert that was sent."""
    now = _now_iso()
    conn = get_conn()
    conn.execute(
        "INSERT INTO alert_log (reasons, created_at) VALUES (?, ?)",
        ("\n".join(reasons), now),
    )
    conn.commit()
    conn.close()
