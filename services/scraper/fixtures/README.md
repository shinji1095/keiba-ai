# Fixtures

更新日: 2025-12-27（Asia/Tokyo）

本ディレクトリは **HTML フィクスチャの収集と管理**に使用します。

- 目的: パーサのTDD（`05_parsing_fixture_tdd.md`）
- 取得方法: `python -m scraper_service.cli fixtures download --manifest fixtures/manifest.yml --fixtures-root fixtures`

## 1. manifest.yml

`manifest.yml` は配列です。各要素は以下のキーを持ちます。

- `name`: 任意の識別子（テストケース名）
- `race_key`: `{ race_date, baba_code, race_no }`
- `device`: `pc` | `sp`
- `page_name`: PageName（例: `RaceList`）
- `url`: 取得URL（完全URL推奨）
- `out`: 保存先パス（fixtures_root からの相対パス）
- `odds_flg`（任意）
- `snapshot_kind`（任意、既定 `manual`）
- `expect.http_status`（任意）

## 2. manifest_log.csv

取得結果のログ（append-only）。

列:
- `name,out_path,url,fetched_at,http_status,sha256,content_type,content_encoding,elapsed_ms,note`
