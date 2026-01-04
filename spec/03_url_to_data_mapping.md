# URL と取得情報の対応表（仕様）

更新履歴
- 2026-01-03: `sp.keiba.go.jp`（SP向け）URL パターンとページング（推測）を追記。`www.keiba.go.jp` が取得できない場合の代替経路を明記。
- 2026-01-04: RaceMarkTable（成績/払戻）を追記。OddsTanFuku の単勝/複勝と spec カラム（win_odds / place_odds_min/max）の対応を明記。

## 対象ドメイン
- PC向け: `www.keiba.go.jp`（取得できる場合の正）
- SP向け: `sp.keiba.go.jp`（取得不能時の代替。表構造は概ね同等）

> 注: 本セッション（2026-01-03）では `www.keiba.go.jp` のページ取得に失敗（ClientResponseError）が発生したため、オッズ系は一部 `sp.keiba.go.jp` を参照しました。

## 取得キー（正規化）
- `baba_code`（例: 27）
- `race_date`（例: 2026-01-02）
- `race_no`（例: 2）
- これらから `race_id = "{baba_code}_{race_date}_{race_no:02d}"` を生成（例: `27_2026-01-02_02`）

## URL と保存ファイルの対応

| 種別 | URL（PC向け） | URL（SP向け） | 主な取得テーブル | 保存先（例） |
|---|---|---|---|---|
| レース一覧 | `/KeibaWeb/TodayRaceInfo/RaceList?k_babaCode={baba_code}&k_raceDate={YYYY}%2F{MM}%2F{DD}` | （未調査） | races（補助） | `extracted/01_race_list_...md` |
| 出馬表 | `/KeibaWeb/TodayRaceInfo/DebaTable?k_raceDate={YYYY}%2F{MM}%2F{DD}&k_raceNo={race_no}&k_babaCode={baba_code}` | （未調査） | horses / persons / race_entries / perf_* / best_time / last5 | `data/{race_id}/01_debatable_normalized.md` |
| 単勝・複勝 | `/KeibaWeb/TodayRaceInfo/OddsTanFuku?...` | `/KeibaWebSP/TodayRaceInfo/S_OddsTanFuku?k_babaCode=...&k_raceDate=...&k_raceNo=...` | odds_tanfuku + 補助的に race_entries | `data/{race_id}/02_odds_tanfuku.md` |
| 枠連 | `/KeibaWeb/TodayRaceInfo/OddsWakuLenFukuTan?...` | `/KeibaWebSP/TodayRaceInfo/S_OddsWakuLenFukuTan?...`（推測） | odds_wakuren_* | `data/{race_id}/03_odds_wakuren_*.md` |
| 馬連複 | `/KeibaWeb/TodayRaceInfo/OddsUmLenFuku?...` | `/KeibaWebSP/TodayRaceInfo/S_OddsUmLenFuku?...` | odds_umaren_fuku | `data/{race_id}/04_odds_umaren_fuku.md` |
| 馬連単 | `/KeibaWeb/TodayRaceInfo/OddsUmLenTan?...` | `/KeibaWebSP/TodayRaceInfo/S_OddsUmLenTan?...` | odds_umaren_tan | `data/{race_id}/05_odds_umaren_tan.md` |
| ワイド | `/KeibaWeb/TodayRaceInfo/OddsWide?...` | `/KeibaWebSP/TodayRaceInfo/S_OddsWide?...` | odds_wide | `data/{race_id}/06_odds_wide.md` |
| 成績・払戻 | `/KeibaWeb/TodayRaceInfo/RaceMarkTable?k_raceDate={YYYY}%2F{MM}%2F{DD}&k_raceNo={race_no}&k_babaCode={baba_code}` | （未調査） | race_results / payouts（同一ページ内で確認可能） | `extracted/07_race_mark_table_...md`（将来予約） |

## OddsTanFuku と spec カラムの対応
- 単勝オッズ: `win_odds`
- 複勝オッズ: `place_odds_min` と `place_odds_max`
  - 複勝は **最小値〜最大値**（レンジ）で提供されるため、2カラムに対応付ける

## SP向けオッズページの補助パラメータ（推測）
検索結果の表記から、以下のパラメータが存在します（全件取得のために必要になる見込み）。

- `pop_flg`: `1`=人気順, `0`=高額配当順
- `odds_flg`: 切替用（0/1のいずれか、ページ種別で固定の可能性）
- `k_flag`, `k_pageNum`: 50件単位のページング用（2ページ目以降）

例（馬連複の2ページ目・高額配当順の形式例）:
- `/KeibaWebSP/TodayRaceInfo/S_OddsUmLenFuku?k_babaCode=...&k_flag=1&k_pageNum=1&k_raceDate=...&k_raceNo=...&odds_flg=0&pop_flg=0`

## 検証（babaCode + 日付 + レース番号で全情報を引けるか）
- races（発走/距離/天候/馬場など）は `RaceList` で **日付 + babaCode** から取得可能。
- 出馬表・各オッズは **日付 + babaCode + レース番号** で URL を組み立て可能。
- ただし、**全フィールド（血統・馬主・生産など）** を埋めるには `DebaTable` の本文取得が前提。取得不能の場合は欠損が発生する（現状のレース2が該当）。
