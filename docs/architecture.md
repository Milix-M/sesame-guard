# SESAME Guard - アーキテクチャ設計書

## 全体構成

```
┌─────────────┐    polling     ┌──────────────┐    HTTPS     ┌──────────────┐
│  OCI Server  │ ────────────→ │  SESAME API  │              │  LINE API    │
│  (Python)    │ ←──────────── │  (Cloud v3)  │              │  (Messaging) │
│              │               └──────────────┘              └──────┬───────┘
│  ┌─────────┐ │                                           ↑       │
│  │ SQLite  │ │                                           │       ↓
│  └─────────┘ │               ┌──────────────┐     ┌────────────┐
└─────────────┘               │   Scheduler   │     │   れおさん    │
                              │  (cron/systemd)│     │  (LINE App) │
                              └──────────────┘     └────────────┘
```

## コンポーネント

### 1. メインループ (`main.py`)
- **責務**: 定期ポーリングの実行、状態変化の検知、各モジュールの統括
- **動作**: 指定間隔（デフォルト60秒）でSESAME APIにアクセスし、状態変化を検知
- **異常時**: API呼び出し失敗時はエラーログを出力し、次回ポーリングまで待機

### 2. SESAMEクライアント (`sesame_client.py`)
- **責務**: SESAME Web API v3との通信
- **エンドポイント**: `https://api.candyhouse.co/public`
- **認証**: AuthorizationヘッダーにAPIトークンを設定
- **取得情報**: 施錠状態（locked）、バッテリー残量（battery）、応答性（responsive）

### 3. リスク検知エンジン (`risk_detector.py`)
- **責務**: 解錠イベントの危険度判定
- **判定ロジック**: 後述の「リスク判定ルール」を参照

### 4. LINE通知 (`line_notify.py`)
- **責務**: LINE Messaging API経由でプッシュ通知を送信
- **認証**: Bearer トークン（Channel Access Token）
- **送信先**: 設定されたLINEユーザーID

### 5. データ層 (`db.py`)
- **責務**: SQLiteによる状態管理とイベント履歴の永続化
- **テーブル構成**:
  - `lock_state`: 現在の施錠状態（1行のみ）
  - `events`: 全イベント履歴（解錠・リスク検知）

## データフロー

```
[1分毎]
  │
  ▼
SESAME API → status取得 (locked, battery)
  │
  ▼
前回状態と比較
  │
  ├── 状態変化なし → save_state() → 待機
  │
  └── locked→unlocked 検知
        │
        ▼
      check_risk()
        │
        ├── risky=False → save_event() → save_state() → 待機
        │
        └── risky=True → save_event() → send_risk_alert() → save_state() → 待機
```

## エラーハンドリング

| エラー | 対処 |
|--------|------|
| SESAME APIタイムアウト | ログ出力、次回ポーリングまで待機 |
| SESAME API認証エラー | ログ出力、次回ポーリングまで待機 |
| LINE API送信失敗 | ログ出力、イベントはDBに記録済み |
| SQLite書き込みエラー | ログ出力、次回ポーリングまで待機 |

## デプロイ構成

```
OCI Compute Instance (ARM)
├── /opt/sesame-guard/
│   ├── main.py
│   ├── config.py
│   ├── sesame_client.py
│   ├── risk_detector.py
│   ├── line_notify.py
│   ├── db.py
│   ├── .env
│   └── .venv/
└── systemd: sesame-guard.service
```
