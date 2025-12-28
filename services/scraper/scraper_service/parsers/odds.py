from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional

from bs4 import BeautifulSoup

from scraper_service.keiba.models import BetType, OddsItemUpsert
from scraper_service.parsers.common import extract_ints, normalize_space, parse_odds_range


def _is_ordered(bet_type: BetType) -> bool:
    return bet_type in {"wakutan", "umatan", "sanrentan"}


def _legs_len(bet_type: BetType) -> int:
    if bet_type in {"tansho", "fukusho"}:
        return 1
    if bet_type in {"wakuren", "wakutan", "umaren", "umatan", "wide"}:
        return 2
    return 3


def _parse_popularity(text: str) -> Optional[int]:
    ints = extract_ints(text)
    if not ints:
        return None
    # often popularity is the last integer in the row
    return ints[-1]


_ROW_ODDS_PAT = re.compile(
    r"(?P<legs>(?:\d+\s*[-－]\s*)+\d+|\d+)\s+(?P<odds>\d+(?:\.\d+)?(?:\s*[-–〜～]\s*\d+(?:\.\d+)?)?)"
)


def parse_generic_odds_table(html: bytes, *, bet_type: BetType) -> list[OddsItemUpsert]:
    """Parse odds table of a single bet type.

    This is a best-effort parser:
    - scan each <tr> text for 'legs odds' pattern
    - popularity (if present) is parsed as last integer (heuristic)
    """
    soup = BeautifulSoup(html, "lxml")
    out: list[OddsItemUpsert] = []
    need = _legs_len(bet_type)

    for tr in soup.find_all("tr"):
        t = normalize_space(tr.get_text(" ", strip=True))
        m = _ROW_ODDS_PAT.search(t)
        if not m:
            continue
        legs = extract_ints(m.group("legs"))
        if len(legs) < need:
            continue
        legs = legs[:need]
        odds_min, odds_max = parse_odds_range(m.group("odds"))
        pop = _parse_popularity(t)
        out.append(
            OddsItemUpsert(
                legs=legs,
                is_ordered=_is_ordered(bet_type),
                odds_min=odds_min,
                odds_max=odds_max,
                popularity=pop,
            )
        )

    # de-dup by (legs,is_ordered)
    uniq: dict[tuple[str, bool], OddsItemUpsert] = {}
    for it in out:
        k = ("-".join(map(str, it.legs)), it.is_ordered)
        uniq[k] = it
    return list(uniq.values())


def parse_odds_tanfuku(html: bytes) -> dict[BetType, list[OddsItemUpsert]]:
    """Parse OddsTanFuku page which contains both tansho and fukusho.

    Implementation:
    - if the page has sections containing '単勝'/'複勝', try to split by nearest table after the heading
    - otherwise fall back to generic parsing with bet_type=tansho and bet_type=fukusho on the same HTML
    """
    soup = BeautifulSoup(html, "lxml")

    def find_table_after(keyword: str):
        el = soup.find(string=lambda s: s and keyword in s)
        if not el:
            return None
        tag = el.parent
        return tag.find_next("table")

    t_table = find_table_after("単勝")
    f_table = find_table_after("複勝")

    out: dict[BetType, list[OddsItemUpsert]] = {}
    if t_table is not None:
        out["tansho"] = parse_generic_odds_table(str(t_table).encode("utf-8"), bet_type="tansho")
    else:
        out["tansho"] = parse_generic_odds_table(html, bet_type="tansho")

    if f_table is not None:
        out["fukusho"] = parse_generic_odds_table(str(f_table).encode("utf-8"), bet_type="fukusho")
    else:
        out["fukusho"] = parse_generic_odds_table(html, bet_type="fukusho")

    return out


_LABEL_TO_BETTYPE: list[tuple[str, BetType]] = [
    ("単勝", "tansho"),
    ("複勝", "fukusho"),
    ("枠連複", "wakuren"),
    ("枠連単", "wakutan"),
    ("馬連", "umaren"),
    ("馬単", "umatan"),
]


def _find_table_after(soup: BeautifulSoup, keyword: str):
    el = soup.find(string=lambda x: x and keyword in x)
    if not el:
        return None
    tag = el.parent
    return tag.find_next("table")


def parse_odds_multi_page(html: bytes, *, primary: BetType, secondary: BetType, primary_label: str, secondary_label: str) -> dict[BetType, list[OddsItemUpsert]]:
    soup = BeautifulSoup(html, "lxml")
    t1 = _find_table_after(soup, primary_label)
    t2 = _find_table_after(soup, secondary_label)

    out: dict[BetType, list[OddsItemUpsert]] = {}
    out[primary] = parse_generic_odds_table(str(t1).encode("utf-8"), bet_type=primary) if t1 is not None else parse_generic_odds_table(html, bet_type=primary)
    out[secondary] = parse_generic_odds_table(str(t2).encode("utf-8"), bet_type=secondary) if t2 is not None else parse_generic_odds_table(html, bet_type=secondary)
    return out


def parse_odds_waku(html: bytes) -> dict[BetType, list[OddsItemUpsert]]:
    return parse_odds_multi_page(html, primary="wakuren", secondary="wakutan", primary_label="枠連複", secondary_label="枠連単")


def parse_odds_uma(html: bytes) -> dict[BetType, list[OddsItemUpsert]]:
    """DEPRECATED.

    Historical note:
      Early exploration assumed a combined "馬連/馬単" page, but
      the current site structure uses separate pages:
        - OddsUmLenFuku (umaren)
        - OddsUmLenTan  (umatan)

    Kept only to avoid breaking older code/tests; new code should call
    parse_generic_odds_table(html, bet_type=...) directly.
    """
    return parse_odds_multi_page(html, primary="umaren", secondary="umatan", primary_label="馬連", secondary_label="馬単")
