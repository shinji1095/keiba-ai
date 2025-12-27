# Coding Standard（TDD / 規約 / レビュー）

## 1. 基本方針
- 仕様（docs）→ テスト → 実装 の順で進める（TDD）
- “読みやすさ” と “変更容易性” を優先（マイクロサービスの寿命を延ばす）

## 2. Python（PEP8準拠）
- ベースは PEP8（4スペース、行長 79、docstring は 72 を目安）
- 命名: 関数/変数は snake_case、クラスは CapWords、定数は UPPER_SNAKE_CASE
- import 順序: 標準ライブラリ → サードパーティ → ローカル（空行で区切る）
- docstring: Google フォーマットを使用（公開モジュール/クラス/関数は必須）
- formatter/linter: Ruff（PEP8 相当の規約をルール化）
- テスト: pytest
- 例外: 例外は握りつぶさず、エラーコードとログを残す
- 設定: 環境変数（.env）を基本とし、ハードコード禁止

## 3. TypeScript / React
- strict: true（tsconfig）
- API呼び出しは 1 箇所に集約（client層）
- UI とロジックを分離（hooks / services）

## 4. ブランチ戦略（推奨）
- main: 常にデプロイ可能
- dev: 開発ブランチ（作業ブランチの成果を一度集約）
- feature/*: 作業ブランチ

## 5. PR運用（推奨）
- PRは小さく（レビュー可能なサイズ）
- 必ず以下を含める:
  - 変更理由（Why）
  - 影響範囲
  - テスト結果（CI）
  - ドキュメント更新（必要なら）

## 6. 自動化（最低限）
- pre-commit: ruff / yamlチェック / 大容量ファイル禁止
- CI: lint + test + build を必須ゲートにする
