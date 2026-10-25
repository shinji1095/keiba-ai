# 競馬AI Dashboard (React + TypeScript + Vite)

作成日: 2025-12-27（Asia/Tokyo）
更新日: 2026-01-04（Asia/Tokyo）

更新履歴
- 2025-12-27: 初版作成。
- 2026-01-02: 同期UI・手動スクレイプ投入を追加。
- 2026-01-04: Test Data Viewer（/test-data）を追加し、docs/test/data を可視化。

`docs/21_openapi.yaml` に定義されたエンドポイント（認証: Bearer JWT / Refresh: HttpOnly Cookie）を操作するためのダッシュボードです。

## 構成

- React + TypeScript + Vite
- TanStack Query (データ取得/キャッシュ)
- 通常運用: NGINXで静的配信（port 80）。開発・テスト: Playwrightベースのdevelopmentターゲット。

## 起動（Docker）

リポジトリルートで `docker compose up -d --build` を実行し、
`http://localhost` を開きます。APIは同じ入口の `/api/` です。
ビルド時に `docs/test/data/` を取り込みます。

開発・テスト用イメージは次で作成できます。

```bash
docker build --target development -f services/frontend/Dockerfile -t keiba-frontend-test .
docker run --rm keiba-frontend-test npm run test:unit
```

## 起動（ローカル）

```bash
npm ci
# docs/test/data を public/ にコピー（Test Data Viewer 用）
mkdir -p public/docs/test/data
cp -r ../../docs/test/data/. public/docs/test/data/
npm run dev -- --host 0.0.0.0 --port 5173
```

## 使い方

1. `/register` で `POST /auth/register` を実行してユーザーを作成し、user token を取得します。
2. `/login` で `POST /auth/login` を実行して user token を取得します。
3. 401 の場合、user token 使用中のみ `POST /auth/refresh` を自動実行してリトライします。
4. 「外部連携」で連携先を登録し、外部連携用トークンを発行できます。
5. 「データ収集」で自動収集とデータ同期を設定し、データを手動で登録できます。
6. 「データ収集」の「手動収集」で、競馬場や開催日を指定して収集を依頼できます。
7. 「テストデータ」で `docs/test/data/` の正規化データを閲覧できます（TDD用フィクスチャ）。
8. 「収集スケジュール」で自動収集の設定内容とオッズの収集予定を確認できます。

## フォルダ構成（保守運用向け）

- `src/api/` : OpenAPI 由来の型と API 呼び出し
- `src/app/` : アプリ全体（認証・ルーティング・レイアウト）
- `src/features/` : 画面単位（Overview / Venues / Races / Admin / Scrape / TestData / Settings）
- `src/shared/` : 再利用 UI（ErrorBox / Loading / JsonView / MarkdownView）
- `../../docs/test/data/` : テストデータの原本（ビルド時にpublicへ取り込み）

## 注意

- Refresh token は HttpOnly Cookie を前提としているため、フロントから参照できません。
- CORS / Cookie 属性（SameSite / Secure）などは API 側設定に依存します。
- Test Data Viewer は `docs/test/data/` を `public/` にコピーして静的配信します（ビルド時に含まれる）。

## TODO（運用・保守の観点で優先度高）

- [ ] OpenAPI から TypeScript 型を自動生成する仕組みを導入する（例: `openapi-typescript`）＋ CI で差分検知して `src/api/generated.ts` の乖離を防ぐ。
- [ ] 認証トークンの保管方針を最終決定する（現状は localStorage。XSS リスクを踏まえ、可能ならメモリ保持＋refresh運用へ寄せる）。
- [ ] エラー境界（ErrorBoundary）と共通のエラー通知（トースト等）を追加し、運用時の障害切り分けを容易にする。
- [ ] UI/E2E テストの拡充（主要画面の回帰防止 + 主要 API のリクエスト内容検証）。
- [ ] API のタイムアウト/リトライ方針（ネットワーク断・429 等）を運用契約として整理し、実装にも反映する。
- [ ] MarkdownView の本格実装（react-markdown + remark-gfm）でコードハイライト・リンク・画像対応を追加。
