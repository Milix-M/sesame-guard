"""Tests for db module."""

import os
import tempfile
from datetime import datetime, timezone, timedelta

import pytest

from db import (
    init_db, get_conn,
    get_last_state, save_state,
    save_event, count_recent_unlocks,
    get_events_since, get_last_unlock_time,
    get_last_alert_time, save_alert,
)

JST = timezone(timedelta(hours=9))


@pytest.fixture(autouse=True)
def tmp_db(monkeypatch):
    """Use a temp DB for each test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr("db.DB_PATH", path)
    init_db()
    yield path
    os.unlink(path)


class TestLockState:
    def test_initial_state_is_none(self):
        assert get_last_state() is None

    def test_save_and_get(self):
        save_state(True)
        state = get_last_state()
        assert state["locked"] is True

    def test_update_state(self):
        save_state(True)
        save_state(False)
        state = get_last_state()
        assert state["locked"] is False


class TestEvents:
    def test_save_and_count_recent_unlocks(self):
        save_event("unlock", False, 100, False, None)
        save_event("unlock", False, 100, False, None)
        assert count_recent_unlocks(300) == 2

    def test_count_excludes_old_events(self):
        save_event("unlock", False, 100, False, None)

        # Manually insert an old event
        conn = get_conn()
        old_time = (datetime.now(JST) - timedelta(hours=1)).isoformat()
        conn.execute(
            "INSERT INTO events (event_type, locked, battery, is_risky, reason, created_at, created_at_jst) VALUES (?,?,?,?,?,?,?)",
            ("unlock", False, 100, False, None, old_time, old_time),
        )
        conn.commit()
        conn.close()

        assert count_recent_unlocks(300) == 1  # only the recent one


class TestEventsSince:
    def test_get_events_filters_type(self):
        save_event("unlock", False, 100, False, None)
        save_event("status_change", True, 100, False, None)

        unlocks = get_events_since(days=1, event_type="unlock")
        assert len(unlocks) == 1
        assert unlocks[0]["hour"] is not None

    def test_get_events_respects_days(self):
        save_event("unlock", False, 100, False, None)

        conn = get_conn()
        old_time = (datetime.now(JST) - timedelta(days=31)).isoformat()
        conn.execute(
            "INSERT INTO events (event_type, locked, battery, is_risky, reason, created_at, created_at_jst) VALUES (?,?,?,?,?,?,?)",
            ("unlock", False, 100, False, None, old_time, old_time),
        )
        conn.commit()
        conn.close()

        events = get_events_since(days=30, event_type="unlock")
        assert len(events) == 1


class TestLastUnlockTime:
    def test_no_unlocks(self):
        assert get_last_unlock_time() is None

    def test_returns_latest(self):
        save_event("unlock", False, 100, False, None)
        result = get_last_unlock_time()
        assert result is not None
        assert isinstance(result, datetime)


class TestAlertLog:
    def test_no_alerts(self):
        assert get_last_alert_time() is None

    def test_save_and_get(self):
        save_alert(["理由1", "理由2"])
        result = get_last_alert_time()
        assert result is not None
