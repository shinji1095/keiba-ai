# Frontend Screen List（画面リスト）

作成日: 2026-01-04（Asia/Tokyo）  
更新日: 2026-01-04（Asia/Tokyo）

更新履歴
- 2026-01-04: 初版作成（機能一覧と画面の対応付けを明確化）。

---

## 1. 目的
- frontend の画面（URL/責務）を棚卸しし、`docs/02_feature_list.csv` の機能IDへトレース可能にする。
- 画面追加は最小限にし、原則「一覧→詳細（展開/タブ/パネル）」で情報密度を高める。

## 2. 画面一覧（URL・機能対応）
|URL|画面名|概要|認証|対応機能ID（例）|主なデータソース|
|---|---|---|---|---|---|
|`/login`|Login|ユーザーがログインし access token を取得する|不要|FE-AUTH-002|POST `/auth/login`|
|`/register`|Register|ユーザー登録を行い access token を取得する|不要|FE-AUTH-001|POST `/auth/register`|
|`/`|Overview|システム状態（/health）と主要画面への導線|必要|FE-SCREEN-001|GET `/health`|
|`/venues`|Venues|競馬場一覧|必要|FE-SCREEN-002|GET `/venues`|
|`/races`|Races|レース一覧（検索）|必要|FE-SCREEN-003|GET `/races`|
|`/races/today`|Today Races|当日出走表の一覧（ページング）|必要|FE-SCREEN-009|GET `/race-entries`|
|`/races/past`|Past Races|任意日出走表＋成績の一覧（ページング）|必要|FE-SCREEN-010|GET `/race-entry-results`|
|`/races/:raceId`|Race Detail|レース詳細（概要/出走表/オッズ/成績/払戻）|必要|FE-SCREEN-004〜008|GET `/races/{id}` + related|
|`/results`|Race Results|任意日の成績一覧（ページング）|必要|FE-SCREEN-011|GET `/race-entry-results`|
|`/admin/oauth-clients`|OAuth Clients|OAuth client 管理＋ service token 発行|必要|FE-ADMIN-001, FE-ADMIN-002|`/admin/oauth-clients*`, POST `/auth/token`|
|`/scrape`|Scrape Console|手動投入/スケジュール/同期/手動スクレイプ依頼|必要|FE-SCRAPE-001〜004|`/scrape/*`|
|`/settings`|Settings|API base URL と token の確認/管理|必要|FE-SETTINGS-001, FE-SETTINGS-002|（主に localStorage）|
|`/test-data`|Docs Test Data Viewer|`docs/test/data` の Markdown（正規化結果・検証レポート）を一覧/詳細表示|不要（閲覧）|FE-SCREEN-012（追加予定）|静的ファイル（manifest + `.md`）|
|`/404`|Not Found|存在しないURLの案内|不要|（機能外）|—|

## 3. 認証・権限の考え方（画面仕様）
- **認証が必要**な画面は token が無い場合 `/login` へ遷移する（遷移元 URL を保持する）。
- `/test-data` は **デバッグ/仕様検証目的**のため、API/認証なしでも閲覧できる（ただし操作系機能は含めない）。






