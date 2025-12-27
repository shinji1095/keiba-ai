# CI/CD（品質ゲート・ビルド・デプロイ）

## 1. 目的
- main ブランチの品質を機械的に担保する
- “壊れたものをデプロイしない” を最優先する

## 2. CI（Pull Request で必須）
- Python:
  - ruff check / format --check
  - pytest
- Frontend:
  - npm ci
  - npm run build
- （将来）コンテナビルド、SBOM、脆弱性スキャン

## 3. CD（段階導入）
- Phase 1（手動デプロイ）:
  - Ubuntu PC: `docker compose --env-file .env -f deploy/compose/compose.pc.yaml up -d --build`
  - Pi: `docker compose --env-file .env -f deploy/compose/compose.pi.yaml up -d --build`
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
