"""SESAME Biz Web API client."""

import requests
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))


class SesameBizClient:
    """Client for SESAME Biz Web API.

    Supports both read-only operations (status, history) and
    control commands (lock, unlock, toggle) with AES-CMAC signing.
    """

    BASE_URL = "https://app.candyhouse.co/api/sesame2"

    def __init__(self, api_key: str, secret_key: str = ""):
        self.api_key = api_key
        self.secret_key = secret_key
        self._headers = {"x-api-key": api_key}

    def get_sesames(self) -> list[dict]:
        """List all SESAME devices (not available in Biz API, use config)."""
        raise NotImplementedError(
            "SESAME Biz API does not have a device list endpoint. "
            "Set SESAME_DEVICE_ID directly."
        )

    def get_status(self, device_id: str) -> dict:
        """Get current status of a SESAME device.

        Returns: {
            "batteryPercentage": int,
            "batteryVoltage": float,
            "position": int,
            "CHSesame2Status": "locked" | "unlocked" | "moved",
            "timestamp": int
        }
        """
        resp = requests.get(
            f"{self.BASE_URL}/{device_id}",
            headers=self._headers,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        # Normalize to our internal format
        status = data.get("CHSesame2Status", "moved")
        locked = status == "locked"
        battery = data.get("batteryPercentage", 0)

        return {
            "locked": locked,
            "battery": battery,
            "responsive": True,
            "status_raw": status,
            "position": data.get("position"),
            "timestamp": data.get("timestamp"),
        }

    def get_history(self, device_id: str, page: int = 0, limit: int = 50) -> list[dict]:
        """Get event history for a SESAME device.

        Args:
            device_id: SESAME UUID
            page: Page number (0-based, newest first)
            limit: Number of records to retrieve

        Returns: list of {
            "type": int,       # event type code
            "timeStamp": float, # unix timestamp
            "historyTag": str | None,
            "recordID": int,
            "parameter": any,
        }
        """
        resp = requests.get(
            f"{self.BASE_URL}/{device_id}/history",
            headers=self._headers,
            params={"page": page, "lg": limit},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_unlock_history(self, device_id: str, since_timestamp: float = 0, limit: int = 50) -> list[dict]:
        """Get unlock events since a given timestamp.

        Type codes (partial):
          2  = unlock (by key/Bluetooth)
          11 = lock (auto)
          Other codes exist for different trigger types.

        Args:
            device_id: SESAME UUID
            since_timestamp: Only return events after this unix timestamp
            limit: Max records per page

        Returns: list of history records filtered for unlock events.
        """
        page = 0
        all_unlocks = []

        while True:
            records = self.get_history(device_id, page=page, limit=limit)
            if not records:
                break

            found_old = False
            for r in records:
                if r.get("timeStamp", 0) < since_timestamp:
                    found_old = True
                    break
                # Type 2 = unlock
                if r.get("type") in (2,):
                    all_unlocks.append(r)

            if found_old or len(records) < limit:
                break
            page += 1

        return all_unlocks

    def send_command(self, device_id: str, cmd: int = 83) -> dict:
        """Send a control command to SESAME.

        Requires AES-CMAC signing with the device secret key.

        Args:
            device_id: SESAME UUID
            cmd: Command code (82=lock, 83=unlock, 88=toggle)

        Returns: API response
        """
        if not self.secret_key:
            raise ValueError("secret_key is required for control commands. Set SESAME_SECRET_KEY.")

        import base64
        import struct

        ts = int(datetime.now().timestamp())
        # Build message: 4-byte little-endian timestamp, take bytes 1-3
        ts_bytes = struct.pack("<I", ts)
        message = ts_bytes[1:4]

        # AES-CMAC
        sign = self._aes_cmac(bytes.fromhex(self.secret_key), message)

        history = base64.b64encode(b"sesame_guard").decode()

        resp = requests.post(
            f"{self.BASE_URL}/{device_id}/cmd",
            headers={**self._headers, "Content-Type": "application/json"},
            json={
                "cmd": cmd,
                "history": history,
                "sign": sign,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def lock(self, device_id: str) -> dict:
        return self.send_command(device_id, cmd=82)

    def unlock(self, device_id: str) -> dict:
        return self.send_command(device_id, cmd=83)

    def toggle(self, device_id: str) -> dict:
        return self.send_command(device_id, cmd=88)

    @staticmethod
    def _aes_cmac(key: bytes, message: bytes) -> str:
        """Compute AES-CMAC."""
        try:
            from Crypto.Hash import CMAC
            from Crypto.Cipher import AES

            cmac = CMAC.new(key, ciphermod=AES)
            cmac.update(message)
            return cmac.hexdigest()
        except ImportError:
            # Fallback using cryptography library
            from cryptography.hazmat.primitives.cmac import CMAC
            from cryptography.hazmat.primitives import hashes

            c = CMAC(key, hashes.BLAKE2s(16))
            # AES-CMAC requires manual implementation with cryptography lib
            # For now, raise helpful error
            raise ImportError(
                "AES-CMAC requires 'pycryptodome' package. "
                "Install with: pip install pycryptodome"
            )


# Legacy compatibility
def get_sesames(token: str) -> list[dict]:
    raise NotImplementedError("Use SesameBizClient.get_status() with SESAME_DEVICE_ID.")


def get_sesame_status(token: str, device_id: str) -> dict:
    raise NotImplementedError("Use SesameBizClient class instead. See sesame_client.py.")
