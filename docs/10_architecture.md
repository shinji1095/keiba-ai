# Architecture（サービス境界・配置・データフロー）

作成日: 2025-12-27（Asia/Tokyo）  
更新日: 2025-12-27（Asia/Tokyo）

---

## 1. サービス境界（今回スコープ）

- **reverse-proxy（NGINX）**
  - 外部入口、/ と /api のルーティング集約
  - 「直接 api-service にアクセスさせない」要件の実装点

- **api-service（FastAPI）**
  - 認証（Bearer/JWT + Refresh Cookie）
  - スクレイピング結果の受け口（収集イベントの投入）
  - データ参照API（ダッシュボード/バックテスト/デバッグ向け）
  - 入出力契約の正: `21_openapi.yaml` / `20_data_contracts.md`

- **postgres（PostgreSQL）**
  - 永続データ（レース、出走表、オッズスナップショット、成績、払戻、HTTP取得ログ）

- **scraper-service（Scrapy / Raspberry Pi 常駐）**
  - 低負荷ポリシーに従い定期収集し、api-service へ送信
  - HTMLフィクスチャの採取（TDD用）
- **frontend（React / Typescript / Vite）**
  - ダッシュボード

---

## 2. 今回スコープ外（将来導入候補）
- pipeline-service（Prefect）
- worker-service（Celery）
- MLflow

> これらは本リリースの契約（API/イベント）に影響しない範囲で後続追加する。

---

## 3. ネットワーク境界（前提）

- 外部からの入口は reverse-proxy のみ
- Pi → PC は **scraper → api-service のみ**
- PC → Pi は **scraper health check（GET /health）** のみ
- 認証方式:
  - Access: `Authorization: Bearer <JWT>`（15分）
  - Refresh: HttpOnly Cookie（30日, rotation, Redis revoke）

---

## 4. データフロー（代表）

1. Pi: scraper が `RaceList / DebaTable / Odds* / RaceMarkTable / RefundMoneyList` を収集
2. Pi → PC: scraper が api-service に収集イベントを POST（例: `POST /scrape/odds-snapshots`）
3. PC: api-service が DB に Upsert（整合性チェック、重複排除、ログ記録）
4. PC: frontend / backtest が api-service から参照（集計・可視化）

---

## 5. 重要な設計上の約束（PMレビュー）

- 契約（API/DB/イベント）を固定してから実装する（破壊的変更は Decision Log へ）
- スクレイピングの頻度・同時接続数・リトライは **“技術設定”ではなく運用契約** として扱う
- 冪等性の担保:
  - race_key による Upsert
  - 収集イベントは event_id による重複検知
