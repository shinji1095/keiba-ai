# Glossary（用語集）

## 1. 基本用語
- **api-service**: PC 側の API/DB。Pi から pull した正規化データの取り込みと差分同期の判定主体。
- **scraper-service**: Pi 側のスクレイピング実行ノード。取得結果と最新データの保管先（同期の正）。
- **scrape API**: api-service の `/scrape/*`。正規化データの受理口。
- **control API**: scraper-service の `/control/*`。手動実行/定期実行の制御と同期データ提供口。
- **ingest**: scraper-service から api-service へデータを取り込み反映すること。

## 2. 差分同期/スケジュール
- **race_key**: `race_date + baba_code + race_no` で構成するレース識別子。
- **scope_key**: 差分判定の範囲キー。`race_date` 単位または `race_date + baba_code (+ race_no)`。
- **diff_key**: `scope_key + page_type + snapshot_kind + odds_flg` で構成する差分判定キー。
- **fingerprint**: 差分判定に使う `sha256`。正規化データ（payload）から算出し、前回と同一なら同期を省略する。
- **sync_state**: 差分キーと fingerprint を保持する永続状態（同期の判定に利用）。
- **interval_days**: 定期同期の実行間隔（日数、JST 日付境界基準）。
- **diff_enabled**: 差分判定を有効化するフラグ。

## 3. 取得データ/ログ
- **snapshot**: ある時点の取得データ。例: odds snapshot（`captured_at` と `snapshot_kind` を持つ）。
- **snapshot_kind**: 取得タイミングのラベル（例: `t_minus_5m`, `final`）。
- **odds_flg**: 同一オッズ種別内の条件差を識別するフラグ（存在しない場合は `null`）。
