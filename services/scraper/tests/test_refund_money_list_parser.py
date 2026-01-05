from __future__ import annotations

from pathlib import Path

from scraper_service.parsers.refund_money_list import parse_refund_money_list


HTML = """<html><body>
<h3>第1競走</h3>
<table>
<tr><th>式別</th><th>馬番</th><th>払戻</th><th>人気</th></tr>
<tr><td>単勝</td><td>5</td><td>1,230円</td><td>3人気</td></tr>
<tr><td>複勝</td><td>5</td><td>300円</td><td>2人気</td></tr>
<tr><td></td><td>1</td><td>450円</td><td>4人気</td></tr>
<tr><td>ワイド</td><td>1-5</td><td>560円</td><td>1人気</td></tr>
<tr><td></td><td>2-5</td><td>900円</td><td>5人気</td></tr>
</table>
</body></html>
""".encode("utf-8")


def test_parse_refund_money_list_continuation_rows():
    payouts = parse_refund_money_list(HTML, race_date="2025-12-26", baba_code=20)
    # tansho 1, fukusho 2 rows, wide 2 rows => total 5
    assert len(payouts) == 5
    tansho = [p for p in payouts if p.bet_type == "tansho"]
    assert tansho[0].legs == [5]
    assert tansho[0].payout_yen == 1230

    fukusho = [p for p in payouts if p.bet_type == "fukusho"]
    assert {tuple(p.legs) for p in fukusho} == {(5,), (1,)}

    wide = [p for p in payouts if p.bet_type == "wide"]
    assert {tuple(p.legs) for p in wide} == {(1, 5), (2, 5)}


def test_parse_refund_money_list_fixture_sonoda_20260102() -> None:
    fixtures_root = Path(__file__).resolve().parent / "fixtures"
    html = (fixtures_root / "27_2026-01-02_refund_money_list.html").read_bytes()
    payouts = parse_refund_money_list(html, race_date="2026-01-02", baba_code=27)

    # 2R should be present (the production page uses <p class="roundNum">2R</p>).
    r2 = [p for p in payouts if p.race_key.race_no == 2]
    assert len(r2) == 12

    tansho = next(p for p in r2 if p.bet_type == "tansho" and p.legs == [9])
    assert tansho.payout_yen == 860

    fukusho = [p for p in r2 if p.bet_type == "fukusho"]
    assert {tuple(p.legs) for p in fukusho} == {(9,), (12,), (11,)}
