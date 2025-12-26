# 01 スクレイピング対象サイト構造（keiba.go.jp / TodayRaceInfo）

作成日: 2025-12-27（Asia/Tokyo）  
対象: `https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/` 配下（PC版を正とする）

---

## 1. 全体像（ページ遷移）

- 入口（開催場一覧）: `TodayRaceInfoTop`
- 日付×開催場: `RaceList`
- レース単位（`k_raceDate`, `k_babaCode`, `k_raceNo`）で以下へ分岐
  - 出馬表: `DebaTable`（および印刷用 `DebaTableSmall`）
  - 対戦表: `CompeteTable`
  - 成績: `RaceMarkTable`
  - オッズ（式別ごと）: `Odds*`
- 日付×開催場（レース一覧＋払戻）:
  - 当日払戻: `RefundMoneyList`

---

## 2. URLキーとパラメータ（PC版）

### 2.1 レースキー（race_key）
- `k_raceDate`: `YYYY/MM/DD`（URLでは通常 `%2F` でエンコード）
- `k_babaCode`: 競馬場コード（例: 大井=20）
- `k_raceNo`: レース番号（1〜12 を想定）

### 2.2 URL組み立て規約（推奨）
- `k_raceDate` は **ゼロ埋め**（`2025/12/06` のように月日2桁）で生成する
- `k_raceDate` は `quote(..., safe="")` 相当で **スラッシュをエンコード**する  
  - 例: `2025%2F12%2F26`

---

## 3. PageName 一覧（PC版 / TodayRaceInfo 配下）

|用途|PageName|粒度|主キー（URL）|
|---|---|---|---|
|開催場トップ|TodayRaceInfoTop|日付（暗黙）|なし|
|開催場×日付|RaceList|日付×開催場|`k_raceDate,k_babaCode`|
|出馬表|DebaTable|レース|`k_raceDate,k_babaCode,k_raceNo`|
|出馬表（印刷用）|DebaTableSmall|レース|同上|
|対戦表|CompeteTable|レース|同上|
|成績|RaceMarkTable|レース|同上|
|当日払戻金|RefundMoneyList|日付×開催場|`k_raceDate,k_babaCode`|

---

## 4. オッズ（7ページ＝導線上の式別）

`Odds*` は「式別ごとに別ページ」だが、**1ページ内に複数式別が同居**するケースがある（単複・枠連）。

|導線上のページ|PageName|含まれる式別（bet_type）|備考|
|---|---|---|---|
|単複|OddsTanFuku|単勝（tansho）, 複勝（fukusho）|複勝はレンジ表現が出ることがある|
|枠連|OddsWakuLenFukuTan|枠連複（wakuren）, 枠連単（wakutan）|マトリクス型表示あり（`odds_flg`）|
|馬連|OddsUmLenFuku|馬連複（umaren）| |
|馬単|OddsUmLenTan|馬連単（umatan）| |
|ワイド|OddsWide|ワイド（wide）|レンジ表現が出ることがある|
|三連複|Odds3LenFuku|三連複（sanrenpuku）|ページ名は **3LenFuku**（3RenFuku ではない）|
|三連単|Odds3LenTan|三連単（sanrentan）|ページ名は **3LenTan**（3RenTan ではない）|

根拠（画面導線の追跡・確認日 2025-12-27）:
- 大井 2025/12/26 3R の OddsTanFuku から各式別へ遷移できることを確認（当日メニューのリンク）。  
- 3連系のページ名が `Odds3LenFuku / Odds3LenTan` であることを確認。

---

## 5. エラー/欠損の分類（A2 の結果）

### 5.1 代表的な失敗パターン（現時点の観測）
- **HTTP 200 だがデータなし（ソフト欠損）**  
  - 例: `ご指定のオッズは存在しません。`  
  - 例: `現在、情報を表示できません`（一時的な可能性）
- **HTTP 5xx / Internal Error（サーバ側エラー）**  
  - 例: 大井 2025/12/25 6R の三連複ページ（導線クリックで Internal Error を観測）
- **HTTP 404（未確認）**  
  - 今回の追試（導線クリック）では **404 を再現できなかった**ため、原因は「race_key 不整合」「ページ名変更」「スクレイパ実装起因」などがあり得るが、現時点では **わからない**。

### 5.2 フォールバック方針（推奨）
|状況|判定（例）|対応（推奨）|
|---|---|---|
|200 + 「オッズは存在しません」|本文に定型文|**発売なし/欠損**として記録し、再試行しない|
|200 + 「現在、情報を表示できません」|本文に定型文|短いバックオフで **少回数リトライ**→ダメなら欠損として記録|
|5xx / Internal Error|HTTPステータス or 本文|対象ページは欠損扱い。必要なら **別ページ（RefundMoneyList 等）で補完**|
|404|HTTPステータス|URL生成/パラメータを再確認（race_key）。直らない場合は欠損として記録し、将来のURL変更に備えてログを残す|

---

## 6. PC版とSP版（フォールバック）

- SP版は `https://sp.keiba.go.jp/KeibaWebSP/TodayRaceInfo/` など、URLプレフィックスが異なる。
- SP版はHTMLが簡素な一方、時間帯によってはオッズ等の導線が出ないケースが観測されている。
- 方針: **PC版を正**にして、PCが 取得失敗（404/5xx/パース不能）のときに **SP版をフォールバック**候補にする（ただし、SP側も未検証部分がある）。

---

## 7. 未確認事項（明確化が必要）

- SP版 `KeibaWebSP` の Odds* が常に PC 版と同等の情報を返すか（リンクが出ない時間帯の扱い）
- 404 が導線上で発生する条件（race_key 不整合以外の要因があるか）
