# URLパターン（正規化前提）

更新履歴
- 2026-01-03: 初版作成。
- 2026-01-03: 添付HTML（keiba.go.jp PC向けページ）から、オッズページのHTML構造・必要パラメータを追記（`odds_flg` 等はページ内リンクから確認）。

## 前提
- 取得キーは `babaCode` + `raceDate` + `raceNo`（レース一覧のみ `babaCode` + `raceDate`）とする。
- 同一レースについて、出馬表・各種オッズは同じキーで URL を組み立て可能。

## パラメータ定義（PC向け）
- `k_raceDate`: `YYYY/MM/DD` を URL エンコード（例: `2026%2F01%2F02`）
- `k_babaCode`: 競馬場コード（例: `27`）
- `k_raceNo`: レース番号（例: `2`）

## PC向け：主要エンドポイント

### 出馬表
- `https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/DebaTable?k_raceDate=...&k_raceNo=...&k_babaCode=...`

### オッズ（単勝・複勝）
- `https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/OddsTanFuku?k_raceDate=...&k_raceNo=...&k_babaCode=...`
- HTML構造（添付HTMLより）:
  - `#odd_content table.odd_popular_table_02` に1頭1行の表
  - `複勝オッズ` は **2列（最小・最大）** に分割される（`colspan`）

### オッズ（枠連）
- `https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/OddsWakuLenFukuTan?k_raceDate=...&k_raceNo=...&k_babaCode=...`
- HTML構造（添付HTMLより）:
  - `#odd_content ul.odd_horse_number_list table` が枠番ごとに分割され、行として相手枠とオッズを列挙する
  - 当ページには `人気` 列が無いため、人気はオッズ昇順で派生させる（必要に応じて別表示/別パラメータで取得）

### オッズ（馬連複）
- `https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/OddsUmLenFuku?k_raceDate=...&k_raceNo=...&k_babaCode=...`
- HTML構造（添付HTMLより）:
  - `#odd_content table.odd_ranking_table` が複数存在し、**全組（12頭なら66組）** を分割表示する
  - 各行は `組合せ / オッズ / 人気` の3列

### オッズ（馬連単）
- `https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/OddsUmLenTan?k_raceDate=...&k_raceNo=...&k_babaCode=...`
- HTML構造（添付HTMLより）:
  - `#odd_content table.odd_ranking_table` が複数存在し、**全組（12頭なら132組）** を分割表示する
  - 各行は `組合せ / オッズ / 人気`

### オッズ（ワイド）
- `https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/OddsWide?k_raceDate=...&k_raceNo=...&k_babaCode=...`
- HTML構造（添付HTMLより）:
  - `#odd_content table.odd_ranking_table` が複数存在し、**全組（12頭なら66組）** を分割表示する
  - 各行は `組合せ / オッズ（範囲） / 人気`

## SP向け（参考・未検証）
- `https://sp.keiba.go.jp/KeibaWebSP/TodayRaceInfo/...`
- 本作業環境では `sp.keiba.go.jp` への直接取得が安定しないため、**添付HTML（PC向けページ）を正とする**。
- SP向けのページング/並び替えパラメータ（`k_pageNum` 等）は推測の域を出ないため、実装時は実アクセスで確認する。
