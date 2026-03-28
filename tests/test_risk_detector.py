"""Tests for risk_detector module."""

import math
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest

from risk_detector import (
    _check_nighttime,
    _check_rapid_unlock,
    _check_anomaly,
    check_unlock_timeout,
    is_cooled_down,
    evaluate_risk,
    JST,
)


# ─── Nighttime ───

class TestCheckNighttime:
    @patch("risk_detector._now_jst")
    def test_weekday_night_risky(self, mock_now):
        """Weekday 2:00 AM → risky."""
        mock_now.return_value = datetime(2026, 3, 27, 2, 30, tzinfo=JST)  # Friday
        risky, reason = _check_nighttime()
        assert risky is True
        assert "平日" in reason

    @patch("risk_detector._now_jst")
    def test_weekday_3am_risky(self, mock_now):
        """Weekday 3:00 AM → risky."""
        mock_now.return_value = datetime(2026, 3, 27, 3, 0, tzinfo=JST)  # Friday
        risky, reason = _check_nighttime()
        assert risky is True

    @patch("risk_detector._now_jst")
    def test_weekday_daytime_safe(self, mock_now):
        """Weekday 14:00 → safe."""
        mock_now.return_value = datetime(2026, 3, 27, 14, 0, tzinfo=JST)  # Friday
        risky, reason = _check_nighttime()
        assert risky is False

    @patch("risk_detector._now_jst")
    def test_saturday_2am_safe(self, mock_now):
        """Saturday 2:00 AM → safe (weekend starts at 3:00)."""
        mock_now.return_value = datetime(2026, 3, 28, 2, 30, tzinfo=JST)  # Saturday
        risky, reason = _check_nighttime()
        assert risky is False

    @patch("risk_detector._now_jst")
    def test_saturday_3am_risky(self, mock_now):
        """Saturday 3:00 AM → risky (weekend range)."""
        mock_now.return_value = datetime(2026, 3, 28, 3, 30, tzinfo=JST)  # Saturday
        risky, reason = _check_nighttime()
        assert risky is True
        assert "休日" in reason

    @patch("risk_detector._now_jst")
    def test_sunday_4am_risky(self, mock_now):
        """Sunday 4:00 AM → risky."""
        mock_now.return_value = datetime(2026, 3, 29, 4, 0, tzinfo=JST)  # Sunday
        risky, reason = _check_nighttime()
        assert risky is True
        assert "休日" in reason

    @patch("risk_detector._now_jst")
    def test_boundary_5am_safe(self, mock_now):
        """5:00 AM → safe (exclusive end)."""
        mock_now.return_value = datetime(2026, 3, 27, 5, 0, tzinfo=JST)  # Friday
        risky, reason = _check_nighttime()
        assert risky is False


# ─── Rapid unlock ───

class TestCheckRapidUnlock:
    @patch("risk_detector.count_recent_unlocks")
    def test_rapid_unlock_risky(self, mock_count):
        mock_count.return_value = 3
        risky, reason = _check_rapid_unlock()
        assert risky is True
        assert "3回" in reason

    @patch("risk_detector.count_recent_unlocks")
    def test_rapid_unlock_safe(self, mock_count):
        mock_count.return_value = 2
        risky, reason = _check_rapid_unlock()
        assert risky is False


# ─── Anomaly detection ───

class TestCheckAnomaly:
    @patch("risk_detector.get_events_since")
    def test_not_enough_data(self, mock_events):
        """Less than 10 events → skip anomaly check."""
        mock_events.return_value = [{"hour": 18}] * 5
        risky, reason = _check_anomaly()
        assert risky is False

    @patch("risk_detector._now_jst")
    @patch("risk_detector.get_events_since")
    def test_zero_hit_anomaly(self, mock_events, mock_now):
        """Current hour has zero historical unlocks → anomalous."""
        mock_now.return_value = datetime(2026, 3, 28, 3, 0, tzinfo=JST)

        # 15 events all at hour 18-22
        events = [{"hour": h} for h in [18, 19, 20, 21, 22] * 3]
        mock_events.return_value = events

        risky, reason = _check_anomaly()
        assert risky is True
        assert "実績のない時間帯" in reason

    @patch("risk_detector._now_jst")
    @patch("risk_detector.get_events_since")
    def test_normal_hour_safe(self, mock_events, mock_now):
        """Current hour is within normal range → safe."""
        mock_now.return_value = datetime(2026, 3, 28, 19, 0, tzinfo=JST)

        events = [{"hour": h} for h in [18, 19, 20, 21, 22] * 5]
        mock_events.return_value = events

        risky, reason = _check_anomaly()
        assert risky is False


# ─── Unlock timeout ───

class TestCheckUnlockTimeout:
    @patch("risk_detector.get_last_unlock_time")
    def test_locked_safe(self, mock_last):
        """Locked state → no timeout check."""
        risky, reason = check_unlock_timeout(locked=True)
        assert risky is False

    @patch("risk_detector.get_last_unlock_time")
    def test_unlocked_short_safe(self, mock_last):
        """Unlocked for 30 min → safe (< 120 min threshold)."""
        mock_last.return_value = datetime.now(JST) - timedelta(minutes=30)
        risky, reason = check_unlock_timeout(locked=False)
        assert risky is False

    @patch("risk_detector.get_last_unlock_time")
    def test_unlocked_long_risky(self, mock_last):
        """Unlocked for 150 min → risky."""
        mock_last.return_value = datetime.now(JST) - timedelta(minutes=150)
        risky, reason = check_unlock_timeout(locked=False)
        assert risky is True
        assert "長時間" in reason

    @patch("risk_detector.get_last_unlock_time")
    def test_no_history_safe(self, mock_last):
        """No unlock history → safe."""
        mock_last.return_value = None
        risky, reason = check_unlock_timeout(locked=False)
        assert risky is False


# ─── Cooldown ───

class TestCooldown:
    @patch("risk_detector.get_last_alert_time")
    def test_no_previous_alert(self, mock_last):
        mock_last.return_value = None
        assert is_cooled_down() is True

    @patch("risk_detector._now_jst")
    @patch("risk_detector.get_last_alert_time")
    def test_within_cooldown(self, mock_last, mock_now):
        mock_last.return_value = datetime(2026, 3, 28, 9, 0, tzinfo=JST)
        mock_now.return_value = datetime(2026, 3, 28, 9, 15, tzinfo=JST)  # 15 min < 30
        assert is_cooled_down() is False

    @patch("risk_detector._now_jst")
    @patch("risk_detector.get_last_alert_time")
    def test_after_cooldown(self, mock_last, mock_now):
        mock_last.return_value = datetime(2026, 3, 28, 8, 0, tzinfo=JST)
        mock_now.return_value = datetime(2026, 3, 28, 9, 0, tzinfo=JST)  # 60 min > 30
        assert is_cooled_down() is True


# ─── Evaluate risk (integration) ───

class TestEvaluateRisk:
    @patch("risk_detector.is_cooled_down", return_value=False)
    @patch("risk_detector.check_risk")
    def test_suppressed_by_cooldown(self, mock_checks, mock_cool):
        mock_checks.return_value = [(True, "深夜帯の解錠")]
        risky, reasons = evaluate_risk()
        assert risky is False
        assert reasons == []

    @patch("risk_detector.is_cooled_down", return_value=True)
    @patch("risk_detector.check_risk")
    def test_multiple_reasons(self, mock_checks, mock_cool):
        mock_checks.return_value = [
            (True, "深夜帯の解錠"),
            (False, None),
            (True, "過去30日で解錠実績のない時間帯"),
        ]
        risky, reasons = evaluate_risk()
        assert risky is True
        assert len(reasons) == 2

    @patch("risk_detector.is_cooled_down", return_value=True)
    @patch("risk_detector.check_risk")
    def test_no_risk(self, mock_checks, mock_cool):
        mock_checks.return_value = [(False, None), (False, None), (False, None)]
        risky, reasons = evaluate_risk()
        assert risky is False
        assert reasons == []
