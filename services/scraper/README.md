# scraper-service

作成日: 2025-12-27（Asia/Tokyo）  
更新日: 2026-01-02（Asia/Tokyo）

更新履歴
- 2025-12-27: 初版作成。
- 2025-12-28: トリガ駆動の実行方式に更新。
- 2025-12-28: 外部スケジューラ手順を追記。
- 2025-12-28: cronコンテナ運用とAPI制御方針を追記。
- 2025-12-31: api→scraper の同期受け口（/control/ingest）を追記。
- 2026-01-01: raw_fetch_logs を削除し、取得ログはCSVで管理する方針に更新。
- 2026-01-02: 同期を Pi 最新/PC pull に更新し、/control/export を追加。

本サービスは `keiba.go.jp / TodayRaceInfo` を**低負荷ポリシー**で定期/手動トリガ実行し、Pi 側に保存します。正規化データは Pi 側に保存し、api-service が pull して取り込みます。

- 取得対象/スケジュール/例外/負荷: `04_scraping_requirements.md`
- サイト構造（PageName / URL規約）: `01_site_structure.md`
- 正規化（Odds/Payout）とフィクスチャ/TDD方針: `05_parsing_fixture_tdd.md`
- API 契約（正）: `21_openapi.yaml`
- DB/イベント契約の要点: `20_data_contracts.md`

## 1. できること（スコープ）

- PC版を正として、以下のページを取得し HTML を保存（sha256 採番）します。
  - TodayRaceInfoTop / RaceList / DebaTable / RaceMarkTable / RefundMoneyList / Odds*（7ページ）
- scraper が取得した正規化データを Pi 側に保存し、api-service が /control/export/* で pull します。
- フィクスチャ収集（manifest.yml → HTML保存 + manifest_log.csv）を CLI で実行できます。

> 注意  
> 本リポジトリには実データ（取得済みHTML）は同梱しません。TDDは fixtures を別途収集して行ってください。

## 2. 重要な運用制約（固定）

- per-host concurrency: 1
- 連続リクエスト最小間隔（全ページ共通）:
  - 定期実行: 60〜300 秒（1〜5分、ジッタ込み）
  - 手動実行: 60 秒（1分、固定）
- リトライ: 最大 3 回（ネットワーク例外 / 一部 5xx のみ、指数バックオフ）
- 全リクエストで取得結果ログを残す（成功/失敗問わず）

上記は `04_scraping_requirements.md` の C2 に基づき実装しています。

## 3. 使い方

### 3.1 環境変数

- `KEIBA_DEVICE`（`pc` | `sp`、既定 `pc`）
- `RAW_HTML_DIR`（既定: `./data/raw_html`）
- `INGEST_DIR`（同期データの保存先。既定: `./data/ingest`）
- `USER_AGENT`（既定は設定済み。必要に応じて変更）
- `SCRAPER_CRON`（cron コンテナの実行間隔。例: `0 6 * * *`）
- `SCRAPER_CONTROL_HOST` / `SCRAPER_CONTROL_PORT`（control API の待受。既定: `0.0.0.0:8080`）

### 3.2 ローカル実行（開発）

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements/dev.txt

# CLI ヘルプ
python -m scraper_service.cli --help
```

### 3.3 フィクスチャ収集（manifest.yml）

```bash
python -m scraper_service.cli fixtures download --manifest fixtures/manifest.yml --fixtures-root fixtures
```

- 取得結果は `fixtures/manifest_log.csv` に append-only で記録されます。
- HTML は `fixtures/<YYYY-MM-DD>_<babaCode>_<RR>/<device>/...html` に保存されます。

### 3.4 スクレイピング（ワンショット）

当日の開催場・レース一覧を取得し、直ちに取得可能なページを best-effort で取得して Pi 側に保存します。

```bash
python -m scraper_service.cli scrape once --race-date 2025-12-26
```

### 3.5 Pi plan スケジューラ（常駐）

scraper-scheduler コンテナが plan を生成し、計画時刻に沿ってスクレイピングを実行します。  
api-service が定期実行の on/off と baba_codes を制御し、スケジューラはその状態に従って plan を生成/実行します。

```bash
docker compose -f docker-compose.pi.yaml up -d scraper-scheduler
```

ローカル実行は以下です。

```bash
python -m scraper_service.cli scrape scheduler
```

### 3.6 Pi cron コンテナ（legacy）

scraper-cron コンテナは `scrape scheduled` を定期実行する旧方式です。  
plan 駆動の常駐スケジューラが正となるため、互換用途でのみ利用します。

```bash
docker compose -f docker-compose.pi.yaml up -d scraper-cron
```

### 3.7 手動実行

- frontend → api-service → Pi control API の経路で即時実行する
- ローカル確認は以下で実行できる

```bash
docker compose -f docker-compose.pi.yaml run --rm scraper scrape once --baba-code 18
```

> わからない  
> レース終了のリアルタイム検知が可能かは未確認のため、RaceMarkTable/RefundMoneyList は固定遅延 + 少回数リトライで実装しています。

### 3.8 api-service への同期データ提供（export）

- 提供先: `POST /control/export/*`（認証不要）
- `INGEST_DIR` 配下に保存した正規化データを JSONL から読み出して返す
- レスポンスの各 item は api-service の `/scrape/*` と同一スキーマ

## 4. Docker

```bash
docker build -t scraper-service:dev .
docker run --rm -it \
  scraper-service:dev \
  python -m scraper_service.cli --help
```

## 5. 開発（品質）

- `pytest`（ユニットテストはネットワークアクセス無し）
- `ruff`（lint/format）
- `mypy`（型チェック）

```bash
pytest -q
ruff check .
mypy .
```

## 6. TODO（契約の整合）

- 冥等性は自然キーUpsertを正とする（Decision Log を参照）
