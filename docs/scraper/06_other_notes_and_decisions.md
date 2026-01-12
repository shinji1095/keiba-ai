# 06 追加観測・設計判断（メモ）

作成日: 2025-12-27（Asia/Tokyo）

---

## 1. scraper-service の実装方針（高レベル）

### 1.1 日次バッチの基本フロー（案）
1. `TodayRaceInfoTop` から当日の開催場（babaCode）を列挙
2. `RaceList(date,babaCode)` を取得し、当日のレース一覧（発走時刻/R番号）を作る
3. レースごとに監視スケジュールを作成（t_minus_60m, t_minus_30m, t_minus_20m, t_minus_10m, t_minus_5m, t_minus_1m, final）
4. 指定時刻に `Odds*` を取得し、DBへ保存（スナップショット）
5. レース終了後に `RaceMarkTable` / `RefundMoneyList` を取得し、成績・払戻を保存

### 1.2 ログ・監視（推奨）
- すべてのHTTP取得について取得結果ログ（CSV等）を残す
  - `url`, `captured_at`, `http_status`, `sha256(body)`, `elapsed_ms`
- 例外（404/5xx/定型文による欠損）は **件数とURLを集計**し、スクレイパの健全性監視に使う

---

## 2. 観測事項（A2/A4/B3/B4で更新）

### 2.1 3連系 PageName の表記揺れ
- 画面導線（PC版）では `Odds3LenFuku / Odds3LenTan` を確認した。
- 既存資料に `3Ren*` 表記が混在していたため、実装では **実取得URLをmanifestに残す**こと。

### 2.2 Internal Error の扱い
- 一部レースで `Odds3LenFuku` が Internal Error になるケースを観測した（大井 2025/12/25 6R）。
- 方針: オッズは欠損として記録し、レース確定後の `RefundMoneyList` で払戻を取得して学習可能にする。

### 2.3 払戻・成績のデータソース優先順位（確定）

- 払戻（payouts）
  - 主: `RefundMoneyList`（当日×開催場で全レース一括）
  - 従: `RaceMarkTable`（レース単位、欠損時の補助）
- 成績（race_results）
  - 主: `RaceMarkTable`
- 出馬表（race_entries）
  - 主: `DebaTable`
  - 従: `RaceMarkTable`（馬体重など「確定値」に上書きできる項目）

根拠（プロジェクト共有資料）
- `source_shared/01_known_facts.md`（RefundMoneyListの位置づけ、RaceListの変更欄）
- `source_shared/09_race_mark_table_structure.md`（成績と払戻の存在）
- `05_parsing_fixture_tdd.md`（A4/B3/B4で設計確定）

### 2.4 「開催中→確定後」移行の現実的運用（推奨）

> わからない
> - レース終了をリアルタイムに検知する公式API/イベントがあるかは未確認。

そのため、初期の scraper-service は以下の運用に寄せる。

- `RaceList` を一次情報にし、`races.start_time` を基準にスケジュールを組む
- `RaceMarkTable` は `races.start_time + 固定遅延` で取得し、少回数リトライで結果の出現を待つ
- `RefundMoneyList` は「最終レース後に1回」が基本（障害時のみ追加）

詳細は `04_scraping_requirements.md` と `source_shared/28_race_entry_result_parser_design.md` を参照。

---

## 3. 参考（共有資料一覧）

- 12_odds_time_series_and_snapshot_strategy.md
- 13_odds_flg_mapping.md
- 14_odds_pages_structure_additional.md
- 15_debatable_small_and_sp_observation.md
- 17_current_facts_and_next_actions_update.md
- 18_project_decisions_and_scope_update.md
- 19_html_fixture_collection_guide.md
- 20_parser_normalization_contracts.md
- 21_tdd_testcase_plan_for_odds_parser.md
- 23_odds_fixture_collection_and_tdd.md
- 24_project_decisions_update_20251227.md
- docs/database/25_database_definition.md
- 22_fixture_downloader_example.py
- README.md


---

## 3. C1/C2（DB/運用）で確定した設計

### 3.1 DB（PostgreSQL）

- 物理スキーマは `docs/database/25_database_definition.md` のDDLを正とする
- マイグレーションは SQL連番適用（`source_shared/29_db_migration_and_bootstrap.md`）

### 3.2 負荷制御・監視

- per-host concurrency は初期値 1（直列）
- min interval 60s + jitter（scheduled: 60〜300s、manual: 60s）

参照: `source_shared/30_load_control_and_observability.md`
