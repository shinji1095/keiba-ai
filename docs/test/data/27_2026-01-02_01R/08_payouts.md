# 払戻金（RaceMarkTable） 正規化結果

更新履歴
- 2026-01-04: 初版作成（RaceMarkTable の払戻を転記し、UI照合用の基準データとする）。

出典
- 地方競馬情報サイト. "払戻金（RaceMarkTable）". https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceMarkTable?k_raceDate=2026%2f01%2f02&k_raceNo=1&k_babaCode=27 (accessed 2026-01-04).

対象
- 競馬場コード(babaCode): 27
- レース日: 2026-01-02
- レース番号: 1R

## payouts
| bet_type | legs | payout_yen | popularity |
|---|---|---:|---:|
| tansho | 8 | 110 | 1 |
| fukusho | 8 | 100 | 1 |
| fukusho | 11 | 350 | 7 |
| fukusho | 9 | 120 | 2 |
| wakuren | 6-8 | 1520 | 3 |
| umaren | 8-11 | 3690 | 9 |
| umatan | 8-11 | 4350 | 11 |
| wide | 8-11 | 610 | 8 |
| wide | 8-9 | 130 | 1 |
| wide | 9-11 | 810 | 12 |
| sanrenpuku | 8-9-11 | 990 | 5 |
| sanrentan | 8-11-9 | 8830 | 24 |

備考
- 本ファイルは UI 照合用の最小表現（bet_type/legs/payout/popularity）に正規化している。


