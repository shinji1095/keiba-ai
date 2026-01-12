# docs/ 運用ガイド

このフォルダは **保守・運用可能な競馬AI** を実現するための「合意事項（意思決定）」「設計」「運用手順」を集約します。
MLOps とマイクロサービスでは「動くコード」より「継続して動かし続けるための判断基準」が重要になるため、
ドキュメントを **コードと同じ品質ゲート（レビュー・CI）** で扱います。

## 更新ルール（推奨）
- 変更は PR で実施し、少なくとも 1 名レビューを通す
- 仕様変更は **まず docs を更新** → その後に実装・テストを更新（TDDと整合）
- 破壊的変更（データスキーマ、API、スクレイピング頻度、学習パイプライン）は
  `docs/90_decisions.md` に Decision Log（ADR風）を追記する

## ドキュメント一覧（推奨読了順）
1. `00_project_concept.md`（目的・前提・成功指標・非目標）
2. `01_glossary.md`（用語集）
3. `02_feature_list.csv`（機能一覧：現状の実装機能を棚卸し）
4. `03_non_functional_requirements.md`（非機能要件：性能/可用性/セキュリティ/運用）
5. `10_architecture.md`（サービス境界・データフロー・配置）
6. `11_frontend_screen_list.md`（画面リスト：機能と対応付け）
7. `12_frontend_screen_transitions.md`（画面遷移：認証リダイレクト含む）
8. `20_data_contracts.md`（DB・API・イベントの契約）
9. `30_scraping_policy.md`（負荷抑制・取得タイミング・障害検知）
10. `31_scraping_flow.md`（スクレイピング→正規化→保存フロー）
11. `32_http_request_data_mapping.md`（HTTPリクエスト対応表）
12. `40_mlops_pipeline.md`（学習・評価・登録・配布・再現性）
13. `50_coding_standard.md`（規約・レビュー・TDDの約束）
14. `60_ci_cd.md`（CI/CD、ゲート、デプロイ）
15. `70_operations_runbook.md`（監視、バックアップ、復旧、SLO）
16. `80_test_guideline.md`（テスト契約・設計方針・実行方法）
17. `90_decisions.md`（決定ログ：いつ・誰が・なぜ決めたか）

## オーナーシップ（推奨）
- Architecture/Infra: PM + Backend Lead
- Data Contracts: Backend Lead + ML Lead
- Scraping Policy: Scraping Owner + PM
- MLOps Pipeline: ML Lead + Infra
- Coding/CI/CD: Tech Lead
- Runbook: Ops Owner
