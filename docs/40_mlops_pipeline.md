# MLOps Pipeline（収集→学習→評価→登録→配布）

## 1. 目的
- 学習を定期実行し、再現性・監査性を維持したままモデルを更新する
- データ変化やモデル劣化を検知し、ロールバック可能な運用を実現する

## 2. 最初に導入するモデル（v1）
**目的**: 出走馬が「1着になる / ならない」の2値分類（勝率推定）。

- **ラベル**: `race_results.finish_position == 1` を 1、その他を 0（`label_win`）
- **特徴量（リーク無し・最小）**:
  - race: `baba_code`, `race_no`, `distance_m`, `course`, `weather`, `track_condition`, `field_size`, `race_month`, `race_dow`
  - entry: `horse_number`, `post_position`, `handicap_kg`, `body_weight`, `body_weight_diff`, `jockey_name`, `trainer_name`
- **実装**:
  - 学習/登録: `services/pipeline/src/pipeline_service/train_win_classifier.py`
  - 推論API: `GET /ml/win-prob/{race_id}`（Production モデルを使用）

> まずは「勝率推定の土台（実験→検証→登録→デプロイ）」を最短で通し、次に特徴量の高度化（過去戦績/オッズ/指数）へ拡張する。

## 3. 未来情報（リーク）を入力にしないためのルール
### 3.1 禁止（例）
- `race_results` の `finish_position/time_str/margin/last3f/corner*/popularity` 等を特徴量に入れない
- `payouts`（払戻）を特徴量に入れない
- 未来のオッズスナップショット（当該レースの「締切後」「確定後」）を特徴量に入れない

### 3.2 必須（今回の実装で実施）
- 学習データは **`races` + `race_entries` を特徴量**、`race_results.finish_position` は **ラベル計算のみに使用**
- 評価は **時系列分割（time split）**:
  - train: `val_start` より前
  - val: `val_start` 〜 `test_start` 未満
  - test: `test_start` 以降
- 学習スクリプト側で **想定外カラムが混入したら例外**（リーク検知）

## 4. データサイエンティスト向け実験環境
### 4.1 起動（PC）
`docker-compose.pc.yaml` に MLflow（Tracking/Registry）が含まれる。

- MLflow UI: `http://localhost:5000`
- pipeline-service からの接続先: `http://mlflow:5000`（compose 内ネットワーク）

### 4.2 学習（手動実験）
pipeline コンテナ上で以下を実行する（例）:

```bash
docker compose --env-file .env -f docker-compose.pc.yaml run --rm pipeline \
  python -m pipeline_service.train_win_classifier --promote
```

- `--promote` を付けると、検証指標が閾値を満たす場合に Production へ昇格する（昇格ルールは引数で調整可）
- 生成物は MLflow に記録される（run / metrics / model / registry version）

## 5. パイプライン全体像（実装方針）
1. Ingest（既存）: scraper → api-service → DB（races/entries/results/odds/payouts）
2. Validate:
   - 件数/欠損/重複の最小チェック（v1）
   - 将来: Great Expectations 等で拡張
3. Feature:
   - v1: DBから取得できるリーク無し最小特徴量
   - 将来: 「ある時点(as-of)までの情報」だけで特徴量を作る（Feature View / as-of join）
4. Train:
   - v1: LogisticRegression（まず再現性/監査性を優先）
   - 将来: LightGBM 等 + 探索（ただしリーク検知を強化）
5. Evaluate:
   - 分類指標: AUC / PR-AUC / LogLoss / Brier
   - レース単位指標: race_top1_acc（各レースで最大確率を選んだときの的中率）
   - 将来: 収益指標（バックテスト）/ドリフト検知
6. Register:
   - MLflow Tracking に metrics/params/artifacts を保存
   - MLflow Model Registry に version を登録
7. Promote/Deploy:
   - Production へ昇格（手動 or ルールベース）
   - api-service が Production モデルをロードして推論提供（`/ml/win-prob/{race_id}`）

## 6. スケジュール（例）
- daily: 前日分のデータ取り込み・検証・軽量学習
- weekly: フルリトレーニング + ハイパラ探索（必要なら）
- on-demand: サイト変更や障害復旧後の再学習

## 7. 再現性の要件
- データ版：DVC（またはDBスナップショット）で追跡
- コード版：Git commit hash
- 実験：MLflow run id
- モデル：MLflow registry version + 生成時刻
- これらを “1つのレポート” として保存し、後で同じ結果を再現できること

## 8. 昇格（Promotion）ルール（暫定）
- 最低限：検証指標が閾値以上（v1は AUC）
- データ品質チェックを通過
- 重大な欠損が無い
- 重大なモデル劣化が無い（過学習、ドリフト）

## 9. アラート（必須）
- 学習失敗（連続N回）
- データ品質失敗
- モデル性能劣化
