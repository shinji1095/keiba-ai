# 競馬AI Webアプリ v1.0.0

データ収集・保存・閲覧・学習・推論をすべて1台のPCで実行します。
Raspberry Piは使用しません。起動設定はルートの `compose.yaml` に集約しています。

## 起動

```bash
# 初回のみ。既存の .env は上書きせず env.example と照合する
cp -n env.example .env
docker compose up -d --build
```

画面は `http://localhost`、APIドキュメントは `http://localhost/api/docs` です。
既存 .env の Pi 向けURLは不要です。内部接続先はComposeで固定しています。

## 構成

| コンテナ | 役割 |
|---|---|
| web | Reactのビルド成果物をNGINXで配信し、`/api/` をAPIへ転送 |
| api | FastAPIと定期同期。Supervisorで両プロセスを管理 |
| postgres | PostgreSQLによる永続保存 |
| scraper | 取得制御APIと常駐取得スケジューラ。Supervisorで管理 |

取得データはPCの `services/scraper/data/` に保存し、APIが同一PC内のscraperから
pullしてDBへ反映します。取得間隔・正規化・差分同期の契約は維持します。
DB・同期状態・MLflow成果物はそれぞれ永続ボリュームへ保存します。

学習・モデル管理は必要なときだけ起動します。

```bash
docker compose --profile ml up -d mlflow
docker compose run --build --rm pipeline python -m pipeline_service.train_win_classifier --promote
```

`services/` に処理のコード、`infra/nginx/` に配信設定、`docs/` に設計・運用方針、
`spec/` に取得データの詳細仕様、`fixtures/` に検証用HTMLがあります。

移行・運用は `deploy/compose/README.md`、構成は `docs/10_architecture.md`、
テスト手順は `docs/80_test_guideline.md` を参照してください。
