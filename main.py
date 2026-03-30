"""SESAME Guard - Main polling loop (SESAME Biz API)."""

import logging
import time
import sys
from datetime import datetime, timezone, timedelta

from config import (
    SESAME_API_KEY, SESAME_SECRET_KEY, SESAME_DEVICE_ID,
    POLL_INTERVAL_SEC, RISK_UNLOCK_TIMEOUT_MIN,
)
from sesame_client import SesameBizClient
from line_notify import send_risk_alert, send_timeout_alert
from risk_detector import evaluate_risk, check_unlock_timeout
from db import (
    init_db, get_last_state, save_state, save_event, save_alert,
    get_last_unlock_time, get_last_history_timestamp,
)

JST = timezone(timedelta(hours=9))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# Track last timeout alert to avoid spamming
_last_timeout_alert_min = 0


def create_client() -> SesameBizClient:
    if not SESAME_API_KEY:
        log.error("SESAME_API_KEY not set")
        sys.exit(1)
    if not SESAME_DEVICE_ID:
        log.error("SESAME_DEVICE_ID not set")
        sys.exit(1)

    return SesameBizClient(
        api_key=SESAME_API_KEY,
        secret_key=SESAME_SECRET_KEY,
    )


def check_new_unlocks(client: SesameBizClient) -> list[dict]:
    """Fetch unlock events since last check using history API."""
    last_ts = get_last_history_timestamp()
    if last_ts is None:
        # First run: just record current timestamp, don't alert for old events
        now = datetime.now().timestamp()
        save_event("init", True, None, False, None)
        return []

    try:
        return client.get_unlock_history(SESAME_DEVICE_ID, since_timestamp=last_ts)
    except Exception as e:
        log.error(f"History fetch error: {e}")
        return []


def poll() -> None:
    global _last_timeout_alert_min

    client = create_client()
    init_db()

    log.info(f"SESAME Guard started (device: {SESAME_DEVICE_ID[:8]}...)")

    while True:
        try:
            # 1. Check for new unlock events via history API
            new_unlocks = check_new_unlocks(client)
            for unlock in new_unlocks:
                ts = unlock.get("timeStamp", 0)
                dt = datetime.fromtimestamp(ts, tz=JST)
                tag = unlock.get("historyTag")

                log.info(f"Unlock detected from history: {dt.isoformat()}")

                is_risky, reasons = evaluate_risk()
                tag_info = f" ({tag})" if tag else ""
                save_event(
                    "unlock", False, None,
                    is_risky,
                    " | ".join(reasons) if reasons else None,
                )

                if is_risky and reasons:
                    log.warning(f"RISKY UNLOCK: {reasons}")
                    try:
                        send_risk_alert(
                            unlock_time=dt.strftime("%Y-%m-%d %H:%M:%S JST"),
                            reasons=reasons,
                            battery=None,
                        )
                        save_alert(reasons)
                    except Exception as e:
                        log.error(f"LINE notification failed: {e}")

                # Update last seen timestamp
                from db import set_last_history_timestamp
                set_last_history_timestamp(ts)

            # 2. Also poll current status for timeout detection
            status = client.get_status(SESAME_DEVICE_ID)
            locked = status["locked"]
            battery = status["battery"]

            # Check unlock timeout
            if not locked:
                timeout_risky, timeout_reason = check_unlock_timeout(locked)
                if timeout_risky and timeout_reason:
                    last_unlock = get_last_unlock_time()
                    elapsed = int((datetime.now(JST) - last_unlock).total_seconds() / 60) if last_unlock else 0

                    if elapsed > _last_timeout_alert_min:
                        log.warning(f"UNLOCK TIMEOUT: {timeout_reason}")
                        _last_timeout_alert_min = elapsed
                        try:
                            send_timeout_alert(elapsed_min=elapsed, battery=battery)
                        except Exception as e:
                            log.error(f"LINE timeout notification failed: {e}")

            if locked:
                _last_timeout_alert_min = 0

            # Save state
            prev = get_last_state()
            if prev is None or prev["locked"] != locked:
                save_event("status_change", locked, battery, False, None)
            save_state(locked)

        except Exception as e:
            log.error(f"Poll error: {e}")

        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    poll()
