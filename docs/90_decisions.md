# Decision Log（ADR風）

破壊的変更や、後戻りコストが高い意思決定を記録する。
「いつ・誰が・なぜ」を残し、将来の議論コストを下げる。

## 2025-12-27: 技術スタック一次決定
- Decision:
  - FastAPI / Scrapy / Prefect / Celery / MLflow / Postgres / React(Vite) を一次採用
  - 初期は docker compose、将来 k3s へ移行可能な構成を維持
- Rationale:
  - Python中心でMLOpsと親和性が高い
  - Pi常駐スクレイピングとPC側学習の役割分担がしやすい
- Consequences:
  - Python/TS の2言語運用になるためCI・規約を早期に整備する
