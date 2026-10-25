# PC単独運用 — v1.0.0

リポジトリルートの `compose.yaml` だけを使用します。
PC/Pi/開発/API単体のComposeは統合しました。

## 起動・停止

```bash
cp -n env.example .env
docker compose up -d --build
docker compose ps
docker compose logs -f api scraper
# 停止（永続データを保持）
docker compose down
```

通常起動はweb、api、postgres、scraperの4コンテナです。
Webは `http://localhost`（変更時は `WEB_PORT`）、APIは `/api/` です。
API・DB・scraperはコンテナ内ネットワークで通信します。

## 既存環境からの移行

- 旧環境を停止してから新構成を起動してください。他プロジェクトのコンテナは対象外です。
- `.env` は上書きせず `env.example` と照合してください。
- `PC_API_URL`、`SCRAPER_CONTROL_BASE_URL`、`SCRAPER_CONTROL_PORT`、
  `SCRAPER_HEALTH_PORT`、`SCRAPER_CRON`、`API_ACCESS_TOKEN` は新Composeでは不要です。
- `SCRAPER_FORWARD_TIMEOUT_SEC` と `SCRAPE_SYNC_CRON` は継続利用します。
- PostgreSQLとMLflowのボリュームキーは継続します。同じComposeプロジェクト名で
  起動すれば既存ボリュームを再利用できます。プロジェクト名を変える場合は
  DBをバックアップし、復元してから切り替えてください。
- 旧Piの `services/scraper/data/` は停止中にPCの同じパスへコピーしてください。
- APIの同期状態は `api_data` ボリュームに保存します。旧状態ファイルがあれば
  `/app/data/sync_state.json` へ移行してください。未移行時は再同期します。
- 既存MLflowモデルが `/mlartifacts` の直接ファイル参照で記録されている場合、
  新構成のHTTP artifact配信に対応させるため学習・登録を再実行してください。

## 任意の学習・モデル管理

```bash
docker compose --profile ml up -d --build mlflow
# 前日までのデータで学習・登録（既定のPrefect Flow）
docker compose run --build --rm pipeline
# 明示的に評価閾値を満たしたモデルを昇格
docker compose run --build --rm pipeline python -m pipeline_service.train_win_classifier --promote
```

MLflow UIは `http://localhost:5000`。推論APIを使う間はMLflowを起動してください。
`pipeline` は単発ジョブです。定期学習のスケジュール登録は別途行ってください。

## テスト・開発

`docs/80_test_guideline.md` を参照してください。
フロントエンドはDockerfileの `development` ターゲットで開発・テストできます。
