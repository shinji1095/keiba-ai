# scraper-service

更新日: 2025-12-27（Asia/Tokyo）

本サービスは `keiba.go.jp / TodayRaceInfo` を**低負荷ポリシー**で定期取得し、正規化したデータを api-service に投入します。

- 取得対象/スケジュール/例外/負荷: `04_scraping_requirements.md`
- サイト構造（PageName / URL規約）: `01_site_structure.md`
- 正規化（Odds/Payout）とフィクスチャ/TDD方針: `05_parsing_fixture_tdd.md`
- API 契約（正）: `21_openapi.yaml`
- DB/イベント契約の要点: `20_data_contracts.md`

## 1. できること（スコープ）

- PC版を正として、以下のページを取得し HTML を保存（sha256 採番）しつつ、パースして api-service へ POST します。
  - TodayRaceInfoTop / RaceList / DebaTable / RaceMarkTable / RefundMoneyList / Odds*（7ページ）
- 取得ログ（raw_fetch_logs）を api-service に投入できます（`POST /scrape/raw-fetch-logs`）。
- フィクスチャ収集（manifest.yml → HTML保存 + manifest_log.csv）を CLI で実行できます。

> 注意  
> 本リポジトリには実データ（取得済みHTML）は同梱しません。TDDは fixtures を別途収集して行ってください。

## 2. 重要な運用制約（固定）

- per-host concurrency: 1
- 連続リクエスト最小間隔: 1.5 秒以上（+ ジッタ）
- リトライ: 最大 3 回（ネットワーク例外 / 一部 5xx のみ、指数バックオフ）
- 全リクエストで取得ログを残す（成功/失敗問わず）

上記は `04_scraping_requirements.md` の C2 に基づき実装しています。

## 3. 使い方

### 3.1 環境変数

- `API_BASE_URL`（例: `http://reverse-proxy/api`）
- 認証（どちらか）
  - `API_ACCESS_TOKEN`（Bearer JWT を直接指定）
  - もしくは `API_USERNAME` / `API_PASSWORD`（`POST /auth/login` で取得）
- `KEIBA_DEVICE`（`pc` | `sp`、既定 `pc`）
- `RAW_HTML_DIR`（既定: `./data/raw_html`）
- `USER_AGENT`（既定は設定済み。必要に応じて変更）

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

当日の開催場・レース一覧を取得し、直ちに取得可能なページを best-effort で取得して api-service に投入します。

```bash
python -m scraper_service.cli scrape once --race-date 2025-12-26
```

### 3.5 常駐（簡易スケジューラ）

`RaceList` の発走時刻を一次情報として、t-5m/t-1m/final などのジョブを組み、実行します。

```bash
python -m scraper_service.cli scrape daemon --race-date 2025-12-26
```

※ `--race-date` を省略すると当日（JST）を使用します。

> わからない  
> レース終了のリアルタイム検知が可能かは未確認のため、RaceMarkTable/RefundMoneyList は固定遅延 + 少回数リトライで実装しています。

## 4. Docker

```bash
docker build -t scraper-service:dev .
docker run --rm -it \
  -e API_BASE_URL="http://reverse-proxy/api" \
  -e API_ACCESS_TOKEN="YOUR_JWT" \
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

- `20_data_contracts.md` では「event_id による冪等化」を言及していますが、`21_openapi.yaml` の /scrape 系スキーマには `event_id` が存在しません。  
  どちらを正とするかを Decision Log に記録し、必要なら OpenAPI を更新してください。
