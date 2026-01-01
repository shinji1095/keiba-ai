# 07 next_actions（統合）

作成日: 2025-12-27（Asia/Tokyo）

---

## A. 調査（サイト構造/取得対象/正規化）

|ID|内容|状態|成果物|
|---|---|---|---|
|A1|Odds* 各ページの構造調査（行抽出に必要な目印）|完了|`01_site_structure.md`, `05_parsing_fixture_tdd.md`|
|A2|「開催中データ」で **7ページ（式別）** が揃う race_key を再選定し、404/5xx 等の条件整理、URLパターン確定、フォールバック条件表を作る|完了|`01_site_structure.md`（URL/分類）, `04_scraping_requirements.md`（フォールバック）, `05_parsing_fixture_tdd.md`（フィクスチャ選定）|
|A3|ワイド/複勝などの **レンジ表現オッズ**（min/max）正規化を確定する|完了|`05_parsing_fixture_tdd.md`（A3 仕様）, `02_database_design.md`（odds_min/odds_max 方針）|
|A4|払戻金を **bet_type×legs×payout** に正規化し、取得元（RefundMoneyList/RaceMarkTable）を確定する|完了|`05_parsing_fixture_tdd.md`（A4 仕様）, `02_database_design.md`（payouts 方針）, `03_data_for_prediction_and_rl.md`|

---

## B. 実装（fixture収集→TDD→パーサ）

|ID|内容|状態|備考|
|---|---|---|---|
|B1|Odds* HTMLフィクスチャ収集 → TDD用テストケース化|設計完了（実収集は未）|収集計画/命名/manifest仕様を `05_parsing_fixture_tdd.md` と `source_shared/19_html_fixture_collection_guide.md`, `source_shared/23_odds_fixture_collection_and_tdd.md` に確定。実収集はA2の正常系/異常系 race_key から開始|
|B2|Oddsパーサ（bet_type ごとの正規化）|設計完了（実装は未）|TDDテストマトリクスと「固定する表示モード（odds_flg）」を `05_parsing_fixture_tdd.md` に確定。テスト計画は `source_shared/21_tdd_testcase_plan_for_odds_parser.md` を更新|
|B3|RefundMoneyList パーサ（払戻正規化）|設計完了（実装は未）|状態機械（継続行）・式別名マッピング・legs/payout/popularity の抽出規則を確定。`source_shared/27_refund_money_list_parser_design.md` と `source_shared/20_parser_normalization_contracts.md`, `05_parsing_fixture_tdd.md` を更新|
|B4|レース/出走表/成績の正規化（races, entries, results, changes）|設計完了（実装は未）|RaceList/DebaTable/RaceMarkTable のパース契約とDB反映（upsert順序・優先順位）を確定。`source_shared/28_race_entry_result_parser_design.md` と `02_database_design.md`, `docs/database/25_database_definition.md`, `source_shared/20_parser_normalization_contracts.md` を更新|

---

## C. DB/運用

|ID|内容|状態|備考|
|---|---|---|---|
|C1|DBスキーマ初期実装（PostgreSQL）|設計完了|`02_database_design.md` と `docs/database/25_database_definition.md` を元にマイグレーション|
|C2|負荷制御・監視（HTTPログ/再試行/並列数）|設計完了|`04_scraping_requirements.md`, `source_shared/11_scraping_strategy_and_load_control.md`|


### C1（DBスキーマ初期実装）設計で確定したもの

- 物理DB: PostgreSQL
- 方式: SQLマイグレーション（`migrations/sql/0001_init.sql` から順次適用）
- 主要テーブル: `venues, races, race_entries, odds_snapshots, odds_items, race_results, payouts, race_changes`（raw_fetch_logs は任意）
- `bet_type` は `tansho/fukusho/wakuren/wakutan/umaren/umatan/wide/sanrenpuku/sanrentan` を採用（`tanfuku` の統合表現は使わない）
- Upsertキーとユニーク制約は `docs/database/25_database_definition.md` に統一
- Raw HTML はDBに格納せず、**ファイル保存**で参照（必要なら `raw_fetch_logs.storage_path` に保存）

参照: `02_database_design.md`, `docs/database/25_database_definition.md`, `source_shared/29_db_migration_and_bootstrap.md`

### C2（負荷制御・監視）設計で確定したもの

- 取得は **ホスト単位で直列（並列=1）** を初期値とし、必要なら段階的に緩和
- 1リクエストごとに最小待機（例: 1.5s）＋ジッタを入れる
- 再試行は **限定的**（ネットワーク例外/一部5xxのみ、最大3回、指数バックオフ）
- すべてのHTTP取得について `raw_fetch_logs` を **記録してもよい**（成功/失敗を問わない）
- 監視指標（最低限）: 成功率、HTTPステータス分布、平均/95pレイテンシ、リトライ回数

参照: `04_scraping_requirements.md`, `source_shared/11_scraping_strategy_and_load_control.md`, `source_shared/30_load_control_and_observability.md`
