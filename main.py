"""SESAME Guard - Main polling loop."""

import logging
import time
import sys

from config import SESAME_API_TOKEN, SESAME_DEVICE_ID, POLL_INTERVAL_SEC
from sesame_client import get_sesame_status, get_sesames
from line_notify import send_risk_alert
from risk_detector import check_risk
from db import init_db, get_last_state, save_state, save_event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


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

            # Detect state change: locked -> unlocked
            if prev is not None and prev["locked"] and not locked:
                log.info(f"Unlock detected at {__import__('datetime').datetime.utcnow().isoformat()}")

                is_risky, reason = check_risk()
                save_event("unlock", locked, battery, is_risky, reason)

                if is_risky:
                    log.warning(f"RISKY UNLOCK: {reason}")
                    try:
                        send_risk_alert(
                            unlock_time=__import__('datetime').datetime.now(
                                __import__('datetime').timezone(__import__('datetime').timedelta(hours=9))
                            ).strftime("%Y-%m-%d %H:%M:%S JST"),
                            reason=reason,
                            battery=battery,
                        )
                    except Exception as e:
                        log.error(f"LINE notification failed: {e}")
            else:
                # Save periodic state (no alert)
                if prev is None or prev["locked"] != locked:
                    save_event("status_change", locked, battery, False, None)

            save_state(locked)

        except Exception as e:
            log.error(f"Poll error: {e}")

        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    poll()
