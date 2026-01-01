# Glossary（用語集）

## 1. 基本用語
- **api-service**: PC 側の API/DB。正規化データの受理と差分同期の判定主体。
- **scraper-service**: Pi 側のスクレイピング実行ノード。取得結果や Raw ログの保管先。
- **scrape API**: api-service の `/scrape/*`。正規化データの受理口。
- **control API**: scraper-service の `/control/*`。同期データ受け口や手動実行のトリガ。
- **ingest**: api-service から scraper-service へ差分ペイロードを送信すること。

## 2. 差分同期/スケジュール
- **race_key**: `race_date + baba_code + race_no` で構成するレース識別子。
- **scope_key**: 差分判定の範囲キー。`race_date` 単位または `race_date + baba_code (+ race_no)`。
- **diff_key**: `scope_key + page_type + snapshot_kind + odds_flg` で構成する差分判定キー。
- **fingerprint**: 差分判定に使う `sha256`。原則は `raw_fetch_logs.sha256` を使い、ログがない場合は正規化データの hash を代替として使う。
- **sync_state**: 差分キーと fingerprint を保持する永続状態（同期の判定に利用）。
- **interval_days**: 定期同期の実行間隔（日数、JST 日付境界基準）。
- **diff_enabled**: 差分判定を有効化するフラグ。

## 3. 取得データ/ログ
- **snapshot**: ある時点の取得データ。例: odds snapshot（`captured_at` と `snapshot_kind` を持つ）。
- **snapshot_kind**: 取得タイミングのラベル（例: `t_minus_5m`, `final`）。
- **odds_flg**: 同一オッズ種別内の条件差を識別するフラグ（存在しない場合は `null`）。
- **raw_fetch_log**: 取得時の URL/HTTP ステータス/sha256/時刻などを記録した Raw ログ。
