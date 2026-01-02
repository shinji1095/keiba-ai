更新履歴
- 2025-12-28: 初版作成。
- 2025-12-28: API/フロントエンドの定義済み・追加テスト要件を追記。
- 2025-12-28: テスト分類と追加実装の反映。
- 2025-12-28: scraper の定期同期/差分同期テスト要件を追加。
- 2025-12-28: 手動実行タスク/定期実行状態/同期APIのテスト要件を追加。
- 2025-12-28: cronコンテナ運用と同期頻度の変更を反映。
- 2025-12-31: 同期方向を api→scraper に更新。
- 2026-01-01: 同期スケジューラ/cron/フロントエンド同期テスト要件を追加。
- 2026-01-01: 差分同期の判定主体を api-service に更新。
- 2026-01-01: TR-014 の fingerprint 要件を更新（payload sha256）。
- 2026-01-01: 即時転送モードのテスト要件を追加。
- 2026-01-02: pull 同期の実装/テスト反映に伴い、同期要件の実装状況を更新。
- 2026-01-02: 同期定義を Pi 最新/PC pull に更新し、即時転送モード要件を廃止。

# テスト要件

## 目的
- サービス間通信と主要 API 契約のテスト要件を定義する。
- 既存の仕様・運用ドキュメントにトレースできる状態を維持する。

## リスク一覧（安全性・行政申請重視）
- RISK-001: データ整合性の損失（重複・欠損）。
- RISK-002: 保護エンドポイントへの不正アクセス。
- RISK-003: サービス可用性低下または検知遅延。
- RISK-004: PC と Pi のネットワーク境界違反。

## テスト要件

### TR-001: PC から scraper への疎通（health）
- 要件ID: TR-001
- 要件名: PC→scraper health check
- 要件の説明: PC から scraper の health エンドポイントへ到達でき、`{"status":"ok"}` を受信できること。
- 根拠となる仕様・要件ID: docs/10_architecture.md#3, docs/70_operations_runbook.md#1
- 関連リスクID: RISK-003, RISK-004
- テスト観点: 正常系
- テスト分類: システムテスト
- 対象機能・モジュール: scraper-service health endpoint, PC network path
- 実装状況: 既存テストあり（services/scraper/tests/test_scraper_health_connection.py）

### TR-002: client_credentials トークン（将来予約）
- 要件ID: TR-002
- 要件名: client_credentials トークン（将来予約）
- 要件の説明: `POST /auth/token` は将来の認証方式（mTLS/OAuth）に備えた予約で、現行の api-service ⇔ scraper-service は無認証。現時点では必須要件ではない。
- 根拠となる仕様・要件ID: docs/21_openapi.yaml:/auth/token, docs/20_data_contracts.md#5.2
- 関連リスクID: RISK-002
- テスト観点: 将来予約
- テスト分類: 保留
- 対象機能・モジュール: api-service auth, OAuth client store
- 実装状況: 将来予約（現行は必須でない）

### TR-003: 収集イベント投入（odds snapshots）
- 要件ID: TR-003
- 要件名: オッズスナップショット投入イベント
- 要件の説明: `POST /scrape/odds-snapshots` が最小ペイロードを受理し、期待どおりに永続化すること。
- 根拠となる仕様・要件ID: docs/20_data_contracts.md#5.2
- 関連リスクID: RISK-001
- テスト観点: 正常系
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service scrape routes, DB upsert
- 実装状況: 既存テストあり（services/api/tests/test_scrape_and_races.py）

### TR-004: 自然キーによる冪等性
- 要件ID: TR-004
- 要件名: 自然キーの冪等投入
- 要件の説明: 同一の自然キー（例: `race_key`, `race_id × bet_type × snapshot_kind × odds_flg` など）を再送しても成功レスポンスとなり、重複レコードを生成しないこと。
- 根拠となる仕様・要件ID: docs/20_data_contracts.md#1.4, docs/20_data_contracts.md#3
- 関連リスクID: RISK-001
- テスト観点: 正常系／境界値
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service scrape routes, DB constraints
- 実装状況: 既存テストあり（services/api/tests/test_scrape_and_races.py）

### TR-005: API health エンドポイント
- 要件ID: TR-005
- 要件名: API health check
- 要件の説明: `GET /health` が `ok` を返し、監視に利用できること。
- 根拠となる仕様・要件ID: docs/21_openapi.yaml:/health, docs/70_operations_runbook.md#1
- 関連リスクID: RISK-003
- テスト観点: 正常系
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service health route
- 実装状況: 既存テストあり（services/api/tests/test_health.py）

### TR-006: ユーザー認証フロー（login/refresh/logout）
- 要件ID: TR-006
- 要件名: ユーザー認証フロー
- 要件の説明: `POST /auth/login` で access token を取得し、`/auth/refresh` で refresh token がローテーションされ、`/auth/logout` で Cookie が無効化されること。
- 根拠となる仕様・要件ID: docs/20_data_contracts.md#5.1.1, docs/21_openapi.yaml:/auth/login
- 関連リスクID: RISK-002
- テスト観点: 正常系
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service auth
- 実装状況: 既存テストあり（services/api/tests/test_auth_flow.py）

### TR-007: OAuth client 作成（管理者）
- 要件ID: TR-007
- 要件名: 管理者による OAuth client 作成
- 要件の説明: 管理者権限で `POST /admin/oauth-clients` を実行し、`client_id` / `client_secret` を取得できること。
- 根拠となる仕様・要件ID: docs/21_openapi.yaml:/admin/oauth-clients, services/frontend/README.md#使い方
- 関連リスクID: RISK-002
- テスト観点: 正常系
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service admin oauth clients
- 実装状況: 既存テストあり（services/api/tests/test_oauth_client_and_scope.py）

### TR-008: /scrape の無認証受付（内部通信）
- 要件ID: TR-008
- 要件名: /scrape は無認証で受理する
- 要件の説明: 認証なしで `POST /scrape/*` が受理されること（ペイロード検証は行う）。
- 根拠となる仕様・要件ID: docs/20_data_contracts.md#5.1.1, docs/21_openapi.yaml:/scrape/*
- 関連リスクID: RISK-004
- テスト観点: 正常系
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service scrape routes
- 実装状況: 既存テストあり（services/api/tests/test_oauth_client_and_scope.py）

### TR-009: venues 参照 API
- 要件ID: TR-009
- 要件名: 会場一覧取得
- 要件の説明: `GET /venues` が一覧を返し、空データ時も安定して応答すること。
- 根拠となる仕様・要件ID: docs/21_openapi.yaml:/venues
- 関連リスクID: RISK-003
- テスト観点: 正常系／境界値
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service venues
- 実装状況: 既存テストあり（services/api/tests/test_scrape_and_races.py）

### TR-010: races 一覧 API（検索・ページング）
- 要件ID: TR-010
- 要件名: レース一覧取得と絞り込み
- 要件の説明: `GET /races` が `race_date` / `baba_code` で検索でき、ページングが正しく動作すること。
- 根拠となる仕様・要件ID: docs/20_data_contracts.md#5.3, docs/21_openapi.yaml:/races
- 関連リスクID: RISK-001
- テスト観点: 正常系／境界値
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service races
- 実装状況: 既存テストあり（services/api/tests/test_scrape_and_races.py）

### TR-011: race 詳細 API
- 要件ID: TR-011
- 要件名: レース詳細の参照
- 要件の説明: `GET /races/{id}` と関連リソース（entries/odds/results/payouts）が整合した内容を返すこと。
- 根拠となる仕様・要件ID: docs/20_data_contracts.md#5.3, docs/21_openapi.yaml:/races/{race_id}
- 関連リスクID: RISK-001
- テスト観点: 正常系／境界値
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service races
- 実装状況: 既存テストあり（services/api/tests/test_scrape_and_races.py）

### TR-012: 収集イベント投入（races/entries/results/payouts/changes）
- 要件ID: TR-012
- 要件名: 収集イベント投入（odds 以外）
- 要件の説明: `/scrape/races` `/scrape/race-entries` `/scrape/race-results` `/scrape/payouts` が最小ペイロードで upsert されること。`/scrape/race-changes` は将来予約（本リリースはスコープ外）。
- 根拠となる仕様・要件ID: docs/20_data_contracts.md#3, docs/20_data_contracts.md#4, docs/21_openapi.yaml:/scrape/*
- 関連リスクID: RISK-001
- テスト観点: 正常系
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service scrape routes, DB upsert
- 実装状況: 既存テストあり（services/api/tests/test_scrape_and_races.py）

### TR-013: api 定期同期の判定
- 要件ID: TR-013
- 要件名: 定期同期の判定（JST）
- 要件の説明: api-service が1日おき（JST）に実行可否を制御でき、同日内は不要な同期を抑止し、日付跨ぎで同期が許可されること。
- 根拠となる仕様・要件ID: docs/scraper/04_scraping_requirements.md#1.1
- 関連リスクID: RISK-001, RISK-003
- テスト観点: 正常系／境界値
- テスト分類: 単体テスト
- 対象機能・モジュール: api-service sync policy
- 実装状況: 追加テストあり（services/api/tests/test_sync_policy.py）

### TR-014: api 差分同期の判定
- 要件ID: TR-014
- 要件名: 差分キーとfingerprint判定
- 要件の説明: api-service が scope_key と page_type 等で差分キーを構成し、fingerprint（payload sha256）で前回と同一なら同期をスキップできること。
- 根拠となる仕様・要件ID: docs/scraper/04_scraping_requirements.md#1.1
- 関連リスクID: RISK-001
- テスト観点: 正常系／異常系
- テスト分類: 単体テスト
- 対象機能・モジュール: api-service sync diff
- 実装状況: 追加テストあり（services/api/tests/test_sync_diff.py）

### TR-015: 手動実行タスクAPI
- 要件ID: TR-015
- 要件名: 手動実行タスクの受付
- 要件の説明: `POST /scrape/manual-tasks` が最小入力で受理され、タスクIDが返ること。
- 根拠となる仕様・要件ID: docs/scraper/04_scraping_requirements.md#1.2, docs/21_openapi.yaml:/scrape/manual-tasks
- 関連リスクID: RISK-003
- テスト観点: 正常系
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service scrape control
- 実装状況: 追加テストあり（services/api/tests/test_scrape_control.py）

### TR-016: 定期実行状態API
- 要件ID: TR-016
- 要件名: 定期実行の状態参照（複数競馬場）
- 要件の説明: `GET /scrape/schedule` がオン/オフ状態と `baba_codes` を返すこと。
- 根拠となる仕様・要件ID: docs/scraper/04_scraping_requirements.md#1.2, docs/21_openapi.yaml:/scrape/schedule
- 関連リスクID: RISK-003
- テスト観点: 正常系
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service scrape control
- 実装状況: 追加テストあり（services/api/tests/test_scrape_control.py）

### TR-016B: 定期実行設定API
- 要件ID: TR-016B
- 要件名: 定期実行設定の更新
- 要件の説明: `POST /scrape/schedule` が `enabled` と `baba_codes` を受理し、更新結果を返すこと。
- 根拠となる仕様・要件ID: docs/scraper/04_scraping_requirements.md#1.2, docs/21_openapi.yaml:/scrape/schedule
- 関連リスクID: RISK-003
- テスト観点: 正常系／異常系
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service scrape control
- 実装状況: 追加テストあり（services/api/tests/test_scrape_control.py）

### TR-017: 同期トリガAPI
- 要件ID: TR-017
- 要件名: 手動同期の開始
- 要件の説明: `POST /scrape/sync` が api-service 起点の pull 同期要求を受理し、scraper-service からの取得と差分評価を開始すること。
- 根拠となる仕様・要件ID: docs/scraper/04_scraping_requirements.md#1.2, docs/21_openapi.yaml:/scrape/sync
- 関連リスクID: RISK-003
- テスト観点: 正常系
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service scrape sync
- 実装状況: 追加テストあり（services/api/tests/test_scrape_control.py）

### TR-018: 同期状態API
- 要件ID: TR-018
- 要件名: 定期同期/差分同期の状態参照
- 要件の説明: `GET /scrape/sync/status` が Pi → PC pull 同期の状態（1日おき/差分）を返すこと。
- 根拠となる仕様・要件ID: docs/scraper/04_scraping_requirements.md#1.2, docs/21_openapi.yaml:/scrape/sync/status
- 関連リスクID: RISK-003
- テスト観点: 正常系
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service scrape sync
- 実装状況: 未対応（pull 同期の実装/テスト未追加）

### TR-019: cron コンテナによる定期実行トリガ
- 要件ID: TR-019
- 要件名: cron→scraper の定期実行制御
- 要件の説明: cron コンテナが `GET /control/schedule` の結果に従い、`enabled=true` の場合は `scraper_service.cli scrape scheduled` を `baba_codes` 指定で起動し、`enabled=false` の場合は実行しないこと。
- 根拠となる仕様・要件ID: docs/scraper/04_scraping_requirements.md#1.3, docs/10_architecture.md#3, docs/70_operations_runbook.md#1
- 関連リスクID: RISK-003
- テスト観点: 正常系／異常系
- テスト分類: システムテスト
- 対象機能・モジュール: scraper-cron, scraper-service control API
- 実装状況: 追加テストあり（services/scraper/tests/test_cron_run.py）

### TR-020: scraper→api 同期データ取り込み
- 要件ID: TR-020
- 要件名: Pi から PC への同期取り込み
- 要件の説明: api-service が scraper-service から差分ペイロードを pull し、PC 側に反映されること。
- 根拠となる仕様・要件ID: docs/10_architecture.md#3, docs/20_data_contracts.md#5.2
- 関連リスクID: RISK-001, RISK-004
- テスト観点: 正常系
- テスト分類: システムテスト
- 対象機能・モジュール: api-service sync runner, scraper-service sync export
- 実装状況: 追加テストあり（services/api/tests/test_scrape_control.py, services/api/tests/test_sync_integration.py）

### TR-021: 同期スケジュール設定API
- 要件ID: TR-021
- 要件名: 同期スケジュール更新
- 要件の説明: `POST /scrape/sync/schedule` が `enabled`/`interval_days` を受理し、`GET /scrape/sync/status` に反映されること。
- 根拠となる仕様・要件ID: docs/scraper/04_scraping_requirements.md#1.1, docs/21_openapi.yaml:/scrape/sync/schedule
- 関連リスクID: RISK-001, RISK-003
- テスト観点: 正常系／境界値
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service scrape sync schedule
- 実装状況: 追加テストあり（services/api/tests/test_scrape_control.py）

### TR-022: 同期スケジュール判定（JST 1日おき）
- 要件ID: TR-022
- 要件名: 定期同期の判定ロジック
- 要件の説明: JST 日付跨ぎを基準に 1日おき（interval_days）で実行判定し、同日内は不要な同期を抑止できること。
- 根拠となる仕様・要件ID: docs/scraper/04_scraping_requirements.md#1.1
- 関連リスクID: RISK-001, RISK-003
- テスト観点: 正常系／境界値
- テスト分類: 単体テスト
- 対象機能・モジュール: api-service sync schedule policy
- 実装状況: 追加テストあり（services/api/tests/test_sync_policy.py）

### TR-023: 同期結果の成功/失敗状態
- 要件ID: TR-023
- 要件名: 同期結果の状態保持
- 要件の説明: `GET /scrape/sync/status` が直近の成功/失敗/スキップ状態と理由を返すこと。
- 根拠となる仕様・要件ID: docs/scraper/04_scraping_requirements.md#1.1, docs/21_openapi.yaml:/scrape/sync/status
- 関連リスクID: RISK-001, RISK-003
- テスト観点: 正常系／異常系
- テスト分類: 単体テスト
- 対象機能・モジュール: api-service scrape sync status
- 実装状況: 追加テストあり（services/api/tests/test_scrape_control.py）

### TR-024: api-sync cron 単体
- 要件ID: TR-024
- 要件名: cron コンテナの実行制御
- 要件の説明: api-sync cron が API URL 未設定時はエラー終了し、API から 4xx/5xx が返った場合に失敗扱いとなること。
- 根拠となる仕様・要件ID: docs/70_operations_runbook.md#1
- 関連リスクID: RISK-003
- テスト観点: 正常系／異常系
- テスト分類: 単体テスト
- 対象機能・モジュール: api-sync cron script
- 実装状況: 追加テストあり（services/api/tests/test_sync_cron.py）

### TR-025: api-sync cron → api 連携
- 要件ID: TR-025
- 要件名: cron からの同期トリガ
- 要件の説明: api-sync cron が `POST /scrape/sync/scheduled` を呼び出し、API 側が受理できること。
- 根拠となる仕様・要件ID: docs/21_openapi.yaml:/scrape/sync/scheduled, docs/70_operations_runbook.md#1
- 関連リスクID: RISK-003
- テスト観点: 正常系
- テスト分類: 結合テスト
- 対象機能・モジュール: api-sync cron, api-service scrape sync
- 実装状況: 追加テストあり（services/api/tests/test_sync_cron.py）

### TR-026: フロントエンド同期UI（単体）
- 要件ID: TR-026
- 要件名: 同期UIの操作
- 要件の説明: 同期の有効/無効と interval_days を変更し、API 呼び出しペイロードが期待どおりに組み立てられること。
- 根拠となる仕様・要件ID: docs/scraper/04_scraping_requirements.md#1.1
- 関連リスクID: RISK-003
- テスト観点: 正常系／境界値
- テスト分類: 単体テスト
- 対象機能・モジュール: frontend sync settings
- 実装状況: 追加テストあり（services/frontend/src/features/scrape/SyncControlCard.test.tsx）

### TR-027: フロントエンド同期UI（API連携）
- 要件ID: TR-027
- 要件名: 同期ステータス表示と手動同期
- 要件の説明: frontend が `GET /scrape/sync/status` を表示し、手動同期（`POST /scrape/sync`）を実行できること。
- 根拠となる仕様・要件ID: docs/scraper/04_scraping_requirements.md#1.2, docs/21_openapi.yaml:/scrape/sync
- 関連リスクID: RISK-003
- テスト観点: 正常系
- テスト分類: システムテスト
- 対象機能・モジュール: frontend sync console, api-service scrape sync
- 実装状況: 追加テストあり（services/frontend/tests/e2e/ui_flows.spec.ts）

### TR-028: Pi → PC 同期連携
- 要件ID: TR-028
- 要件名: 同期ペイロードの pull 取得
- 要件の説明: api-service が scraper control API（/control/export/*）へリクエストし、同期データを受理できること。
- 根拠となる仕様・要件ID: docs/20_data_contracts.md#5.2
- 関連リスクID: RISK-001, RISK-004
- テスト観点: 正常系
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service scrape sync, scraper-service control export
- 実装状況: 追加テストあり（services/api/tests/test_sync_integration.py）

### TR-029: scraper 同期提供の永続化
- 要件ID: TR-029
- 要件名: 同期データ提供の読み出し
- 要件の説明: scraper-service が Pi 側に保存した正規化データを pull 要求で返却できること。
- 根拠となる仕様・要件ID: docs/20_data_contracts.md#5.2, docs/10_architecture.md#3
- 関連リスクID: RISK-001
- テスト観点: 正常系
- テスト分類: 単体テスト
- 対象機能・モジュール: scraper-service sync export
- 実装状況: 追加テストあり（services/scraper/tests/test_ingest_store.py）

### TR-101: ログイン画面（UI/E2E）
- 要件ID: TR-101
- 要件名: ログイン画面の基本フロー
- 要件の説明: `/login` で認証に成功した場合に遷移し、失敗時にエラーメッセージが表示されること。
- 根拠となる仕様・要件ID: services/frontend/README.md#使い方, services/frontend/src/router.tsx
- 関連リスクID: RISK-002
- テスト観点: 正常系／異常系
- テスト分類: システムテスト
- 対象機能・モジュール: frontend auth
- 実装状況: 既存テストあり（services/frontend/tests/e2e/ui_flows.spec.ts）

### TR-102: 登録画面（UI/E2E）
- 要件ID: TR-102
- 要件名: ユーザー登録の基本フロー
- 要件の説明: `/register` でユーザー作成が成功し、失敗時はエラーが表示されること。
- 根拠となる仕様・要件ID: services/frontend/README.md#使い方, services/frontend/src/router.tsx
- 関連リスクID: RISK-002
- テスト観点: 正常系／異常系
- テスト分類: システムテスト
- 対象機能・モジュール: frontend auth
- 実装状況: 既存テストあり（services/frontend/tests/e2e/ui_flows.spec.ts）

### TR-103: Races 画面（UI/E2E）
- 要件ID: TR-103
- 要件名: レース一覧と詳細の表示
- 要件の説明: `/races` から一覧を表示し、レース詳細へ遷移できること。
- 根拠となる仕様・要件ID: docs/20_data_contracts.md#5.3, services/frontend/src/router.tsx
- 関連リスクID: RISK-001
- テスト観点: 正常系
- テスト分類: システムテスト
- 対象機能・モジュール: frontend races
- 実装状況: 既存テストあり（services/frontend/tests/e2e/ui_flows.spec.ts）

### TR-104: Admin OAuth Clients 画面（UI/E2E）
- 要件ID: TR-104
- 要件名: OAuth client 管理
- 要件の説明: `/admin/oauth-clients` で client 作成・ローテーション・revoke が実行できること。
- 根拠となる仕様・要件ID: services/frontend/README.md#使い方, services/frontend/src/router.tsx
- 関連リスクID: RISK-002
- テスト観点: 正常系／異常系
- テスト分類: システムテスト
- 対象機能・モジュール: frontend admin, api-service admin oauth clients
- 実装状況: 既存テストあり（services/frontend/tests/e2e/ui_flows.spec.ts）

### TR-105: Scrape Console 画面（UI/E2E）
- 要件ID: TR-105
- 要件名: 手動スクレイプ投入
- 要件の説明: `/scrape` から `/scrape/*` の投入操作ができ、結果を表示できること。
- 根拠となる仕様・要件ID: services/frontend/README.md#使い方, services/frontend/src/router.tsx
- 関連リスクID: RISK-001
- テスト観点: 正常系／異常系
- テスト分類: システムテスト
- 対象機能・モジュール: frontend scrape console, api-service scrape routes
- 実装状況: 既存テストあり（services/frontend/tests/e2e/ui_flows.spec.ts）
