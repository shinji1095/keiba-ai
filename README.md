# 競馬AI Webアプリ（MLOps / TDD / マイクロサービス）

本リポジトリは、Ubuntu PC と Raspberry Pi 5 に分散配置することを前提にしたモノレポ構成のスケルトンです。

## 配置方針（推奨）
- Ubuntu PC:
  - reverse-proxy（NGINX）
  - api-service（FastAPI）
  - postgres（PostgreSQL）
  - worker-service（Celery）
  - pipeline-orchestrator（Prefect）
  - mlflow（Tracking / Registry）
  - frontend（React + Vite）
- Raspberry Pi 5:
  - scraper-service（Scrapy）
  - inference-service（Hailo 8 推論、必要になってから追加）

## 開発開始（例）
- PC側: `deploy/compose/compose.pc.yaml`
- Pi側: `deploy/compose/compose.pi.yaml`

詳細は `deploy/compose/README.md` と `docs/10_architecture.md` を参照してください。

## TODO / 改善点
- frontend 単体テストのカバレッジ計測（Vitest coverage 導入）
