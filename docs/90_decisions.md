# Decision Log（ADR風）

破壊的変更や、後戻りコストが高い意思決定を記録する。
「いつ・誰が・なぜ」を残し、将来の議論コストを下げる。

作成日: 2025-12-27（Asia/Tokyo）  
更新日: 2025-12-28（Asia/Tokyo）

更新履歴
- 2025-12-27: 初版作成。
- 2025-12-28: scraper 実行方式の決定を追記。
- 2025-12-28: cronコンテナ/制御API/同期方針を追記。

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
  - スクレイピング情報は Pi 側で保存し、差分同期でPCへ反映（既定: 1日おき）
- Rationale:
  - 即時性を確保しつつ、plan固定/無限ループの運用負担を排除する
  - 定期/手動トリガの契約をAPI側で一元管理できる
- Consequences:
  - PC→Pi の制御通信が必要になる（認証/可用性の設計が必須）
  - cron コンテナと control API の保守運用が必要になる
