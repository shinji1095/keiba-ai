# 04 スクレイピング要件（取得対象・スケジュール・例外・負荷）

作成日: 2025-12-27（Asia/Tokyo）  
更新日: 2025-12-31（Asia/Tokyo）

更新履歴
- 2025-12-27: 初版作成。
- 2025-12-28: 実行モード（常駐/手動）とタスク仕様を追記。
- 2025-12-28: 手動実行タスクの指定項目を明記。
- 2025-12-28: api-server との定期同期、手動同期、差分同期の方針を追記。
- 2025-12-28: 差分同期の判定キーと同期対象を明記。
- 2025-12-28: 手動実行/定期実行/同期のAPI契約を追記。
- 2025-12-28: 定期実行のオン/オフ状態をfrontendから参照できる旨を明記。
- 2025-12-28: トリガ駆動の実行方式（plan固定/日付更新なし）を明記。
- 2025-12-28: cronコンテナによる定期実行/手動実行の制御、保存/同期方針を更新。
- 2025-12-31: Pi 側 control API の認証不要方針を明記。
- 2025-12-31: 同期方向を api→scraper に変更し、差分評価のトリガを更新。
---

## 1. 実行モードとタスク

- scraper-service は **常時起動の control API** を提供し、api-service からの手動実行を受け付ける
- Pi 側に cron コンテナを配置し、定期実行は cron コンテナが scraper-service の control API を呼び出す
- api-service から cron コンテナに対し定期実行の on/off と baba_codes を制御する
- 定期実行は複数競馬場（baba_codes）を指定可能
- race_date はトリガごとに決定する（未指定は当日JST）
- **起動時に race_date を固定した plan を作成し、無限ループする方式は採用しない**
- スクレイピング情報（raw_html/ログ/正規化データ）は Pi 側で保存する
- PC/Pi 間は **api-service からの要求をトリガ**として差分を評価し、**api → scraper** 方向に定期同期する（既定: 1日おき）
- 定期実行のオン/オフ状態は frontend から参照できる

### 1.1 同期と差分管理

- 差分評価対象: `/scrape/*` に相当する正規化データ と `raw_fetch_logs`
- 同期頻度（既定）: 1日おき（JST）
- 同期方向: api → scraper（api-service 起点）
- 差分判定（最小構成）:
  - 差分キー: `scope_key + page_type + snapshot_kind + odds_flg`
  - scope_key:
    - TodayRaceInfoTop: `race_date`
    - RaceList / RefundMoneyList: `race_date + baba_code`
    - DebaTable / RaceMarkTable / Odds*: `race_date + baba_code + race_no`
  - fingerprint: `raw_fetch_logs.sha256`（HTML 保存時はこれを優先）
- 同期ルール: fingerprint が前回と同一なら同期をスキップし、差分のみを api → scraper 方向で反映する
- 正規化データの差分キー（参考）:
  - races: `race_key`
  - race_entries: `race_key + horse_number`
  - odds_snapshots: `race_key + bet_type + snapshot_kind + odds_flg`
  - race_results: `race_key + finish_position`（併用で `horse_number` も許容）
  - payouts: `race_key + bet_type + legs + is_ordered`
  - race_changes: `race_key + change_type + captured_at`

### 1.2 Control API（frontend からの操作/参照）

- 手動実行タスク: `POST /scrape/manual-tasks`
  - 指定項目: `baba_code`（必須）, `race_date`（任意, 未指定は当日JST）, `race_no`（任意）
  - api-service は受理後に scraper-service の control API へトリガを転送する
- 定期実行の状態確認: `GET /scrape/schedule`
  - frontend は定期実行のオン/オフ状態を参照できる
- 手動同期のトリガ: `POST /scrape/sync`
  - api-service が scraper への同期要求を発行し、差分評価を開始する
- 定期同期/差分同期の状態確認: `GET /scrape/sync/status`

### 1.3 Pi 側 Control API（cron 制御 / 手動実行）

- 受信元: api-service のみ（PC→Pi）
- 認証: 不要（PC 経由の内部通信を想定）
- 定期実行の制御: `POST /control/schedule`
  - `enabled`: boolean
  - `baba_codes`: int[]（複数指定可）
- 手動実行: `POST /control/scrape`
  - 指定項目: `baba_code`（必須）, `race_date`（任意）, `race_no`（任意）
- cron コンテナは `/control/schedule` の状態に従って実行する

## 2. 取得対象（最低限）

### 2.1 開催場トップ（当日開催一覧）
- `TodayRaceInfoTop`
  - 当日の開催場（`k_babaCode`）の導線
  - 前日/翌日などの導線（取得可能なら）

### 2.2 レース一覧（当日・開催場単位）
- `RaceList?k_raceDate=...&k_babaCode=...`
  - 発走時刻 / R番号 / 距離 / 天候 / 馬場 / 頭数 / 変更情報
  - 各レースへの導線（出馬表・成績・オッズ）

### 2.3 レース単位（race_key）
- 出馬表: `DebaTable`
- 成績: `RaceMarkTable`
- オッズ（7ページ）: `Odds*`（`01_site_structure.md` を参照）

### 2.4 当日払戻金（日付×開催場）
- `RefundMoneyList?k_raceDate=...&k_babaCode=...`
  - 1ページで当日の全レースの払戻が取れる（**高効率**）
  - 払戻は `payouts` テーブル（bet_type×legs）へ正規化する（`05_parsing_fixture_tdd.md`, `source_shared/20_parser_normalization_contracts.md` 参照）

---

## 3. 取得スケジュール（推奨）

前提: スケジューリングは **トリガ駆動**で行い、scraper は **実行時点で必要な取得**を行う。  
代表オッズ（最終/5分前/1分前）は **発走時刻基準**でトリガを組む（`RaceList` の発走時刻を一次情報とする）。

### 3.1 RaceList（当日・開催場単位）

- 1回目: 当日開始時（例: 朝）に全開催場を取得
- 以降: 発走時刻変更/取消等を拾うため、開催中は **低頻度で再取得**（例: 10〜30分間隔、もしくは「直近レースが始まる前だけ」）

> わからない
> - 発走時刻が当日にどの程度変更されるかは未確認。再取得頻度は実測で調整する。

### 3.2 DebaTable（出馬表）

- 原則: 各レースで **最低1回**
- 推奨: `t_start - 60〜20分` の間に取得（出走取消/騎手変更が反映される可能性を考慮）
- 追加取得（任意）: 変更が多い開催では `t_start - 10分` 付近に再取得（負荷とのトレードオフ）

### 3.3 Odds*（代表オッズ）

- t-5m: 発走5分前
- t-1m: 発走1分前
- last: 締切後〜発走直前（サイト更新タイミングに依存）

> 注意
> - 締切・発走・更新が完全同期しない可能性があるため、`captured_at`（取得時刻）を必ず保存し、後段で選別する。

### 3.4 RaceMarkTable（成績）

- 取得タイミングの考え方
  - レース終了をイベントで検知できない場合、`t_start` からの **固定遅延 + 少回数リトライ**で現実運用する。

推奨（最小）
- 1回目: `t_start + 10〜20分`（距離/馬場により変動）
- リトライ: 2〜4回（例: 5分間隔）
- 上限: `t_start + 60分` を超えたら欠損扱い

### 3.5 RefundMoneyList（払戻）

- 1ページで当日全レースの払戻が取れるため、**開催場×日付で最小回数**にする。

推奨（最小）
- 最終レース後（`RaceList` の最終発走時刻 + 90分` 程度）に 1回取得
- 欠損の場合のみ、数回リトライ（例: 10分間隔で2回）

> 推測ですが
> - レースごとにページ内容が順次更新される可能性があるため、「当日途中での途中取得」は障害時のフォールバックとして扱い、基本は最終取得に寄せる。

---

## 4. 例外・エラー分類とフォールバック（A2）

### 4.1 エラー分類（推奨）
|分類|主な判定|意味|推奨対応|
|---|---|---|---|
|ソフト欠損|HTTP 200 + 定型文（例: オッズなし）|発売なし/対象外|欠損として記録（リトライしない）|
|一時的不可|HTTP 200 + 定型文（例: 表示できません）|一時障害の可能性|短いバックオフで少回数リトライ|
|サーバエラー|HTTP 5xx / Internal Error|サーバ側問題|欠損として記録（ログ必須）。必要なら別ページで補完|
|URL不整合|HTTP 404|race_key/URL生成ミス or 仕様変更|URL生成を再確認→直らなければ欠損|

### 4.2 フォールバック順（推奨）
1. PC版（`www.keiba.go.jp/KeibaWeb/...`）を正として取得
2. PC版が取得不能（404/5xx/パース不能）の場合
   - （候補）SP版（`sp.keiba.go.jp/KeibaWebSP/...`）を試す
     - ただし、時間帯によって導線が出ない観測があるため、安定性は **未確認**（わからない）
3. それでもダメなら欠損として記録し、後段で学習から除外/マスクする

---

## 5. 負荷制御（最重要）

- 取得頻度は **最小**（代表時点のみ）に絞る
- 並列数を抑える（1〜数スレッド程度から開始）
- 失敗時のリトライは **少回数**（指数バックオフ）
- Raw層ログ（url/http_status/sha256/fetched_at）を残し、原因調査を可能にする

---

## 6. フィクスチャ収集方針（TDD用）

- `RaceList / DebaTable / RaceMarkTable / RefundMoneyList / Odds*` を保存してパーサをTDDで固定する。
- 収集は「開催中の日付」で行う（オッズが出ない日付では検証できない）。
- **取得計画（manifest.yml）** と **取得結果ログ（manifest_log.csv）** を必須とする。
  - 取得計画: URL / PageName / odds_flg（指定するなら） / 出力パス / 期待HTTP（異常系のみ）
  - 取得結果ログ: url / sha256 / fetched_at / http_status / content_type / content_encoding
  - 仕様は `05_parsing_fixture_tdd.md` 7章に確定。

### 6.1 odds_flg と表示モード

- Odds* は `odds_flg` によって「馬番順/人気順」「枠マトリクス/ランキング」など表示が変わる。
- 初期のTDDでは **固定する表示モード** を 1つ決めて安定化し、後から代替モードの fixtures を追加して頑健性を上げる。
  - 確定済み: `OddsTanFuku(4/5)`, `OddsWakuLenFukuTan(6/5)`
  - 未確定: `OddsUmLenFuku`, `OddsUmLenTan`, `OddsWide`, `Odds3LenFuku`, `Odds3LenTan`（現時点ではわからない）
  - 棚卸し方法: fixtures のHTMLからタブ/リンクの `href` を解析して採番（ブラウザ手作業に依存しない）

### 6.2 取得時のHTTP要件（推奨）

- `User-Agent` を設定する（requests等のデフォルトUAのままにしない）
- `Accept-Language: ja` を付け、表示揺れのリスクを下げる
- gzip等はクライアントが透過解凍してよい（TDDは「パース入力としてのHTML」が目的）
- リトライは **少回数**（例: 0〜2回）にし、指数バックオフを入れる

---

## 7. コンプライアンス

- `keiba.go.jp` の利用規約・著作権表記に従うこと
- 過度なアクセスはブロックされ得るため、頻度・並列は慎重に設計する


---

## 8. C2（負荷制御・監視）— 要件として固定

### 8.1 負荷制御（固定）

- ホスト単位の並列: 初期値 **1**
- 連続リクエストの最小間隔: **1.5秒以上**（+ジッタ）
- 失敗時の再試行: 最大3回、指数バックオフ（ネットワーク例外/一部5xxのみ）
- 同一URLの連打禁止: スケジューラが抑止（直近N秒の再取得を避ける）

### 8.2 取得ログ（固定）

- すべての取得について `raw_fetch_logs` を必ず記録する（成功/失敗を問わない）
- HTMLを保存する場合:
  - `sha256` を採番に使いファイル保存（例: `raw_html/YYYY/MM/DD/{page_type}/{sha256}.html`）
  - DBには `storage_path` のみ保存する

### 8.3 監視指標（最低限）

- 成功率（2xx率）
- HTTPステータス分布（2xx/3xx/4xx/5xx）
- レイテンシ（平均/95p）
- リトライ回数・最終失敗件数

参照: `source_shared/30_load_control_and_observability.md`
