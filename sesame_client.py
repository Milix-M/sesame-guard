"""SESAME Web API v3 client."""

import requests
from config import SESAME_API_BASE


def get_sesames(token: str) -> list[dict]:
    """List all SESAME devices."""
    resp = requests.get(
        f"{SESAME_API_BASE}/sesames",
        headers={"Authorization": token},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_sesame_status(token: str, device_id: str) -> dict:
    """Get current status of a SESAME device.

    Returns: {"locked": bool, "battery": int, "responsive": bool}
    """
    resp = requests.get(
        f"{SESAME_API_BASE}/sesame/{device_id}",
        headers={"Authorization": token},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
