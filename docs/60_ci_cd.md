# CI/CD（品質ゲート・ビルド・デプロイ）

## 1. 目的
- main ブランチの品質を機械的に担保する
- “壊れたものをデプロイしない” を最優先する

## 2. CI（Pull Request で必須）
- テストは **Docker Compose 環境内**で実行する（api/scraper/webの開発ターゲットを対象）
- Python:
  - ruff check / format --check
  - pytest（docker compose exec）
- Frontend:
  - npm ci / npm run build（docker compose exec）
  - npm run test:unit / npm run test:e2e（docker compose exec）
- （将来）コンテナビルド、SBOM、脆弱性スキャン

## 3. CD（段階導入）
- Phase 1（手動デプロイ）:
  - PC: `docker compose up -d --build`
- Phase 2（自動化）:
  - main マージでイメージをビルドし、レジストリへpush
  - ホスト側は “pull & restart” のみ

## 4. Secrets 管理（推奨）
- .env を Git 管理しない
- 本番は OS の secret store や vault を検討（必要になった時点で）

## 5. リリース手順（暫定）
- tag を切る（例: v0.1.0）
- changelog を更新
- compose を更新（イメージタグ）

v1.0.0の実行コマンドは `80_test_guideline.md`、CI設定はルート `.github/workflows/ci.yml` を参照。
