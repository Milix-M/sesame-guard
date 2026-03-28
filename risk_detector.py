"""Risk detection logic for SESAME unlock events."""

from datetime import datetime, timezone, timedelta

from config import RISK_NIGHT_START, RISK_NIGHT_END, RISK_RAPID_THRESHOLD_SEC, RISK_RAPID_COUNT
from db import count_recent_unlocks

JST = timezone(timedelta(hours=9))


def check_risk() -> tuple[bool, str | None]:
    """Check if current unlock is risky. Returns (is_risky, reason)."""

    # 1. Nighttime unlock (JST)
    hour = datetime.now(JST).hour
    if RISK_NIGHT_START <= hour < RISK_NIGHT_END:
        return True, f"深夜帯の解錠（{hour}:00台）"

    # 2. Rapid successive unlocks
    recent = count_recent_unlocks(RISK_RAPID_THRESHOLD_SEC)
    if recent >= RISK_RAPID_COUNT:
        return True, f"短時間に{recent}回の解錠（{RISK_RAPID_THRESHOLD_SEC}秒以内）"

    return False, None
