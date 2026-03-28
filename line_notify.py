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


def send_risk_alert(unlock_time: str, reasons: list[str], battery: int | None = None) -> dict:
    """Send a formatted risk alert notification with multiple reasons."""
    battery_info = f"\n🔋 バッテリー: {battery}%" if battery is not None else ""
    reasons_text = "\n".join(f"  ‣ {r}" for r in reasons)
    msg = (
        f"🚨 SESAME セキュリティ警告\n"
        f"解錠検知: {unlock_time}\n"
        f"判定理由:\n{reasons_text}"
        f"{battery_info}"
    )
    return send_message(msg)


def send_timeout_alert(elapsed_min: int, battery: int | None = None) -> dict:
    """Send unlock timeout alert."""
    battery_info = f"\n🔋 バッテリー: {battery}%" if battery is not None else ""
    msg = (
        f"⚠️ SESAME 長時間未施錠警告\n"
        f"解錠から{elapsed_min}分が経過しています\n"
        f"施錠忘れの可能性があります"
        f"{battery_info}"
    )
    return send_message(msg)
