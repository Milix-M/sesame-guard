# SESAME Guard - 機能仕様書

## 概要

SESAMEスマートロックの解錠イベントを監視し、リスクの高い解錠を検知してLINEに通知するセキュリティ監視ツール。

## 前提条件

- SESAMEスマートロック（CANDY HOUSE製）
- Wi-Fi Access Point（Hub3）が設定済み
- SESAME API v3が有効（Candy House Dashboard → Integration ON）
- OCI Compute Instance上で稼働

---

## 1. ポーリング機能

### 1.1 状態取得
- SESAME Web API v3の `GET /sesame/{device_id}` を定期呼び出し
- デフォルト間隔: 60秒（環境変数 `POLL_INTERVAL_SEC` で変更可）
- 取得項目: `locked`（bool）, `battery`（int）, `responsive`（bool）

### 1.2 デバイス自動検出
- `SESAME_DEVICE_ID` 未設定時、`GET /sesames` で一覧取得し、最初のデバイスを使用

### 1.3 状態変化検知
- 前回の `locked` 状態と比較
- **locked → unlocked** の変化のみを「解錠イベント」として扱う
- unlocked → locked の変化は記録するが通知はしない

---

## 2. リスク判定ルール

### 2.1 深夜帯の解錠

| 項目 | 値 |
|------|-----|
| 対象時間帯 | 2:00 〜 5:00（UTC） |
| 環境変数 | `RISK_NIGHT_START`, `RISK_NIGHT_END` |
| 判定条件 | 解錠イベントの発生時刻が対象時間帯に含まれる |
| 検知理由文 | 「深夜帯の解錠（{H}:00台）」 |

> **⚠️ 注意**: 現在はUTC基準。JSTで運用する場合は `RISK_NIGHT_START=17`, `RISK_NIGHT_END=20` に設定するか、コードの修正が必要。

### 2.2 短時間の連続解錠

| 項目 | 値 |
|------|-----|
| 監視期間 | 300秒（5分） |
| 閾値 | 3回以上の解錠 |
| 環境変数 | `RISK_RAPID_THRESHOLD_SEC`, `RISK_RAPID_COUNT` |
| 判定条件 | 監視期間内の解錠イベント数が閾値以上 |
| 検知理由文 | 「短時間に{N}回の解錠（{SEC}秒以内）」 |

### 2.3 判定の優先度

深夜帯チェック → 連続解錠チェックの順。最初にマッチしたルールを返す。

---

## 3. 通知機能

### 3.1 通知先
- LINE Messaging API（プッシュメッセージ）

### 3.2 通知フォーマット

```
🚨 SESAME セキュリティ警告
解錠検知: 2026-03-28 02:15:00 UTC
理由: 深夜帯の解錠（2:00台）
🔋 バッテリー: 85%
```

### 3.3 通知タイミング
- リスク判定が `True` の場合のみ通知
- 通常の解錠（リスクなし）はDB記録のみ

---

## 4. データ管理

### 4.1 lock_state テーブル

| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | 常に1（単一行） |
| locked | BOOLEAN | 現在の施錠状態 |
| updated_at | TEXT | 最終更新日時（ISO 8601） |

### 4.2 events テーブル

| カラム | 型 | 説明 |
|--------|-----|------|
| id | INTEGER | 自動採番 |
| event_type | TEXT | `unlock` / `status_change` |
| locked | BOOLEAN | イベント時の状態 |
| battery | INTEGER | バッテリー残量 |
| is_risky | BOOLEAN | リスク判定結果 |
| reason | TEXT | リスク理由（nullable） |
| created_at | TEXT | イベント日時（ISO 8601） |

### 4.3 データ保持
- 現状、自動削除なし（運用に応じて追加予定）

---

## 5. 環境変数一覧

| 変数名 | 必須 | デフォルト | 説明 |
|--------|------|-----------|------|
| `SESAME_API_TOKEN` | ✅ | - | SESAME API認証トークン |
| `SESAME_DEVICE_ID` | ❌ | 自動検出 | SESAMEデバイスID |
| `LINE_CHANNEL_ACCESS_TOKEN` | ✅ | - | LINE Messaging API トークン |
| `LINE_USER_ID` | ✅ | - | 通知先LINEユーザーID |
| `RISK_NIGHT_START` | ❌ | `2` | 深夜判定開始時（時、UTC） |
| `RISK_NIGHT_END` | ❌ | `5` | 深夜判定終了時（時、UTC） |
| `RISK_RAPID_THRESHOLD_SEC` | ❌ | `300` | 連続解錠の監視期間（秒） |
| `RISK_RAPID_COUNT` | ❌ | `3` | 連続解錠の閾値（回） |
| `POLL_INTERVAL_SEC` | ❌ | `60` | ポーリング間隔（秒） |
| `DB_PATH` | ❌ | `sesame_guard.db` | SQLiteファイルパス |

---

## 6. 今後の拡張候補

- JST基準の時間判定対応
- SESAME APIのWebhook対応（もしあれば）
- 通知先の追加（Discord、Email等）
- イベントの自動アーカイブ・削除
- ダッシュボード（簡易Web UI）
- 複数デバイス対応
- バッテリー低下通知
