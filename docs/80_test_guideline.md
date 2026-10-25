# テスト契約 — v1.0.0

テストはDocker内で実行します。仕様は `test/00_test_requirements.md` を参照。
システム間通信は同じPCのComposeネットワーク内で行います。

## API・scraper

```bash
docker compose build api scraper
docker compose run --rm --no-deps -e DATABASE_URL=sqlite:////tmp/tests.db -e MLFLOW_TRACKING_URI= api python -m pytest tests -m "not system"
docker compose run --rm --no-deps scraper python -m pytest tests -m "not integration"
```

APIテストはSQLiteを使用し、実行環境のPostgreSQLには書き込みません。
scraperテストは固定HTMLと一時ディレクトリを使用します。

## 学習パイプライン

```bash
docker compose build pipeline
docker compose run --rm --no-deps -e DATABASE_URL= -e PREFECT_SERVER_ANALYTICS_ENABLED=false pipeline python -m pytest tests
```

固定データによる学習・評価と、DB未設定時のFlowの動作を検証します。

## 画面の単体・E2Eテスト

```bash
docker build --target development -f services/frontend/Dockerfile -t keiba-frontend-test .
docker run --rm keiba-frontend-test npm run test:unit
docker run --rm keiba-frontend-test npm run test:e2e
```

## システムテスト

起動済み環境の制御API疎通を確認します（外部サイトの取得なし）。

```bash
docker compose exec -e SCRAPER_HEALTH_URL=http://scraper:8080/health scraper python -m pytest tests/test_scraper_health_connection.py
docker compose exec -e REQUIRE_SCRAPER=1 api python -m pytest tests/test_front_api_scraper_system.py -k "health or schedule"
```

手動取得を含むシステムテストは実サイトへのリクエストを発生させます。
必要なときだけ明示して実行してください。

```bash
docker run --rm --network host -e PW_BASE_URL=http://127.0.0.1 keiba-frontend-test npm run test:e2e:system
```

## 品質ゲート

PythonはRuffとpytest、画面はTypeScript/Viteビルド・Vitest・Playwrightで検証します。
GitHub Actionsの設定はルート `.github/workflows/ci.yml` に配置します。
旧scraper-cronのテストは廃止し、常駐スケジューラは `test_plan_scheduler.py` で検証します。
