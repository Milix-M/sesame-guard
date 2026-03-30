"""LINE Messaging API接続テストスクリプト。

使い方:
    python test_line.py

環境変数 LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID が設定されている必要があります。
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
user_id = os.environ.get("LINE_USER_ID", "")

if not token or not user_id:
    print("❌ 環境変数が未設定です")
    if not token:
        print("   LINE_CHANNEL_ACCESS_TOKEN を設定してください")
    if not user_id:
        print("   LINE_USER_ID を設定してください")
    sys.exit(1)

print(f"Channel Access Token: {token[:10]}...{token[-4:]}")
print(f"User ID: {user_id[:10]}...{user_id[-4:]}")
print()

# 1. Bot info取得テスト
import requests

print("📡 Bot情報を取得中...")
resp = requests.get(
    "https://api.line.me/v2/bot/info",
    headers={"Authorization": f"Bearer {token}"},
    timeout=10,
)
if resp.status_code == 200:
    info = resp.json()
    print(f"✅ Bot名: {info.get('displayName')}")
    print(f"   Bot ID: {info.get('botId')}")
    print(f"   プレミアム: {'はい' if info.get('premium') else 'いいえ'}")
else:
    print(f"❌ Bot情報の取得に失敗: {resp.status_code}")
    print(f"   {resp.text}")
    sys.exit(1)

print()

# 2. プッシュメッセージ送信テスト
print("📨 テストメッセージを送信中...")
resp = requests.post(
    "https://api.line.me/v2/bot/message/push",
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    },
    json={
        "to": user_id,
        "messages": [{"type": "text", "text": "🔔 SESAME Guard 接続テスト\n\nLINE Messaging APIとの接続を確認しました。"}],
    },
    timeout=10,
)

if resp.status_code == 200:
    print("✅ メッセージ送信成功！LINEアプリを確認してください。")
else:
    print(f"❌ メッセージ送信失敗: {resp.status_code}")
    print(f"   {resp.text}")

    if resp.status_code == 400:
        print()
        print("💡 よくある原因:")
        print("   - User IDが不正（正しいLINEユーザーIDを確認）")
        print("   - Botとまだ友達になっていない（QRコードから友達追加）")
    elif resp.status_code == 401:
        print()
        print("💡 よくある原因:")
        print("   - Channel Access Tokenが無効（再発行してください）")
    elif resp.status_code == 429:
        print()
        print("💡 レート制限に引っかかっています。少し待ってから再試行してください。")
