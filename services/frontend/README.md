# 競馬AI Dashboard (React + TypeScript + Vite)

作成日: 2025-12-27（Asia/Tokyo）  
更新日: 2025-12-28（Asia/Tokyo）

更新履歴
- 2025-12-27: 初版作成。
- 2025-12-28: Scrape Console の手動実行と状態確認を追記。


`21_openapi.yaml` に定義されたエンドポイント（認証: Bearer JWT / Refresh: HttpOnly Cookie）を操作するためのダッシュボードです。

## 構成

- React + TypeScript + Vite
- TanStack Query (データ取得/キャッシュ)
- Docker (node:20-alpine) / port 5173

## 起動（Docker）

```bash
docker compose up --build
```

環境変数で API のベースURLを指定できます（例: reverse-proxy が `/api` を公開している場合）:

```bash
VITE_API_BASE_URL=http://localhost:8000/api docker compose up --build
```

ブラウザで `http://localhost:5173` を開きます。

## 起動（ローカル）

```bash
npm ci
npm run dev -- --host 0.0.0.0 --port 5173
```

## 使い方

1. `/register` で `POST /auth/register` を実行してユーザーを作成し、user token を取得します。
2. `/login` で `POST /auth/login` を実行して user token を取得します。
3. 401 の場合、user token 使用中のみ `POST /auth/refresh` を自動実行してリトライします。
4. `OAuth Clients` で client_credentials 用のクライアントを作成し、`/auth/token` で service token を発行できます。
5. `Scrape Console` で `/scrape/*` の投入や手動実行タスクの依頼、状態確認を行えます。

## Scrape Console（手動実行/状態確認）

- 画面: `Scrape Console`（`/scrape`）
- token: `Settings` で Service token を設定し、`Service token` モードで実行する
- 手動実行タスク: `POST /scrape/manual-tasks`
- 差分同期トリガ: `POST /scrape/sync`
- 定期実行状態: `GET /scrape/schedule`
- 同期状態: `GET /scrape/sync/status`
- 直接投入: `POST /scrape/races` ほか `/scrape/*`
- 送信ボディ: 画面のテンプレートJSONをベースに編集して送信する

## フォルダ構成（保守運用向け）

- `src/api/` : OpenAPI 由来の型と API 呼び出し
- `src/app/` : アプリ全体（認証・ルーティング・レイアウト）
- `src/features/` : 画面単位（Overview / Venues / Races / Admin / Scrape / Settings）
- `src/shared/` : 再利用 UI

## 注意

- Refresh token は HttpOnly Cookie を前提としているため、フロントから参照できません。
- CORS / Cookie 属性（SameSite / Secure）などは API 側設定に依存します。

## TODO（運用・保守の観点で優先度高）

- [ ] `package-lock.json` をコミットし、Dockerfile を `npm ci` ベースに変更してビルド再現性を担保する（dev/prod の multi-stage も検討）。
- [ ] OpenAPI から TypeScript 型を自動生成する仕組みを導入する（例: `openapi-typescript`）＋ CI で差分検知して `src/api/generated.ts` の乖離を防ぐ。
- [ ] 認証トークンの保管方針を最終決定する（現状は localStorage。XSS リスクを踏まえ、可能ならメモリ保持＋refresh運用へ寄せる）。
- [ ] エラー境界（ErrorBoundary）と共通のエラー通知（トースト等）を追加し、運用時の障害切り分けを容易にする。
- [ ] 最低限のUI/E2Eテスト（Playwright 等）を追加し、主要画面（Login / Races / Admin / Scrape）の回帰を防止する。
- [ ] API のタイムアウト/リトライ方針（ネットワーク断・429 等）を運用契約として整理し、実装にも反映する。
