# Operations Runbook（監視・バックアップ・復旧）

作成日: 2025-12-27（Asia/Tokyo）  
更新日: 2025-12-28（Asia/Tokyo）

更新履歴
- 2025-12-27: 初版作成。
- 2025-12-28: 定期実行/同期の監視項目を追記。
- 2025-12-28: cronコンテナの運用と同期頻度を反映。

## 1. 監視対象（最低限）
- scraper:
  - 取得件数（時間あたり）
  - 失敗率（HTTP/timeout）
  - パーサ崩壊検知回数
  - /health（PC → Pi の疎通確認）
  - 定期実行の状態（/scrape/schedule、baba_codes 含む）
  - cron コンテナの稼働/最終実行
  - Pi 側ストレージ使用量（raw_html / logs）
  - 定期同期/差分同期の状態（/scrape/sync/status、1日おき）
- api:
  - /health
  - エラー率
  - レイテンシ
  - api-sync cron コンテナの稼働/最終実行
- db:
  - ディスク使用量
  - バックアップ成功/失敗
- pipeline/worker:
  - ジョブ成功率、実行時間
  - 連続失敗回数

## 2. バックアップ（推奨）
- Postgres: 日次バックアップ + 7/30世代保持（容量と相談）
- MLflow artifacts: 日次（または変更時）バックアップ
- 重要設定: nginx / compose / .env

## 3. 復旧手順（最小）
- DB復元 → API起動 → scraper再開 → pipeline再開
- 事故原因を `90_decisions.md` に記録し、再発防止を docs に反映する

## 4. SLO（暫定）
- オッズスナップショット取得率: 99%
- 学習パイプライン成功率: 95%（失敗は自動リトライで吸収）
