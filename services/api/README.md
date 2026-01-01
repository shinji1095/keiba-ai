更新日: 2025-12-27

# Keiba AI API (FastAPI)

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

### 2.1 User Registration（ユーザー向け）

`POST /auth/register` でユーザーを作成し、access token を返します。refresh token は HttpOnly Cookie (`refresh_token`) に設定します。

### 2.2 Password Login（ユーザー向け）

`POST /auth/login` で access token を返し、refresh token を HttpOnly Cookie (`refresh_token`) に設定します。

### 2.3 Refresh（ローテーション）

`POST /auth/refresh` は Cookie の refresh token を検証し、新しい refresh token を再発行（ローテーション）します。

### 2.4 Client Credentials（将来予約）

`POST /auth/token` は `client_id / client_secret` により access token を発行します（refresh cookie は発行しません）。  
api-service ⇔ scraper-service は現時点では認証不要（将来 mTLS で対応予定）。

## 3. 環境変数

`.env.example` を参照してください。scraper への転送を有効化する場合は以下を追加します。

- `SCRAPER_FORWARD_ENABLED`（`true` で api→scraper 転送を有効化）
- `SCRAPER_CONTROL_BASE_URL`（例: `http://scraper-service:8080`）
- `SCRAPER_FORWARD_TIMEOUT_SEC`（既定: `5`）
- `SCRAPER_MTLS_CERT` / `SCRAPER_MTLS_KEY` / `SCRAPER_MTLS_CA_CERT`（mTLS 用、任意）

## 4. データ永続化

デフォルトは SQLite を `/app/data/app.db` に作成します（compose の volume で保持）。

## 5. 開発用メモ

- api-service ⇔ scraper-service 間の /scrape 取り込みは **認証不要**（将来対応予定）
- scraper 側の受け口は `/control/ingest/*`（認証不要）
- Bearer 認証: `Authorization: Bearer <JWT>`

## テスト・品質ゲート（docs/50_coding_standard.md, docs/60_ci_cd.md 準拠）

ローカルでの最低限のゲートは以下です。

- ruff check（lint）
- ruff format --check（format）
- pytest（テスト）

### ローカル実行

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
ruff check .
ruff format --check .
pytest
```

### CI（GitHub Actions）

`.github/workflows/ci.yml` に、上記ゲート（ruff + pytest）を実装しています。

## TODO（スクレイピング連携）

- [ ] 定期実行 on/off と `baba_codes` 管理の永続化（api-service 実装）
- [ ] `GET /scrape/schedule` の返却内容実装（enabled, baba_codes, interval_days など）

## TODO（テスト/品質ゲート・セキュリティ）

### テスト/品質ゲート
- [ ] 重要ユースケースのテスト拡充（例: odds/payouts の upsert、pagination、error envelope）
- [ ] OpenAPI と実装の差分検知（CIで `docs/21_openapi.yaml` と実装の同期をチェック）
- [ ] カバレッジ目標の設定（例: 70% 以上）と coverage レポート出力
- [ ] pre-commit の導入徹底（ruff / ruff-format / yaml / 大容量ファイル禁止）

### セキュリティ
- [ ] 本番環境では `SECRET_KEY` のデフォルト値禁止（起動時に強制チェック）
- [ ] CORS を最小化（`CORS_ALLOW_ORIGINS` を "*" ではなく許可ドメインに限定）
- [ ] Refresh Cookie の `Secure` を本番で有効化（HTTPS前提）し、SameSite/Domain/Path を運用に合わせて固定
- [ ] 認証系エンドポイントのレート制限（/auth/login, /auth/token, /auth/refresh）
- [ ] セキュリティヘッダ（例: HSTS, X-Content-Type-Options など）の付与方針と実装
