"""LINE Messaging API notification client."""

import requests
from config import LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

API_URL = "https://api.line.me/v2/bot/message/push"


def send_message(text: str) -> dict:
    """Send a push message to the configured LINE user."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": text}],
    }
    resp = requests.post(API_URL, headers=headers, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def send_risk_alert(unlock_time: str, reason: str, battery: int | None = None) -> dict:
    """Send a formatted risk alert notification."""
    battery_info = f"\n🔋 バッテリー: {battery}%" if battery is not None else ""
    msg = (
        f"🚨 SESAME セキュリティ警告\n"
        f"解錠検知: {unlock_time}\n"
        f"理由: {reason}"
        f"{battery_info}"
    )
    return send_message(msg)
