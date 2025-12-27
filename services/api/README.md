# Keiba AI API (FastAPI)

更新日: 2025-12-27（Asia/Tokyo）

提供された `21_openapi.yaml` に基づき、FastAPI で API サーバーを構築した最小実装です。

## 1. 起動方法（Docker Compose）

```bash
docker compose up --build
```

起動後:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Health: `GET http://localhost:8000/health`

## 2. 認証

### 2.1 Password Login（ユーザー向け）

`POST /auth/login` で access token を返し、refresh token を HttpOnly Cookie (`refresh_token`) に設定します。

### 2.2 Refresh（ローテーション）

`POST /auth/refresh` は Cookie の refresh token を検証し、新しい refresh token を再発行（ローテーション）します。

### 2.3 Client Credentials（scraper-service）

`POST /auth/token` は `client_id / client_secret` により access token を発行します（refresh cookie は発行しません）。

OAuth client は管理者用 API で作成します:

- `POST /admin/oauth-clients`

## 3. 環境変数

`.env.example` を参照してください。

## 4. データ永続化

デフォルトは SQLite を `/app/data/app.db` に作成します（compose の volume で保持）。

## 5. 実装上の注意

- `odds_flg` は OpenAPI 上 `nullable` だが、SQLite の UNIQUE 制約の都合で **DB では -1 に正規化**しています。
  - API レスポンスでは `-1` を `null` に戻します。
  - 既存 DB を使っている場合はマイグレーションが必要です（下記 TODO 参照）。

## 6. TODO（レビュー指摘）

- **DB マイグレーション**
  - 現状は `create_all()` による初期生成のみ。`alembic` を導入してスキーマ変更を安全に適用する。
  - 既存の SQLite volume を使っている場合、今回のスキーマ変更（`odds_flg` 正規化、`legs_key` 追加、UNIQUE 制約追加）に追従できないため、
    - 開発環境: volume を作り直す
    - 本番相当: Alembic で移行

- **テスト/品質ゲート（50_coding_standard.md, 60_ci_cd.md 準拠）**
  - `pytest` のスモーク（auth / scrape / races）
  - `ruff`（check/format）設定の追加（`pyproject.toml`）
  - GitHub Actions など CI の雛形追加

- **運用/可観測性**
  - `/health` を DB/Redis 疎通込みの readiness に拡張（liveness と分離も検討）
  - ログ（JSON）と request_id の付与

- **セキュリティ**
  - `SECRET_KEY` の必須化（production では起動拒否）
  - refresh cookie の `Secure=true` を production で強制（HTTPS 前提）
  - CORS を `*` から許可 origin リストに切替

- **OpenAPI 運用**
  - `docs/21_openapi.yaml` と実装の差分検知（CI で検証）
