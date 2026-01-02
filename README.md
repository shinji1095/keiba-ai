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

## TODO（仕様再考の記録）
- [P0] scraper-health の起動方式と配置の整合（PYTHONPATH 追加なしで動作する構成を決める）
- [P0] トリガ駆動の実行方式に統一（起動時のplan固定/日付更新は採用しない）
- [P0] Scrapy 実装を正として実行入口/構成を一本化（requests 系の扱いを決定）
- [P1] 手動実行タスク/定期実行状態/同期（1日1回・差分）の制御API連携仕様の確定
- [P1] RaceList 再取得頻度と変更検知（race_changes）方針の確定
- [P1] API接続の環境変数名を統一（PC_API_URL vs API_BASE_URL）
- [P2] odds final の取得タイミング定義（発走直前の窓と許容遅延）
- [P2] PC版失敗時のSP版フォールバック有無・条件の確定

## 開発開始（例）
- PC側: `deploy/compose/compose.pc.yaml`
- Pi側: `deploy/compose/compose.pi.yaml`

詳細は `deploy/compose/README.md` と `docs/10_architecture.md` を参照してください。
