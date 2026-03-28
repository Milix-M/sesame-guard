# 🔐 sesame-guard

SESAMEスマートロックのセキュリティ監視ツール。

不審な解錠を検知してLINEに通知します。

## 機能

- SESAME Web API v3で施錠/解錠状態を定期ポーリング
- リスクの高い解錠を自動検知：
  - 深夜帯（2:00〜5:00）の解錠
  - 短時間の連続解錠（5分以内に3回以上）
- LINE Messaging APIでリアルタイム通知
- SQLiteでイベント履歴を記録

## 必要なもの

- SESAME スマートロック + Wi-Fi Access Point（Hub）
- SESAME API キー（[Candy House Dashboard](https://my.candyhouse.co) で発行）
- LINE Messaging API チャネル（[LINE Developers](https://developers.line.biz/) で作成）

## セットアップ

```bash
git clone https://github.com/Milix-M/sesame-guard.git
cd sesame-guard
python -m venv .venv
source .venv/bin/activate
pip install requests
```

## 設定

環境変数を設定：

```bash
export SESAME_API_TOKEN="your_api_token"
export SESAME_DEVICE_ID="your_device_id"  # 省略時は自動検出
export LINE_CHANNEL_ACCESS_TOKEN="your_line_token"
export LINE_USER_ID="your_line_user_id"

# オプション
export RISK_NIGHT_START=2          # 深夜判定開始時（時）
export RISK_NIGHT_END=5            # 深夜判定終了時（時）
export RISK_RAPID_THRESHOLD_SEC=300 # 連続解錠の閾値（秒）
export RISK_RAPID_COUNT=3           # 連続解錠の回数
export POLL_INTERVAL_SEC=60         # ポーリング間隔（秒）
export DB_PATH="sesame_guard.db"    # DBファイルパス
```

## 実行

```bash
python main.py
```

## デーモン化（systemd例）

```ini
[Unit]
Description=SESAME Guard
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/sesame-guard
ExecStart=/opt/sesame-guard/.venv/bin/python main.py
EnvironmentFile=/opt/sesame-guard/.env
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## ライセンス

MIT
