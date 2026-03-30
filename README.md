# 🔐 sesame-guard

SESAMEスマートロック（SESAME Biz）のセキュリティ監視ツール。

不審な解錠を検知してLINEに通知します。

## 機能

- SESAME Biz Web APIで解錠履歴・ステータスを定期取得
- リスクの高い解錠を自動検知：
  - 深夜帯（2:00〜5:00 JST）の解錠 — 平日/休日で判定を分離
  - 短時間の連続解錠（5分以内に3回以上）
  - 統計的異常検知（過去30日のパターンから外れる時間帯の解錠）
  - 長時間未施錠（2時間以上解錠されたまま）
- LINE Messaging APIでリアルタイム通知（クールダウン付き）
- SQLiteでイベント履歴を記録

## 必要なもの

- SESAME スマートロック + Wi-Fi Access Point（Hub3）
- SESAME Biz アカウント & APIキー（<https://biz.candyhouse.co/> ）
- LINE Messaging API チャネル（<https://developers.line.biz/> で作成）

## セットアップ

```bash
git clone https://github.com/Milix-M/sesame-guard.git
cd sesame-guard
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env を編集してAPIキー等を設定
```

## 設定

`.env` に以下を設定：

```bash
# SESAME Biz API（必須）
SESAME_API_KEY=your_api_key
SESAME_SECRET_KEY=your_secret_key  # 制御コマンド使用時のみ必須
SESAME_DEVICE_ID=your_sesame_uuid  # SESAMEデバイスUUID

# LINE Messaging API（必須）
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token
LINE_USER_ID=your_line_user_id

# リスク検知（任意、デフォルト値あり）
RISK_NIGHT_START=2          # 深夜判定開始時（JST）
RISK_NIGHT_END=5            # 深夜判定終了時（JST）
RISK_RAPID_THRESHOLD_SEC=300 # 連続解錠の閾値（秒）
RISK_RAPID_COUNT=3           # 連続解錠の回数
RISK_UNLOCK_TIMEOUT_MIN=120 # 未施錠警告の閾値（分）
RISK_COOLDOWN_MIN=30         # 通知クールダウン（分）
RISK_ANOMALY_SIGMA=2.0       # 異常検知のσ閾値
POLL_INTERVAL_SEC=60         # ポーリング間隔（秒）
```

### APIキーの取得

- **SESAME_API_KEY / SESAME_SECRET_KEY**: <https://biz.candyhouse.co/> にログイン → 開発者向けページ
- **SESAME_DEVICE_ID**: SESAMEアプリ内のデバイスUUID（`xxx-xxx-xxx` 形式）
- **LINE_CHANNEL_ACCESS_TOKEN**: LINE Developers → Messaging API → チャネルアクセストークン
- **LINE_USER_ID**: LINE Developersのコンソール等で取得可能

## 実行

```bash
python main.py
```

## リスク判定ルール

| ルール | 説明 | 平日 | 休日 |
|--------|------|------|------|
| 深夜帯解錠 | 深夜の解錠を警告 | 2:00〜5:00 | 3:00〜5:00 |
| 連続解錠 | 短時間に複数回の解錠 | 5分以内に3回以上 | 同左 |
| 異常検知 | 過去30日のパターンと乖離 | 2σ以上の乖離 | 同左 |
| 未施錠警告 | 解錠されたまま放置 | 2時間以上 | 同左 |

### 統計的異常検知について

過去30日間の解錠時間を学習し、通常と異なる時間帯の解錠を検知します。外部ライブラリ不要の純粋な統計計算で、データが蓄積するほど精度が上がります。

## プロジェクト構成

```
sesame-guard/
├── main.py              # メインポーリングループ
├── config.py            # 環境変数管理
├── sesame_client.py     # SESAME Biz API クライアント
├── risk_detector.py     # リスク判定エンジン
├── line_notify.py       # LINE 通知クライアント
├── db.py                # SQLite データ管理
├── .env.example         # 環境変数テンプレート
├── requirements.txt     # Python依存
├── docs/
│   ├── architecture.md  # アーキテクチャ設計書
│   └── specification.md # 機能仕様書
└── tests/               # テストコード
```

## テスト

```bash
pip install pytest
pytest tests/ -v
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

```bash
sudo cp sesame-guard.service /etc/systemd/system/
sudo systemctl enable sesame-guard
sudo systemctl start sesame-guard
```

## ライセンス

MIT
