更新履歴
- 2025-12-28: 初版作成。
- 2025-12-28: API/フロントエンドの定義済み・追加テスト要件を追記。
- 2025-12-28: テスト分類と追加実装の反映。

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

### TR-002: scraper の client credentials トークン発行
- 要件ID: TR-002
- 要件名: scraper 向け client_credentials トークン
- 要件の説明: `POST /auth/token` が scraper の認証情報で Bearer トークンを発行し、不正な認証情報は拒否すること。
- 根拠となる仕様・要件ID: docs/20_data_contracts.md#5.1, docs/21_openapi.yaml:/auth/token
- 関連リスクID: RISK-002
- テスト観点: 正常系／異常系
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service auth, OAuth client store
- 実装状況: 既存テストあり（services/api/tests/test_oauth_client_and_scope.py）

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

### TR-004: event_id による冪等性
- 要件ID: TR-004
- 要件名: event_id の冪等投入
- 要件の説明: 同一 `event_id` の再送が成功レスポンスとなり、重複レコードを生成しないこと。
- 根拠となる仕様・要件ID: docs/20_data_contracts.md#1.4, docs/20_data_contracts.md#5.2
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

### TR-008: /scrape のスコープゲート（認可）
- 要件ID: TR-008
- 要件名: scrape:write の認可制御
- 要件の説明: `scrape:write` トークンなしでは `POST /scrape/*` が 401 となり、正しいトークンで成功すること。
- 根拠となる仕様・要件ID: docs/21_openapi.yaml:/scrape/*, services/api/README.md#5
- 関連リスクID: RISK-002
- テスト観点: 正常系／異常系
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service scrape routes, auth scope gate
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
- 要件の説明: `/scrape/races` `/scrape/race-entries` `/scrape/race-results` `/scrape/payouts` `/scrape/race-changes` が最小ペイロードで upsert されること。
- 根拠となる仕様・要件ID: docs/20_data_contracts.md#3, docs/20_data_contracts.md#4, docs/21_openapi.yaml:/scrape/*
- 関連リスクID: RISK-001
- テスト観点: 正常系
- テスト分類: 結合テスト
- 対象機能・モジュール: api-service scrape routes, DB upsert
- 実装状況: 既存テストあり（services/api/tests/test_scrape_and_races.py）

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
