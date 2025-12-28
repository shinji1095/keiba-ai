from __future__ import annotations

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
