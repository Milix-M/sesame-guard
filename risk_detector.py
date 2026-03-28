"""Risk detection logic for SESAME unlock events."""

from datetime import datetime, timezone, timedelta
import math

from config import (
    RISK_NIGHT_START, RISK_NIGHT_END,
    RISK_RAPID_THRESHOLD_SEC, RISK_RAPID_COUNT,
    RISK_UNLOCK_TIMEOUT_MIN, RISK_COOLDOWN_MIN,
    RISK_ANOMALY_SIGMA,
)
from db import count_recent_unlocks, get_events_since, get_last_alert_time

JST = timezone(timedelta(hours=9))


def _now_jst() -> datetime:
    return datetime.now(JST)


def _is_weekend(dt: datetime) -> bool:
    """Saturday=5, Sunday=6"""
    return dt.weekday() >= 5


def _hour(dt: datetime) -> int:
    return dt.hour


# ─── Rule 1: Nighttime unlock (weekday vs weekend differentiated) ───

def _check_nighttime() -> tuple[bool, str | None]:
    now = _now_jst()
    hour = _hour(now)
    weekend = _is_weekend(now)

    # Weekday: full night range
    # Weekend: narrower range (people stay out late)
    if weekend:
        night_start = max(RISK_NIGHT_START, 3)  # 3:00 on weekends
        night_end = RISK_NIGHT_END
    else:
        night_start = RISK_NIGHT_START
        night_end = RISK_NIGHT_END

    if night_start <= hour < night_end:
        label = "休日" if weekend else "平日"
        return True, f"深夜帯の解錠（{label} {hour}:00台）"

    return False, None


# ─── Rule 2: Rapid successive unlocks ───

def _check_rapid_unlock() -> tuple[bool, str | None]:
    recent = count_recent_unlocks(RISK_RAPID_THRESHOLD_SEC)
    if recent >= RISK_RAPID_COUNT:
        return True, f"短時間に{recent}回の解錠（{RISK_RAPID_THRESHOLD_SEC}秒以内）"
    return False, None


# ─── Rule 3: Anomaly detection (pattern learning) ───

def _check_anomaly() -> tuple[bool, str | None]:
    """Statistical anomaly detection based on historical unlock hours.

    Builds a distribution of unlock hours from the past N days,
    then checks if the current hour is an outlier (>2σ from mean or
    in a time slot with zero historical activity).
    """
    now = _now_jst()
    current_hour = _hour(now)

    # Gather unlock events from past 30 days
    events = get_events_since(days=30, event_type="unlock")
    if len(events) < 10:
        # Not enough data to build pattern
        return False, None

    # Build hour distribution
    hours = [e["hour"] for e in events]
    total = len(hours)

    # Count unlocks per hour
    hour_counts = [0] * 24
    for h in hours:
        hour_counts[h] += 1

    # Method 1: If this hour has zero unlocks in 30 days → anomalous
    if hour_counts[current_hour] == 0:
        return True, f"過去30日で解錠実績のない時間帯（{current_hour}:00台）"

    # Method 2: Z-score based anomaly
    mean = sum(hours) / total
    variance = sum((h - mean) ** 2 for h in hours) / total
    std = math.sqrt(variance)

    if std > 0:
        # Circular distance (hours wrap around)
        diff = min(abs(current_hour - mean), 24 - abs(current_hour - mean))
        z_score = diff / std

        if z_score > RISK_ANOMALY_SIGMA:
            return True, f"通常と異なる時間帯の解錠（{current_hour}:00台、通常は{int(mean)}時台付近）"

    return False, None


# ─── Rule 4: Unlock timeout (unlocked too long) ───

def check_unlock_timeout(locked: bool) -> tuple[bool, str | None]:
    """Check if the lock has been unlocked for too long."""
    if locked:
        return False, None

    from db import get_last_unlock_time
    last_unlock = get_last_unlock_time()
    if last_unlock is None:
        return False, None

    elapsed_min = (_now_jst() - last_unlock).total_seconds() / 60
    if elapsed_min >= RISK_UNLOCK_TIMEOUT_MIN:
        return True, f"長時間未施錠（{int(elapsed_min)}分経過）"

    return False, None


# ─── Cooldown check ───

def is_cooled_down() -> bool:
    """Check if enough time has passed since last alert."""
    last = get_last_alert_time()
    if last is None:
        return True
    elapsed = (_now_jst() - last).total_seconds() / 60
    return elapsed >= RISK_COOLDOWN_MIN


# ─── Main risk check ───

def check_risk() -> list[tuple[bool, str | None]]:
    """Run all risk checks. Returns list of (is_risky, reason)."""
    results = []

    results.append(_check_nighttime())
    results.append(_check_rapid_unlock())
    results.append(_check_anomaly())

    return results


def evaluate_risk() -> tuple[bool, list[str]]:
    """Evaluate all risk rules. Returns (is_risky, list_of_reasons)."""
    results = check_risk()
    reasons = [r for risky, r in results if risky and r]

    if not reasons:
        return False, []

    if not is_cooled_down():
        return False, []  # suppress during cooldown

    return True, reasons
