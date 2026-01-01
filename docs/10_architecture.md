# Architecture（サービス境界・配置・データフロー）

作成日: 2025-12-27（Asia/Tokyo）  
更新日: 2026-01-01（Asia/Tokyo）

更新履歴
- 2025-12-27: 初版作成。
- 2025-12-28: 手動実行/定期実行状態/同期のAPIを反映。
- 2025-12-28: scraper の実行方式をトリガ駆動へ更新。
- 2025-12-28: cronコンテナと API 制御を反映。
- 2025-12-31: データ同期の方向（api→scraper）と差分評価トリガを更新。
- 2026-01-01: 差分評価の判定主体を api-service に明記。

---

## 1. サービス境界（今回スコープ）

- **reverse-proxy（NGINX）**
  - 外部入口、/ と /api のルーティング集約
  - 「直接 api-service にアクセスさせない」要件の実装点

- **api-service（FastAPI）**
  - 認証（Bearer/JWT + Refresh Cookie）
  - 同期要求の起点（差分評価トリガ）
  - データ参照API（ダッシュボード/バックテスト/デバッグ向け）
  - 入出力契約の正: `21_openapi.yaml` / `20_data_contracts.md`
  - api-sync cron コンテナが `/scrape/sync/scheduled` を定期トリガ

- **postgres（PostgreSQL）**
  - 永続データ（レース、出走表、オッズスナップショット、成績、払戻、HTTP取得ログ）
  - HTTP取得ログは永続データに含める（任意）

- **scraper-service（Scrapy / Raspberry Pi、control API + cron）**
  - api-service からの手動実行を受け付ける control API を提供
  - 定期実行は Pi の cron コンテナが control API を呼び出す
- 取得データは Pi に保存し、api-service が差分評価の判定主体として同期を実行する（同期方向は api → scraper）
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
- PC → Pi は **api-service → scraper-service（同期/差分同期の要求）**、**scraper control API（/control/*）**、**/health**
- Pi → PC は **同期要求への応答（受理結果/ステータス）**
- 定期実行は Pi の cron コンテナが担当し、api-service が on/off と baba_codes を制御する
- 定期同期は PC の api-sync cron コンテナが担当し、api-service が interval_days と JST 日付境界で可否を制御する
- api-service ⇔ scraper-service 間は **認証不要**（将来のアップデートで対応予定）
- 同期ペイロードの送信先: `/control/ingest/*`
- 認証方式:
  - Access: `Authorization: Bearer <JWT>`（15分）
  - Refresh: HttpOnly Cookie（30日, rotation, Redis revoke）

---

## 4. データフロー（代表）

1. Pi: scraper が `RaceList / DebaTable / Odds* / RaceMarkTable / RefundMoneyList` を収集して Pi に保存
2. PC → Pi: api-service が DB を正として同期要求を発行し、api-service が差分を評価
3. PC → Pi: 差分のみを api → scraper 方向で反映
4. PC: frontend / backtest が api-service から参照（集計・可視化）

---

## 5. 重要な設計上の約束（PMレビュー）

- 契約（API/DB/イベント）を固定してから実装する（破壊的変更は Decision Log へ）
- スクレイピングの頻度・同時接続数・リトライは **“技術設定”ではなく運用契約** として扱う
- 冪等性の担保:
  - race_key による Upsert
  - 収集イベントは event_id による重複検知
- オッズスナップショットの一意性: `race_key × bet_type × snapshot_kind × odds_flg`（odds_flg は表示モード識別子、NULL 可）
