# scraper-service — v1.0.0

PC内でkeiba.go.jp / TodayRaceInfoを収集し、HTML・正規化JSONLを保存します。
Requests・BeautifulSoupによる実装は `scraper_service/` に集約しています。
APIと常駐planスケジューラを1コンテナ内でSupervisorが管理します。

## 起動

リポジトリルートで実行します。

```bash
docker compose up -d --build scraper
```

- control API: Docker内部 `http://scraper:8080/control/*`
- health: 同じサーバーの `/health`（専用コンテナは不要）
- 定期取得: planスケジューラ。画面/APIでon/off、対象場、先読み日数を設定。
- 手動取得: frontend → api → scraperのcontrol API。
- 同期: APIが `/control/export/*` をpullし、DBに反映。
- データ: PCの `services/scraper/data/` を `/app/data` にマウント。

## 負荷制御

- per-host concurrency: 1
- 定期取得: 60〜120秒（60秒＋最大60秒ジッタ）
- 手動取得: 60秒固定
- リトライ: 最大3回、指数バックオフ

## CLI・テスト

```bash
docker compose run --rm --no-deps scraper python -m scraper_service.cli --help
docker compose run --rm --no-deps scraper python -m scraper_service.cli fixtures download --manifest fixtures/manifest.yml --fixtures-root fixtures
docker compose run --rm --no-deps scraper python -m pytest tests -m "not integration"
```

取得元URLは `docs/scraper/01_site_structure.md`、取得条件は
`docs/scraper/04_scraping_requirements.md`、API契約は `docs/21_openapi.yaml` を参照。
