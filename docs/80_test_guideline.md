# 80 Test Contracts（テスト契約）

作成日: 2025-12-28（Asia/Tokyo）  
更新日: 2026-01-01（Asia/Tokyo）

更新履歴
- 2025-12-28: 初版作成。
- 2025-12-28: 単体テストの実行方法を追記。
- 2025-12-28: テスト実行を Docker 環境内に統一。
- 2026-01-01: frontend の単体テスト（Docker 実行手順）を追記。

---

## 1. 目的
- テスト要件、設計方針、実行方法を「契約」として固定する。
- 仕様変更時の更新順序（docs → tests → implementation）を保証する。

## 2. 適用範囲
- 対象サービス: api-service / scraper-service / frontend
- 対象ドキュメント: `docs/test/00_test_requirements.md`（テスト要件の正）

## 3. 用語・識別子
- **TR-xxx**: テスト要件ID（`docs/test/00_test_requirements.md` の項番）
- **RISK-xxx**: リスクID（安全性・行政申請に関わる重要度を明示）
- **仕様参照**: `docs/20_data_contracts.md`, `docs/21_openapi.yaml` など

## 4. テスト分類（単体／結合／システム）
|分類|目的|外部依存|代表例|
|---|---|---|---|
|単体テスト|関数・クラス単体の正しさ|なし|純粋関数、変換ロジック|
|結合テスト|サービス内部の統合動作|DB/HTTP（ローカル）|FastAPI + SQLite, サービス層|
|システムテスト|サービス間／UI含む動作|複数サービス/ネットワーク|Playwright E2E, PC→Pi 疎通|

## 5. テスト要件の設計方針
- **要件1件につき1テスト以上**を割り当てる（TR-xxx に紐付ける）。
- **必須項目**: 要件ID、要件名、説明、仕様参照、関連リスクID、テスト観点、分類、対象モジュール。
- **最小ペイロード優先**: API では最小成立データで検証し、境界値は別ケースで切り出す。
- **データは固定値**: 日付やIDは固定値で再現性を担保する。
- **冪等性検証**: 契約で定義された自然キー（race_key 等）で重複投入を検証する。
- **外部依存は明示**: システムテストは事前条件（起動サービス、環境変数）を明記する。

## 6. テストの実行方法
テストは **構築済みの Docker Compose 環境内**で実行する。  
前提: 対象の compose が起動済み（PC: `docker-compose.pc.yaml` / Pi: `docker-compose.pi.yaml`）。

### 6.1 単体テスト（pytest / fast）
integration マーカーを除外して実行します（scraper は integration を使用）。

```bash
docker compose --env-file .env -f docker-compose.pc.yaml exec api python -m pytest tests -m "not integration"
docker compose --env-file .env -f docker-compose.pi.yaml exec scraper python -m pytest tests -m "not integration"
docker compose --env-file .env -f docker-compose.pc.yaml exec frontend npm run test:unit
```

frontend の単体テストは Vitest を使用します。

### 6.2 API（結合テスト）
起動済みの API コンテナ内で実行します。

```bash
docker compose --env-file .env -f docker-compose.pc.yaml exec api python -m pytest tests
```

### 6.3 scraper（結合/システム）
PC→Pi 疎通テストは `SCRAPER_HEALTH_URL` を必須とします。

```bash
docker compose --env-file .env -f docker-compose.pi.yaml exec scraper python -m pytest tests
docker compose --env-file .env -f docker-compose.pi.yaml exec -e SCRAPER_HEALTH_URL=http://scraper-health:8081/health scraper \
  python -m pytest tests/test_scraper_health_connection.py
```

### 6.4 frontend（システムテスト / Playwright）
frontend コンテナの build 済みを前提に実行します。

```bash
docker compose --env-file .env -f docker-compose.pc.yaml exec frontend npm run test:e2e
```

`PW_BASE_URL` を指定すると接続先を変更できます。

```bash
docker compose --env-file .env -f docker-compose.pc.yaml exec -e PW_BASE_URL=http://127.0.0.1:5173 \
  frontend npm run test:e2e
```

### 6.5 frontend→api→scraper（PC→Pi）システムテスト（実環境）
Pi の scraper-service（control API）へ到達できる環境でのみ実行します。

前提（例）:
- PC IP: `100.103.236.14`
- Pi IP: `100.124.136.103`
- `.env` に `SCRAPER_CONTROL_BASE_URL` を設定（api-service が scraper control API に到達できる必要）
  - 実ホストPi: `SCRAPER_CONTROL_BASE_URL=http://100.124.136.103:8080`
  - 1台で全サービス（`docker-compose.pc.yaml` + `docker-compose.pi.yaml`）: `SCRAPER_CONTROL_BASE_URL=http://scraper:8080`

```bash
docker compose --env-file .env -f docker-compose.pc.yaml exec -e PW_BASE_URL=http://reverse-proxy \
  frontend npm run test:e2e:system
```
