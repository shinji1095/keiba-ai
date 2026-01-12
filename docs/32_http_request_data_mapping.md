# 32 HTTPリクエスト対応表（取得データ）

作成日: 2026-01-12（Asia/Tokyo）

本ドキュメントは、`keiba.go.jp/KeibaWeb/TodayRaceInfo/` 配下の **HTTPリクエスト単位**で
「取得可能なデータ」を整理し、スケジューリング設計の基準とする。

## 1. 対応表（1リクエスト = 1ページ）

|PageName|URL例（PC版）|粒度|取得できるデータ（正規化）|備考|
|---|---|---|---|---|
|TodayRaceInfoTop|https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop|日付（暗黙）|開催場一覧（baba_codes）|当日の開催場導線を取得|
|RaceList|https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceList?k_raceDate=YYYY/MM/DD&k_babaCode=NN|日付×開催場|races（発走時刻、R番号、距離、馬場、変更情報など）|当日のスケジュール基準（start_time）|
|DebaTable|https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/DebaTable?k_raceDate=YYYY/MM/DD&k_babaCode=NN&k_raceNo=RR|レース|race_entries / race_cards|出馬表（馬番、騎手、斤量など）|
|RaceMarkTable|https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceMarkTable?k_raceDate=YYYY/MM/DD&k_babaCode=NN&k_raceNo=RR|レース|race_results|成績のみ。払戻は含まれない|
|RefundMoneyList|https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RefundMoneyList?k_raceDate=YYYY/MM/DD&k_babaCode=NN|日付×開催場|payouts（当日全レース）|1ページで当日全レースの払戻が取得可能|
|OddsTanFuku|https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/OddsTanFuku?k_raceDate=YYYY/MM/DD&k_babaCode=NN&k_raceNo=RR&odds_flg=4|レース|odds_snapshots（tansho, fukusho）|単勝/複勝を同一ページで取得可能|
|OddsWakuLenFukuTan|https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/OddsWakuLenFukuTan?k_raceDate=YYYY/MM/DD&k_babaCode=NN&k_raceNo=RR&odds_flg=6|レース|odds_snapshots（wakuren, wakutan）|枠連複/枠連単を同一ページで取得可能|
|OddsUmLenFuku|https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/OddsUmLenFuku?k_raceDate=YYYY/MM/DD&k_babaCode=NN&k_raceNo=RR|レース|odds_snapshots（umaren）| |
|OddsUmLenTan|https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/OddsUmLenTan?k_raceDate=YYYY/MM/DD&k_babaCode=NN&k_raceNo=RR|レース|odds_snapshots（umatan）| |
|OddsWide|https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/OddsWide?k_raceDate=YYYY/MM/DD&k_babaCode=NN&k_raceNo=RR|レース|odds_snapshots（wide）| |
|Odds3LenFuku|https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/Odds3LenFuku?k_raceDate=YYYY/MM/DD&k_babaCode=NN&k_raceNo=RR|レース|odds_snapshots（sanrenpuku）|ページ名は 3LenFuku|
|Odds3LenTan|https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/Odds3LenTan?k_raceDate=YYYY/MM/DD&k_babaCode=NN&k_raceNo=RR|レース|odds_snapshots（sanrentan）|ページ名は 3LenTan|

補足:
- OddsTanFuku / OddsWakuLenFukuTan は **1回のHTTPリクエストで2種目**が取得できる。
- RefundMoneyList は **1回のHTTPリクエストで当日全レース**の払戻が取得できる。

## 2. よくある勘違いと正しい整理

- OddsTanFuku から **単勝と複勝の両方**が取得できる（正しい）。
- RaceMarkTable から **払戻は取得できない**。払戻は RefundMoneyList のみ（正しい）。
- 「一度のHTTPリクエストで同時に取得可能な情報」は **同一ページ内の複数データのみ**。
  別ページに分かれている情報は **ページごとに別リクエスト**が必要。

## 3. スケジューリング前提（今回の運用方針）

- 時間変化するのは odds のみ。snapshot_kind は `t_minus_60m / t_minus_30m / final` を使用。
- DebaTable は早い時間に1回取得（odds と被らないように配置）。
- RaceMarkTable / RefundMoneyList は `final` のタイミングでのみ取得。
- HTTPリクエスト間隔は 1〜5分（運用上は 1分固定でも可）。

参照: `docs/scraper/01_site_structure.md`
