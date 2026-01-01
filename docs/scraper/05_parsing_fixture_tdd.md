# 05 オッズ構造・正規化・フィクスチャ収集/TDD方針

作成日: 2025-12-27（Asia/Tokyo）

---

## 0. このドキュメントの位置づけ

- Odds*（7ページ）の **パース仕様**（抽出ルール・正規化）を固定し、TDD（フィクスチャ→単体テスト）に落とすためのメモ。
- ここでいう「式別」は **ページ単位**を指す（単複・枠連は1ページ内に複数式別が同居する）。

---

## 1. フィクスチャ選定（A2：確定）

### 1.1 正常系（7ページすべて到達できる）
- 開催: 大井（`k_babaCode=20`）
- 日付: `2025/12/26`
- R: `3`

**対象URL（PC版）**
- 単複: `OddsTanFuku?k_babaCode=20&k_raceDate=2025%2F12%2F26&k_raceNo=3`
- 枠連: `OddsWakuLenFukuTan?k_babaCode=20&k_raceDate=2025%2F12%2F26&k_raceNo=3`
- 馬連: `OddsUmLenFuku?k_babaCode=20&k_raceDate=2025%2F12%2F26&k_raceNo=3`
- 馬単: `OddsUmLenTan?k_babaCode=20&k_raceDate=2025%2F12%2F26&k_raceNo=3`
- ワイド: `OddsWide?k_babaCode=20&k_raceDate=2025%2F12%2F26&k_raceNo=3`
- 三連複: `Odds3LenFuku?k_babaCode=20&k_raceDate=2025%2F12%2F26&k_raceNo=3`
- 三連単: `Odds3LenTan?k_babaCode=20&k_raceDate=2025%2F12%2F26&k_raceNo=3`

> 注意: URLは `https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/` をプレフィックスとして付与する。

### 1.2 異常系（Internal Error 再現）
- 開催: 大井（`k_babaCode=20`）
- 日付: `2025/12/25`
- R: `6`
- 現象: **三連複ページ（Odds3LenFuku）が Internal Error**（導線クリックで観測、確認日 2025-12-27）

---

## 2. Odds* 抽出の共通前提

- ページ上部に `日付 / 場 / 第◯競走 / 発走時刻` が表示される  
  → `race_key` と `start_time` の冗長取得元になる（URLだけに依存しない）
- 実データは概ね「組合せ / オッズ / 人気」を行として持つ
- 3連系は行数が非常に多く、ページ内で「1〜25件」のように分割される（ページングを跨いで同一仕様で抽出）
- ワイド/複勝は **レンジ表現**（例: `1.2-1.5`）が出る

---

## 3. ページ別の行抽出ルール（A1：要約）

※厳密な CSS セレクタは、フィクスチャ取得後に `BeautifulSoup` で最小の依存に落とす（class名の固定に依存しすぎない）。

### 3.1 OddsTanFuku（単複）
- **単勝（tansho）**: `馬番` 単位の行 → `legs=[horse_no]`
- **複勝（fukusho）**: `馬番` 単位の行 → `legs=[horse_no]`（odds はレンジになることがある）

### 3.2 OddsWakuLenFukuTan（枠連）
- ページ内に 2 ブロックが存在する想定
  - **枠連複（wakuren）**
  - **枠連単（wakutan）**
- マトリクス表示の場合、`枠番 i` × `枠番 j` のセルを **ペア行**に正規化する  
  - wakuren: `legs=[min(i,j), max(i,j)]`, `is_ordered=false`
  - wakutan: `legs=[i,j]`, `is_ordered=true`

### 3.3 OddsUmLenFuku（馬連）/ OddsUmLenTan（馬単）/ OddsWide（ワイド）
- 2頭の組合せ単位
  - umaren / wide: `legs` は昇順（`is_ordered=false`）
  - umatan: `legs` は表示順を維持（`is_ordered=true`）

### 3.4 Odds3LenFuku（三連複）/ Odds3LenTan（三連単）
- 3頭の組合せ単位（ページング跨ぎで同一仕様）
  - sanrenpuku: `legs` は昇順（`is_ordered=false`）
  - sanrentan: `legs` は表示順を維持（`is_ordered=true`）

---

## 4. レンジ表現の正規化（A3：確定）

### 4.1 ルール
- odds 文字列が **単値**の場合  
  - `odds_min = odds_max = float(value)`
- odds 文字列が **レンジ**の場合（ワイド/複勝で出現）  
  - 許容区切り: `-`, `–`, `〜`, `～`（前後の空白は無視）
  - `odds_min = float(left)`, `odds_max = float(right)`（`min<=max` を保証）
- 欠損（例: 空文字, `-`, `—`, `発売なし`）は `odds_min = odds_max = NULL` とする

### 4.2 JSON（正規化後）の例
- 単値（馬連など）
```json
{"bet_type":"umaren","legs":[1,7],"is_ordered":false,"odds_min":12.3,"odds_max":12.3,"popularity":4}
```

- レンジ（ワイド/複勝など）
```json
{"bet_type":"wide","legs":[1,7],"is_ordered":false,"odds_min":2.1,"odds_max":2.5,"popularity":3}
```

---

## 5. 払戻金の正規化（A4：確定）

### 5.1 取得元の優先順位
1. `RefundMoneyList`（日付×開催場） … **推奨（行指向で解析が容易）**
2. `RaceMarkTable`（レース） … フォールバック（レイアウト崩れがあるため優先度低）

### 5.2 正規化単位
- **bet_type × legs × is_ordered** を 1 レコードとする  
- 追加属性: `payout_yen`, `popularity`（人気がない場合は NULL）

### 5.3 bet_type と legs の定義（払戻）
|表示|bet_type|legs 例|is_ordered|legsの意味|
|---|---|---:|:---:|---|
|単勝|tansho|[14]|false|馬番|
|複勝|fukusho|[6]|false|馬番|
|枠連複|wakuren|[1,2]|false|枠番|
|馬連複|umaren|[6,14]|false|馬番|
|枠連単|wakutan|[1,2]|true|枠番|
|馬連単|umatan|[14,6]|true|馬番|
|ワイド|wide|[6,14]|false|馬番|
|三連複|sanrenpuku|[4,6,14]|false|馬番|
|三連単|sanrentan|[14,6,4]|true|馬番|

> legs の「枠番/馬番」の違いは bet_type で判別する（追加列が必要なら拡張）。

### 5.4 RefundMoneyList のパース注意点（状態機械）
- `複勝` と `ワイド` は 1 行に 1 件ではなく、**式別名が省略された継続行**が出る  
  - 例:  
    - `複勝 14 170円 ...` の後に `6 110円 ...` のような行が続く  
    - `ワイド 6-14 220円 ...` の後に `4-14 840円 ...` のような行が続く  
- 実装では `current_bet_type` を保持し、
  - 行頭に式別名がある→ `current_bet_type` を更新して1件生成
  - 行頭に式別名がない→ `current_bet_type` を継続して1件生成
  のように処理する

---

## 6. フォールバック/例外（A2の補足）

- Odds3LenFuku が Internal Error（5xx）になるケースがある  
  → オッズは欠損扱いにする（ログ必須）。レース確定後の `RefundMoneyList` から払戻は取得できるため、教師データ/報酬は作れる。
- 「ご指定のオッズは存在しません。」等の定型文は発売なし/欠損扱いにする（リトライしない）
- 「現在、情報を表示できません」は一時的な可能性があるため、少回数のリトライで回復を試みる

---

## 7. B1: HTMLフィクスチャ収集（仕様確定）

ここでは「**パーサの回帰テスト用**」に HTML を固定するための要件を定義する。
（発走時刻基準の t_minus_60m/t_minus_30m/t_minus_20m/t_minus_10m/t_minus_5m/t_minus_1m/final 収集は運用要件であり、フィクスチャ用途では必須ではない。ただし、将来の時系列テストのために `snapshot_kind` をメタとして残す。）

### 7.1 fixtures ディレクトリ構成（推奨）

```
fixtures/
  README.md
  manifest.yml              # 取得“計画”（入力）
  manifest_log.csv          # 取得“結果”（出力ログ）
  2025-12-26_20_03/          # YYYY-MM-DD_babaCode_RR
    pc/                     # device=pc
      odds_tanfuku__flg=4__snap=t_minus_10m.html
      odds_tanfuku__flg=5__snap=t_minus_10m.html
      odds_waku__flg=6__snap=t_minus_10m.html
      odds_waku__flg=5__snap=t_minus_10m.html
      odds_umaren__flg=auto__snap=t_minus_10m.html
      ...
    sp/                     # device=sp（フォールバック用。未使用でもOK）
      ...
  2025-12-25_20_06/          # 異常系
    pc/
      odds_3renpuku__flg=auto__snap=t_minus_10m__expected=5xx.html
```

> 重要: `OddsTanFuku` / `OddsWakuLenFukuTan` は **1ページ内に2式別** が同居する。
> - fixture のファイル名 `odds_tanfuku` / `odds_waku` は **page_type（ページ種別）** を表す。
> - 正規化後の `bet_type` は **別々** に出力する（`tansho` と `fukusho`、`wakuren` と `wakutan`）。


> 補足
> - `RR` は 2桁ゼロ埋め（例: 03）。
> - 取得結果ログは **必ず append-only**（上書きしない）にする。

### 7.2 manifest.yml（入力）スキーマ（確定）

YAML を「取得計画」として使う（人が編集しやすく、追加メタデータが載せやすい）。

```yml
- name: odds_tanfuku_horse_order
  race_key: {race_date: "2025-12-26", baba_code: 20, race_no: 3}
  device: pc                 # pc|sp
  page_name: OddsTanFuku      # TodayRaceInfo の PageName
  odds_flg: 4                 # 数字 or null（未指定=自動）
  snapshot_kind: t_minus_10m  # t_minus_60m|t_minus_30m|t_minus_20m|t_minus_10m|t_minus_5m|t_minus_1m|final
  url: "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/OddsTanFuku?...&odds_flg=4"
  out: "2025-12-26_20_03/pc/odds_tanfuku__flg=4__snap=t_minus_10m.html"
  expect:
    http_status: 200
  note: "単複（馬番順）"
```

#### 必須フィールド
- `name`, `race_key`, `device`, `page_name`, `url`, `out`

#### 任意フィールド
- `odds_flg`（未指定なら `auto` 扱いとして out 名にも `flg=auto` を使う）
- `snapshot_kind`（未指定は `captured_at` と `races.start_time` から最近傍に正規化。`captured_at >= races.start_time` は `final`）
- `expect.http_status`（異常系 fixture のときだけ明示）

### 7.3 manifest_log.csv（出力ログ）スキーマ（確定）

1取得=1行で記録し、テスト/再現性の根拠とする。

|列|意味|
|---|---|
|name|manifest.yml の name|
|out_path|保存先|
|url|取得URL（リダイレクト後も別列に残せるなら残す）|
|captured_at|ISO-8601（JST推奨）|
|http_status|HTTP status|
|sha256|レスポンス body の sha256|
|content_type|レスポンスヘッダ（あれば）|
|content_encoding|gzip 等（あれば）|
|note|任意メモ|

### 7.4 odds_flg の棚卸しと「固定する表示モード」方針

フィクスチャ/TDD では、**表示モードが変わっても壊れない**ことが理想だが、初期実装ではまず「固定する表示モード」を決めて安定稼働させる。

#### 7.4.1 現時点で確定している odds_flg（事実）

|PageName|mode|odds_flg|備考|
|---|---|---:|---|
|OddsTanFuku|馬番順|4|確定（source_shared/13）|
|OddsTanFuku|人気順|5|確定（source_shared/13）|
|OddsWakuLenFukuTan|枠番順（マトリクス）|6|確定（source_shared/13）|
|OddsWakuLenFukuTan|人気順（ランキング）|5|確定（source_shared/13）|

#### 7.4.2 未確定の odds_flg（わからない）

以下は共有資料内に「値の断定」がなく、現時点では **わからない**。

- `OddsUmLenFuku` / `OddsUmLenTan` / `OddsWide` / `Odds3LenFuku` / `Odds3LenTan`

#### 7.4.3 棚卸しのやり方（フィクスチャだけで完結）

フィクスチャ取得後、HTML上部のタブ/リンク（例: 「馬番順」「人気順」）の `href` を走査して `odds_flg` を採番する。
（=ブラウザの手作業ではなく、**fixture → 解析スクリプト**で自動集計する）

成果物: `docs/odds_flg_inventory.csv`（後日追加予定）

### 7.5 最小フィクスチャセット（B2のTDDに必要）

#### 7.5.1 正常系（A2で確定）
- race_key: 大井 2025/12/26 3R
- 7URL ×（可能なら）2表示モード
  - TanFuku: flg=4/5
  - WakuLenFukuTan: flg=6/5
  - その他: flg は棚卸し後に「安定モード1つ」+「代替モード1つ」を追加

#### 7.5.2 異常系（A2で確定）
- race_key: 大井 2025/12/25 6R
  - Odds3LenFuku: 5xx / Internal Error（再現フィクスチャ）

#### 7.5.3 追加で欲しいケース（推奨）
共有資料内では未確認のため、ここは **推測ですが**、実運用で高頻度に出るため早期に集めた方がよい。

- 出走取消/除外があるレース（オッズ表記が変わる可能性）
- 頭数が少ないレース（枠連マトリクスの形が変わる可能性）
- 「発売なし」定型文が出る式別（0件扱いの確定）

---

## 8. B2: Oddsパーサ（TDD設計確定）

### 8.1 パーサの入出力（最小契約）

入力: HTML（bytes） + fixtureメタ（race_key, page_name, odds_flg, snapshot_kind, device, url）

出力: `source_shared/20_parser_normalization_contracts.md` の Odds スキーマ（配列）。

> 方針
> - 解析に必要な `race_key` は、まず URL から取得し、次に HTML ヘッダで**一致確認**する（不一致なら警告ログ）。
> - HTML の class/id は変更されやすいので、初期実装は「テキストパターン」に寄せる（例: `\d+-\d+`、`\d+\.\d+` など）。

### 8.2 テスト構成（goldenテスト）

```
tests/
  fixtures/                 # 7章の fixtures を参照（git submodule でも可）
  expected/
    odds_tanfuku_horse_order.json
    odds_waku_matrix.json
    ...
  test_odds_parsers.py
```

#### 8.2.1 期待値JSONのルール
- 期待値は「そのfixtureの**正規化結果の完全一致**」で固定する（golden）。
- ソートは決定的にする（例: `bet_type`, `legs`, `is_ordered`, `popularity` の順）。
- 数値の丸めは行わない（HTMLに出ている値を float で保持）。

### 8.3 最小テストマトリクス（必須）

|bet_type|入力ページ|最低1ケース|追加（表示モード差）|
|---|---|---|---|
|tansho|OddsTanFuku|馬番順 flg=4|人気順 flg=5|
|fukusho|OddsTanFuku|馬番順 flg=4（レンジ含む可能性）|人気順 flg=5|
|wakuren|OddsWakuLenFukuTan|マトリクス flg=6|人気順 flg=5|
|wakutan|OddsWakuLenFukuTan|マトリクス flg=6|人気順 flg=5（存在するなら）|
|umaren|OddsUmLenFuku|auto（棚卸し後に固定）|代替モード（棚卸し後）|
|umatan|OddsUmLenTan|auto（棚卸し後に固定）|代替モード（棚卸し後）|
|wide|OddsWide|auto（レンジを含むfixture必須）|代替モード（棚卸し後）|
|sanrenpuku|Odds3LenFuku|auto（大量行/セクション結合）|5xx fixture（異常系）|
|sanrentan|Odds3LenTan|auto（大量行/セクション結合）|代替モード（棚卸し後）|

### 8.4 パースの合否基準（assert）

- `race_key` が埋まっている
- `bet_type` ごとに `legs` の長さが正しい（1/2/3）
- `is_ordered` が式別に一致する
- `odds_min/odds_max` がルールに合う（単値は同値、レンジは min<max、欠損は両方null）
- `popularity` があるfixtureでは int で取れる（ない場合は null 許容）

### 8.5 エラー処理（TDDで固定する）

#### 8.5.1 Soft欠損（200 + 定型文）
- 期待: 例外にしない。`items=[]` で返し、メタに `status="no_data"` を残す（実装側の設計）。

#### 8.5.2 5xx / Internal Error
- 期待: 例外にせず `items=[]` + `status="server_error"` を返す（運用で欠損扱いにするため）。

> 注意
> 上記 `status` は DB 正規化JSONの契約（source_shared/20）には含めていない。
> 実装では「戻り値を (items, meta) の2要素にする」などで扱う。


---

## 9. B3: RefundMoneyList パーサ（TDD設計確定）

### 9.1 目的

- `RefundMoneyList`（日付×開催場）から **全レースの払戻**を抽出し、`bet_type×legs×payout_yen` に正規化して `payouts` に入れる。
- `RaceMarkTable` 側にも払戻があるが、**1ページで全レースが取れる**ため `RefundMoneyList` を主とする（A4確定）。

### 9.2 パーサ入出力（最小契約）

入力: HTML（bytes） + fixtureメタ（`race_date`, `baba_code`, `device`, `url`, `scraped_at`）

出力: `source_shared/20_parser_normalization_contracts.md` の **Payout スキーマ配列**（複数 race_no を含む）。

> 注意
> - `RefundMoneyList` は race_no を複数含むため、出力は「race_key ごと」の配列ではなく **ページ全体→複数 race_key** の配列になる。
> - DB反映は `race_key` で `race_id` を引ける前提（B4で確定）。

### 9.3 重要な落とし穴（A4で観測済み）

- **式別名の省略（継続行）**
  - 例: 複勝/ワイドは的中数が複数のため、2行目以降で「複勝」等のラベルが空欄になる場合がある。
  - 対策: 行を上から処理し、直前に確定した `bet_type` を「継続行」に適用する（状態機械）。

### 9.4 bet_type 正規化（ラベル→内部コード）

`RefundMoneyList` の表示ラベルには揺れがあり得るため、**部分一致**で吸収する（推奨）。

|表示ラベル（例）|内部 bet_type|is_ordered|legs 長|
|---|---|---:|---:|
|単勝|tansho|false|1|
|複勝|fukusho|false|1|
|枠連複|wakuren|false|2|
|枠連単|wakutan|true|2|
|馬連複 / 馬連|umaren|false|2|
|馬連単 / 馬単|umatan|true|2|
|ワイド|wide|false|2|
|三連複|sanrenpuku|false|3|
|三連単|sanrentan|true|3|

> わからない
> - 「拡連複」「枠単」など別表記が出るかは未確認。フィクスチャで観測した表記だけを確定し、追加表記はテスト追加で都度対応する。

### 9.5 行パース仕様（最小）

1行（1的中目）から以下を抽出する。

- `race_key`（race_no は行が属するレースブロックから取得）
- `bet_type`（ラベル or 継続行で復元）
- `legs`（組番、数値列）
- `payout_yen`（円、整数）
- `popularity`（人気、整数、無ければ null）

#### 9.5.1 legs の抽出（推奨）

- 組番文字列から `\d+` を抽出し、`bet_type` の期待 legs 長に一致するまで採用する。
- 区切り記号（`-`, `－`, `→`, 空白など）の揺れを許容する。

#### 9.5.2 payout_yen の抽出（推奨）

- `1,230円` のようにカンマが入る可能性があるため、`[^0-9]` を除去して int へ。

#### 9.5.3 popularity の抽出（推奨）

- セル内に `人気` が含まれる場合は `\d+` を抽出して int へ。
- `人気` が無い・空欄の場合は null。

> わからない
> - 「返還」「不成立」などで金額が数値でない表記があるかは未確認。実装では `payout_yen=null` + `note/status` に原文を残す拡張を許容する（DB側は後で `status` 列追加）。

### 9.6 レースブロックの検出（推奨）

HTML構造への依存を減らすため、以下のいずれか（複数）で race_no を判定する。

- レース見出しテキスト（例: `第3競走`, `3R`）の正規表現で判定
- `RaceMarkTable?k_raceNo=...` へのリンクURLを見つけ、クエリの `k_raceNo` を race_no とする

### 9.7 TDD（goldenテスト）構成

```
tests/
  fixtures/
    refund_money_list__date=2025-12-26__baba=20__snap=final.html
  expected/
    refund_money_list__date=2025-12-26__baba=20__snap=final.json
  test_refund_money_list_parser.py
```

- 期待値JSONは **ページ全体の payout レコード配列**（race_no を含む）。
- 比較前に決定的ソート（`race_no`, `bet_type`, `legs`, `payout_yen` 等）を行う。

### 9.8 最小テストマトリクス（必須）

|ケース|狙い|fixture要件|
|---|---|---|
|複勝が複数行|継続行の bet_type 復元|複勝が3行出るレース|
|ワイドが複数行|継続行 + legs=2|ワイドが複数行出るレース|
|三連単/三連複|legs=3 の抽出|いずれも払戻が掲載されている|
|枠連系|legs が枠番|枠連複/枠連単が掲載されている|

---

## 10. B4: レース/出走表/成績（RaceList/DebaTable/RaceMarkTable）パーサ（TDD設計確定）

### 10.1 目的

- レース予測/RL の共通キーである `race_key` を中心に、
  - `RaceList` から当日スケジュール（発走時刻）と変更情報
  - `DebaTable` から出走表（馬番/枠/馬名/騎手/斤量/調教師/馬体重など）
  - `RaceMarkTable` から確定成績（着順/タイム/着差/上り/人気/通過順など）
  を冪等に蓄積できるようにする。

### 10.2 正規化契約（参照）

- 正規化JSONの契約は `source_shared/20_parser_normalization_contracts.md` に統合して定義する。
  - `Race` / `Entry` / `Result` / `RaceChange` / `Payout` / `Odds`

### 10.3 DB反映（upsert順序と優先順位）

**前提**: `races` に `(race_date,baba_code,race_no)` UNIQUE がある。

推奨の反映順（最小）

1. `RaceList(date,baba_code)` を取得し、races を **作成/更新**（発走時刻が最重要）
2. レースごとに `DebaTable` を取得し、races を補完 + `race_entries` を upsert
3. スケジュールに従って `Odds*` を取得し、`odds_snapshots` + `odds_items` を upsert
4. レース後に `RaceMarkTable` を取得し、`race_results` を upsert（確定値）
5. 当日終了後に `RefundMoneyList` を取得し、`payouts` を upsert（B3）

データ優先順位（衝突時の推奨）

- `races.start_time`: RaceList を優先（スケジューラの一次情報）
- `race_entries.body_weight/body_weight_diff`: **RaceMarkTable を優先**（確定値になりやすい）
- 天候/馬場: RaceMarkTable（確定後）で上書き可
- 払戻: RefundMoneyList を優先（同値確認用に RaceMarkTable を補助に使う）

### 10.4 TDD（fixtures → golden）

最小構成は「同一 race_key の3ページ + 当日払戻」で、B1/B3 の odds fixtures と同一日・同一開催場を流用する。

```
tests/
  fixtures/
    racelist__date=2025-12-26__baba=20.html
    deba_table__date=2025-12-26__baba=20__race=3.html
    race_mark_table__date=2025-12-26__baba=20__race=3.html
    refund_money_list__date=2025-12-26__baba=20.html
  expected/
    racelist__date=2025-12-26__baba=20.json
    deba_table__...json
    race_mark_table__...json
  test_race_parsers.py
```

#### 10.4.1 最小 assert（最初に通す）

- RaceList: `race_no` と `start_time` が全行で取れる（取れない行は欠損扱いでスキップしてログ）
- DebaTable: `horse_number` が全行で取れる（取消はフラグで残す）
- RaceMarkTable: `finish_position` と `horse_number` が取れる

### 10.5 追加で早期に集めたいケース（推奨）

共有資料内で未確認のため、ここは **推測ですが**、実運用で頻繁に出る可能性が高い。

- 出走取消があるレース（DebaTable と RaceList の変更欄・RaceMarkTable の表記揺れ）
- 騎手変更があるレース（RaceList 下部の変更テーブル）
- 同着や降着など、着順表記が数値以外になるレース
