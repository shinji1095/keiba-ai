# Decision Log（ADR風）

破壊的変更や、後戻りコストが高い意思決定を記録する。
「いつ・誰が・なぜ」を残し、将来の議論コストを下げる。

作成日: 2025-12-27（Asia/Tokyo）  
更新日: 2026-01-02（Asia/Tokyo）

更新履歴
- 2025-12-27: 初版作成。
- 2025-12-28: scraper 実行方式の決定を追記。
- 2025-12-28: cronコンテナ/制御API/同期方針を追記。
- 2025-12-31: 同期方向の変更（api→scraper）を追記。
- 2026-01-02: 同期定義を Pi 最新/PC pull に変更。
- 2026-01-02: 冪等化は自然キーUpsertを正とし、event_id を廃止。

## 2025-12-27: 技術スタック一次決定
- Decision:
  - FastAPI / Scrapy / Prefect / Celery / MLflow / Postgres / React(Vite) を一次採用
  - 初期は docker compose、将来 k3s へ移行可能な構成を維持
- Rationale:
  - Python中心でMLOpsと親和性が高い
  - Pi常駐スクレイピングとPC側学習の役割分担がしやすい
- Consequences:
  - Python/TS の2言語運用になるためCI・規約を早期に整備する

## 2025-12-28: scraper 実行方式はトリガ駆動
- Decision:
  - scraper は常時起動の無限ループ（plan固定）を採用しない
  - 定期/手動トリガ時にレース探索を行い、その都度スクレイピングを実行する
  - 定期トリガは Pi の cron コンテナで起動する
- Rationale:
  - 日付更新や再起動前提を排除し、誤取得と運用負担を減らす
  - 手動実行/定期実行の契約と整合させる
- Consequences:
  - daemon/plan ループは廃止または非推奨となる
  - 実行スケジュールの監視は cron コンテナ側で行う

## 2025-12-28: cronコンテナによる定期実行とAPI制御
- Decision:
  - Pi 側に cron コンテナを配置し、定期実行は cron コンテナが制御する
  - api-service から cron コンテナの on/off と baba_codes を制御する
  - 手動実行は api-service から Pi 側の control API に指示する
  - スクレイピング情報は Pi 側で保存し、api-service からの要求で差分評価を行う（既定: 1日おき）
- Rationale:
  - 即時性を確保しつつ、plan固定/無限ループの運用負担を排除する
  - 定期/手動トリガの契約をAPI側で一元管理できる
- Consequences:
  - PC→Pi の制御通信が必要になる（認証/可用性の設計が必須）
  - cron コンテナと control API の保守運用が必要になる

## 2025-12-31: データ同期は api → scraper
- Decision:
  - データ同期の方向は api → scraper を正とする
  - api-service が差分評価の判定主体として同期を実行する
- Rationale:
  - 同期の起点を PC 側に集約し、運用と監視を一元化する
  - 同期トリガと差分評価の責務を明確化する
- Consequences:
  - api-service 側の同期要求/差分評価フローと scraper 側の受け口が必要になる
  - テスト要件と運用ドキュメントの更新が必要になる

## 2026-01-02: データ同期は Pi 最新・PC pull
- Decision:
  - Pi 側を最新データの正とする
  - api-service が pull 同期で取り込み、差分評価の判定主体は api-service とする
- Rationale:
  - スクレイピング実行ノード（Pi）が最新データを保持する前提と整合する
  - PC 側の取り込みタイミングを統一し、運用/監視を簡潔化できる
- Consequences:
  - scraper-service に同期データ提供のインターフェースが必要になる
  - api-service の同期フローとテスト要件/ドキュメントの更新が必要になる

## 2026-01-02: 冪等化は自然キーUpsert（event_id を廃止）
- Decision:
  - 収集/同期ペイロードから `event_id` を削除し、冪等性は自然キー・一意制約に基づく Upsert で担保する
  - `event_id` の受信済み管理（イベントログ方式）は本リリースでは採用しない
- Rationale:
  - 取り込み対象（races/entries/odds/results/payouts）は自然キーが定義でき、Upsert で冪等性が成立する
  - event_id 管理は設計/運用（失敗時の扱い、保持期間、レスポンス固定など）の決定が必要で、初期リリースでは過剰
- Consequences:
  - `event_id` で副作用（手動実行タスク等）の二重実行を防ぐことはできないため、クライアント側のリトライ方針や運用で吸収する
  - docs/20_data_contracts.md, docs/21_openapi.yaml, テスト要件/テストを自然キー前提に更新する必要がある
