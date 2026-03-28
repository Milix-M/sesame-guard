"""SESAME Guard - Main polling loop."""

import logging
import time
import sys
from datetime import datetime, timezone, timedelta

from config import SESAME_API_TOKEN, SESAME_DEVICE_ID, POLL_INTERVAL_SEC
from sesame_client import get_sesame_status, get_sesames
from line_notify import send_risk_alert, send_timeout_alert
from risk_detector import evaluate_risk, check_unlock_timeout
from db import init_db, get_last_state, save_state, save_event, save_alert, get_last_unlock_time

JST = timezone(timedelta(hours=9))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# Track last timeout alert to avoid spamming
_last_timeout_alert_min = 0


def find_device_id(token: str) -> str | None:
    """Auto-detect device ID if not configured."""
    try:
        devices = get_sesames(token)
        if devices:
            return devices[0]["device_id"]
    except Exception:
        pass
    return None


def poll() -> None:
    global _last_timeout_alert_min

    token = SESAME_API_TOKEN
    device_id = SESAME_DEVICE_ID

    if not token:
        log.error("SESAME_API_TOKEN not set")
        sys.exit(1)

    if not device_id:
        log.info("SESAME_DEVICE_ID not set, auto-detecting...")
        device_id = find_device_id(token)
        if not device_id:
            log.error("No SESAME device found")
            sys.exit(1)
        log.info(f"Found device: {device_id}")

    init_db()

    log.info("SESAME Guard started")

    while True:
        try:
            status = get_sesame_status(token, device_id)
            locked = status["locked"]
            battery = status.get("battery")

            prev = get_last_state()

            # Detect state change: locked → unlocked
            if prev is not None and prev["locked"] and not locked:
                log.info(f"Unlock detected at {datetime.now(JST).isoformat()}")

                is_risky, reasons = evaluate_risk()
                save_event("unlock", locked, battery, is_risky, " | ".join(reasons) if reasons else None)

                if is_risky and reasons:
                    log.warning(f"RISKY UNLOCK: {reasons}")
                    try:
                        send_risk_alert(
                            unlock_time=datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
                            reasons=reasons,
                            battery=battery,
                        )
                        save_alert(reasons)
                    except Exception as e:
                        log.error(f"LINE notification failed: {e}")

            # Check unlock timeout (runs every poll when unlocked)
            if not locked:
                timeout_risky, timeout_reason = check_unlock_timeout(locked)
                if timeout_risky and timeout_reason:
                    last_unlock = get_last_unlock_time()
                    elapsed = int((datetime.now(JST) - last_unlock).total_seconds() / 60) if last_unlock else 0

                    # Only alert once per timeout cycle (reset when locked again)
                    if elapsed > _last_timeout_alert_min:
                        log.warning(f"UNLOCK TIMEOUT: {timeout_reason}")
                        _last_timeout_alert_min = elapsed
                        try:
                            send_timeout_alert(elapsed_min=elapsed, battery=battery)
                        except Exception as e:
                            log.error(f"LINE timeout notification failed: {e}")

            if locked:
                _last_timeout_alert_min = 0

            # Save state changes
            if prev is None or prev["locked"] != locked:
                save_event("status_change", locked, battery, False, None)

            save_state(locked)

        except Exception as e:
            log.error(f"Poll error: {e}")

        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    poll()
