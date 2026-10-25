# Architecture — v1.0.0

v1.0.0ではRaspberry Piへの分散配置を廃止し、すべての処理をPCで実行する。
この文書とルート `compose.yaml` を現行の配置仕様とする。

## サービス境界

- web: Reactのビルド成果物をNGINXから配信。SPAの画面遷移と `/api/` の転送を担当。
- api: FastAPI、認証、データ参照、取り込み、推論。定期同期のcronも同じコンテナで実行。
- postgres: 業務データを保存。既存のSQLマイグレーションを継続利用。
- scraper: 制御HTTPサーバー、常駐planスケジューラ、HTML/JSONL保存。
  制御APIとスケジューラは同じデータディレクトリを共有する。
- mlflow: 任意起動の実験管理・モデルレジストリ（mlまたはtrainingプロファイル）。
- pipeline: 任意起動の学習ジョブ（trainingプロファイル、通常は `run --rm`）。

web以外の通常サービスはDocker内部ネットワークを使用する。
PostgreSQLの `pg_isready`、scraperの `/health` 成功後にAPIを起動する。
API・scraper内の複数プロセスはSupervisorが管理し、異常終了時に再起動する。

## データフロー

1. scraperがkeiba.go.jpからHTMLを取得し、PC上にHTMLと正規化JSONLを保存。
2. APIが `http://scraper:8080/control/export/*` から取得データをpull。
3. APIが差分を評価し、自然キーによるUpsertでPostgreSQLへ反映。
4. ブラウザはweb経由でAPIを参照。
5. pipelineがDBから学習データを抽出し、評価・登録。APIがモデルを取得して推論。

## 統合・削除

- PC/Pi/開発/API単体のComposeをルート `compose.yaml` に統合。
- reverse-proxyとfrontendをwebへ統合。Vite開発サーバーは通常運用で起動しない。
- api-sync-cronをapiへ、scraper-schedulerをscraperへ統合。
- scraper-healthは制御APIの `/health` に統合。
- 旧scraper-cron、未使用worker、Scrapyのサンプルコードを削除。

## 維持する契約

API・DB・パーサー・取得間隔・差分同期・学習モデルは配置変更の対象外。
API契約は `21_openapi.yaml`、データ契約は `20_data_contracts.md`、
取得条件は `scraper/04_scraping_requirements.md` を参照。
単体・結合テストはDocker内で実行し、外部サイトへの取得を伴うテストは明示的に実行する。
