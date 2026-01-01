# 20 Data Contracts（DB / API / イベント契約）

作成日: 2025-12-27（Asia/Tokyo）  
更新日: 2025-12-31（Asia/Tokyo）

更新履歴
- 2025-12-27: 初版作成。
- 2025-12-28: 手動実行/定期実行状態/同期のAPI契約を追記。
- 2025-12-31: 同期方向を api→scraper に更新。

このドキュメントは、**api-service → scraper-service** の同期契約と **api-service → DB** までの「壊れない約束（契約）」を定義する。  
実装（コード・内部構造）は変えてもよいが、**契約変更は原則として後方互換**を維持する。

- DB 概念設計: `02_database_design.md`
- スクレイピング要件: `04_scraping_requirements.md`
- OpenAPI（正）: `21_openapi.yaml`

---

## 1. 用語・キー

### 1.1 race_key / race_id
- **race_key**: `(race_date, baba_code, race_no)`  
  - `race_date`: `YYYY-MM-DD`（JST）
  - `baba_code`: 開催場コード（例: `18`）
  - `race_no`: `1..12`
- **race_id**: `races` の PK（DB 内部ID）

> Upsert / 冪等ETL は **race_key を一次キー**として行い、DB 内で race_id に正規化する。

### 1.2 snapshot_kind（代表オッズ時点）
- `t_minus_60m` / `t_minus_30m` / `t_minus_20m` / `t_minus_10m` / `t_minus_5m` / `t_minus_1m` / `final` がデフォルト（運用で追加可）
- OpenAPI は **固定 enum にしない**（文字列として拡張可能に扱う）
- 実取得時刻は **必ず** `captured_at`（timestamp, JST）に保存する
- 手動取得は `captured_at` と `races.start_time` から **最も近い `snapshot_kind`** を割り当てる  
  - `captured_at >= races.start_time` は `final` とみなす

### 1.3 bet_type / legs / is_ordered
- **bet_type（共通列挙）**
  - `tansho`, `fukusho`, `wakuren`, `wakutan`, `umaren`, `umatan`, `wide`, `sanrenpuku`, `sanrentan`
- **legs**
  - `wakuren/wakutan` は枠番、それ以外は馬番
  - 配列（例: `[3]`, `[3,7]`, `[3,7,12]`）。並び順は `is_ordered` に従う
- **is_ordered**
  - `wakutan` / `umatan` / `sanrentan` は `true`
  - それ以外は `false`

### 1.4 event_id（冪等化キー）
- 送信する「同期イベント」には `event_id`（UUID）を付与する
- 受信側は `event_id` を用いて **重複受信を検知し、再実行しても同じ結果**になるようにする

---

## 2. 正規化ルール（Odds / Payout）

### 2.1 Odds（odds_min / odds_max へ統一）
- 単値: `odds_min = odds_max`
- レンジ: `odds_min <= odds_max`
- 欠損/発売なし: 両方 `NULL`
- `popularity` は取得できない場合 `NULL` を許容

### 2.2 Payout（払戻）
- 1レコードは `bet_type × legs × is_ordered`
- `payout_yen` は整数（円）
- 返還/不成立等は将来 `status` 追加で拡張する（現時点は未実装）

---

## 3. DB契約（主要テーブル・一意制約）

> 物理DDLの正: `docs/database/25_database_definition.md`（本リポジトリ側）

### 3.1 races
- UNIQUE: `(race_date, baba_code, race_no)`
- `start_time`（発走時刻）は `RaceList` を一次情報とする

### 3.2 race_entries（出走表）
- UNIQUE: `(race_id, horse_number)`
- 取得優先: `DebaTable` を主、`RaceMarkTable` を従（確定値は上書き可）
- `horse_id` 正規化が未確定のため、`horse_name` を冗長保持する

### 3.3 odds_snapshots / odds_items
- `odds_snapshots` UNIQUE: `(race_id, bet_type, snapshot_kind, odds_flg)`
- `odds_items` UNIQUE: `(odds_snapshot_id, legs, is_ordered)`
- `captured_at` は **必ず**保存する
- `odds_flg` は表示モード識別子（NULL 可）。NULL も一意キーに含める
- 同一 `race_id × bet_type × snapshot_kind × odds_flg` は **1件**のみ（最新を上書きする）

### 3.4 race_results（成績）
- UNIQUE: `(race_id, finish_position)` と `(race_id, horse_number)` を併用（安全側）
- 取得元: `RaceMarkTable`（確定値で上書き）

### 3.5 payouts（払戻）
- UNIQUE: `(race_id, bet_type, legs, is_ordered)`
- 取得元: `RefundMoneyList` を主、`RaceMarkTable` を従

### 3.6 race_changes（出走取消/除外/騎手変更など）
- 推奨 UNIQUE: `(race_id, change_type, horse_number, announced_at)`

### 3.7 raw_fetch_logs（HTTP取得ログ）
- raw_fetch_logs は **永続データに含める（任意）**（本リリースでは必須としない）
- 保存する場合の項目（任意）:
  - `url, page_type?, http_status, captured_at, sha256, storage_path, elapsed_ms?`

---

## 4. 反映順序とデータ優先順位（冪等ETL）

### 4.1 反映順序（推奨）
1. `RaceList(date,baba_code)` → `races` + `race_changes`
2. `DebaTable(race_key)` → `race_entries` + `races` 補完
3. `Odds*(race_key, snapshot_kind, odds_flg)` → `odds_snapshots` + `odds_items`
4. `RaceMarkTable(race_key)` → `race_results`（確定値で上書き）
5. `RefundMoneyList(date,baba_code)` → `payouts`

### 4.2 優先順位（衝突時）
- `races.start_time`: `RaceList`
- `race_entries.body_weight/body_weight_diff`: `RaceMarkTable`
- 天候/馬場: `RaceMarkTable`
- 払戻: `RefundMoneyList`

---

## 5. API契約（外部公開 = api-service のみ）

> **正**は `21_openapi.yaml`。本章は要点のみ（テキスト契約）。

### 5.1 認証（Bearer + JWT）
- Access Token: JWT（**短命 15分**）
- Refresh Token: JWT（**長命 30日**）
  - **HttpOnly Cookie** に保存
  - **ローテーション方式（毎回更新）**
  - **Redis で失効管理**（例: refresh の `jti` をキーに revoke / TTL 管理）

#### 5.1.1 リクエスト規約
- Access Token を使うAPI: `Authorization: Bearer <access_jwt>` を必須
- Refresh: Cookie の refresh token により実施（ボディで渡さない）
- Logout: refresh token を失効させ、Cookie を削除する
- `/scrape*` と `/scrape/schedule` は内部通信のため **無認証**

### 5.2 同期イベント（api → scraper）
api-service は **差分評価の結果を scraper-service へ反映**する。  
イベントは **冪等**でなければならず、`event_id` を必須とする。

- api-service ⇔ scraper-service 間は **認証不要**（将来のアップデートで対応予定）
- 同期ペイロードは `/scrape/*` の schema を共通利用する（送信方向は api → scraper）
- 送信先: scraper-service の control API `/control/ingest/*`
- `odds-snapshots`（`/scrape/odds-snapshots` スキーマ）  
  - 目的: 代表時点のオッズ集合を同期（`odds_snapshots` + `odds_items` を Upsert）
  - 入力の最小要件:
    - `event_id`（UUID）
    - `race_key`
    - `bet_type`
    - `snapshot_kind`
    - `captured_at`
    - `source_url`
    - `items[]`（legs/is_ordered/odds_min/odds_max/popularity?）
  - `odds_flg` は表示モード識別子（任意）。一意性は `race_key × bet_type × snapshot_kind × odds_flg` に従う
  - scraper-service は `event_id` 重複時に **同一結果**を返す（少なくとも 200/201 を維持）

> 補足: `raw_fetch_logs` は本リリースでは任意（別API化は将来）。

### 5.3 参照API（frontend / backtest / debug）
- `GET /races`（`race_date` / `baba_code` で検索、ページング対応）
- `GET /races/{race_id}/odds`（`snapshot_kind` 等でフィルタ）

### 5.4 スクレイプ制御API（手動実行/定期/同期）
- `POST /scrape/manual-tasks`（競馬場必須、日時/レース順は任意）
- `GET /scrape/schedule`（定期実行のオン/オフ状態）
- `POST /scrape/sync`（手動同期の開始）
- `GET /scrape/sync/status`（定期同期/差分同期の状態）

---

## 6. イベント契約（将来拡張のための予約）

本リリースでは **Prefect / Celery / MLflow はスコープ外**のため、外部メッセージ基盤は導入しない。  
ただし将来のパイプライン接続を容易にするため、**イベントの形（エンベロープ）を予約**する。

### 6.1 イベントエンベロープ（予約）
- `event_id`: UUID
- `event_type`: 例 `odds_snapshot.ingested`
- `occurred_at`: timestamp（JST）
- `schema_version`: int（初期 1）
- `payload`: 型別

### 6.2 代表イベント（予約）
- `odds_snapshot.ingested`
  - `race_id` / `race_key` / `snapshot_kind` / `odds_flg?` / `captured_at` / `bet_type` / `num_items`

> 予約は **後方互換**でのみ拡張する（フィールド追加は可、意味変更は不可）。

---

## 7. データ品質・破壊的変更

### 7.1 データ品質（最低限）
- `snapshot_kind` はデフォルト集合を基本とし、運用で追加可（OpenAPI は固定 enum にしない）
- `odds_min/odds_max` は正数、異常値は検知（上限閾値を運用で定義）
- `captured_at` は `races.start_time` 近傍の時間窓のみ有効（窓幅は運用契約）

### 7.2 破壊的変更
- column rename / type change / key change は原則禁止
- やむを得ない場合は **新カラム追加 → 移行 → 旧カラム廃止** の段階移行
- Decision Log に必ず記録する（`06_other_notes_and_decisions.md` 等）
