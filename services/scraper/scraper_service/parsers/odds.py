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


def _parse_float(text: str) -> Optional[float]:
    m = re.search(r"(\d+(?:\.\d+)?)", normalize_space(text))
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


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


def _expand_header_cells(cells: Iterable) -> list[str]:
    columns: list[str] = []
    for cell in cells:
        text = normalize_space(cell.get_text(" ", strip=True))
        try:
            colspan = int(cell.get("colspan", "1"))
        except ValueError:
            colspan = 1
        for _ in range(max(colspan, 1)):
            columns.append(text)
    return columns


def _find_col_index(columns: list[str], keyword: str) -> Optional[int]:
    for idx, name in enumerate(columns):
        if keyword in name:
            return idx
    return None


def _parse_tanfuku_table(table) -> Optional[dict[BetType, list[OddsItemUpsert]]]:
    header_row = None
    thead = table.find("thead")
    if thead is not None:
        header_row = thead.find("tr")
    if header_row is None:
        header_row = table.find("tr")
    if header_row is None:
        return None

    columns = _expand_header_cells(header_row.find_all(["th", "td"]))
    if not columns:
        return None

    idx_horse = _find_col_index(columns, "馬番")
    idx_win = _find_col_index(columns, "単勝")
    idx_place = _find_col_index(columns, "複勝")
    if idx_horse is None or idx_win is None or idx_place is None:
        return None

    place_is_range = idx_place + 1 < len(columns) and "複勝" in columns[idx_place + 1]
    tansho: dict[int, OddsItemUpsert] = {}
    fukusho: dict[int, OddsItemUpsert] = {}

    tbody = table.find("tbody")
    rows = tbody.find_all("tr") if tbody is not None else table.find_all("tr")
    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) <= max(idx_horse, idx_win, idx_place):
            continue

        horse_ints = extract_ints(tds[idx_horse].get_text(" ", strip=True))
        if not horse_ints:
            continue
        horse_no = horse_ints[0]
        if horse_no < 1 or horse_no > 18:
            continue

        win_text = tds[idx_win].get_text(" ", strip=True)
        win_odds = _parse_float(win_text)

        place_text = tds[idx_place].get_text(" ", strip=True)
        place_min: Optional[float]
        place_max: Optional[float]
        if place_is_range and idx_place + 1 < len(tds):
            place_min = _parse_float(place_text)
            place_max = _parse_float(tds[idx_place + 1].get_text(" ", strip=True))
            if place_min is None and place_max is None:
                place_min, place_max = parse_odds_range(place_text)
        else:
            place_min, place_max = parse_odds_range(place_text)

        if place_min is not None and place_max is None:
            place_max = place_min
        if place_max is not None and place_min is None:
            place_min = place_max

        if win_odds is not None:
            tansho[horse_no] = OddsItemUpsert(
                legs=[horse_no],
                is_ordered=False,
                odds_min=win_odds,
                odds_max=win_odds,
                popularity=None,
            )

        fukusho[horse_no] = OddsItemUpsert(
            legs=[horse_no],
            is_ordered=False,
            odds_min=place_min,
            odds_max=place_max,
            popularity=None,
        )

    if not tansho and not fukusho:
        return None
    return {
        "tansho": [tansho[k] for k in sorted(tansho.keys())],
        "fukusho": [fukusho[k] for k in sorted(fukusho.keys())],
    }


def parse_odds_tanfuku(html: bytes) -> dict[BetType, list[OddsItemUpsert]]:
    """Parse OddsTanFuku page which contains both tansho and fukusho.

    Implementation:
    - Parse a header-aware table to avoid mixing unrelated numeric columns.
    - Avoid generic fallback to prevent mis-parsing (horse/waku numbers).
    """
    soup = BeautifulSoup(html, "lxml")

    tables: list = []
    primary = soup.find("table", class_="odd_popular_table_02")
    if primary is not None:
        tables.append(primary)

    for table in soup.find_all("table"):
        if table in tables:
            continue
        header_row = table.find("tr")
        if header_row is None:
            continue
        header_cols = _expand_header_cells(header_row.find_all(["th", "td"]))
        if "単勝" in " ".join(header_cols) and "複勝" in " ".join(header_cols):
            tables.append(table)

    for table in tables:
        parsed = _parse_tanfuku_table(table)
        if parsed and parsed.get("tansho") and parsed.get("fukusho"):
            return parsed

    return {"tansho": [], "fukusho": []}


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
    """Parse OddsWakuLenFukuTan page.

    Notes:
    - In practice, some pages only include "枠連複" (wakuren) blocks.
    - When wakutan block is absent, return empty list for wakutan.
    """
    soup = BeautifulSoup(html, "lxml")
    tables = soup.select("ul.odd_horse_number_list table")
    if tables:
        items: dict[tuple[int, int], OddsItemUpsert] = {}
        for t in tables:
            head = t.find("th")
            if head is None:
                continue
            base_ints = extract_ints(head.get_text(" ", strip=True))
            if not base_ints:
                continue
            waku_1 = base_ints[0]

            for tr in t.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) < 2:
                    continue
                opp_ints = extract_ints(tds[0].get_text(" ", strip=True))
                if not opp_ints:
                    continue
                waku_2 = opp_ints[0]
                odds = _parse_float(tds[1].get_text(" ", strip=True))
                if odds is None:
                    continue

                # The page is typically waku_2 >= waku_1 (matrix upper triangle).
                k = (min(waku_1, waku_2), max(waku_1, waku_2))
                items[k] = OddsItemUpsert(
                    legs=[k[0], k[1]],
                    is_ordered=False,
                    odds_min=odds,
                    odds_max=odds,
                    popularity=None,
                )

        wakuren = list(items.values())
        # The page often lacks an explicit popularity column; derive ranking by odds asc.
        ranked = sorted(
            [it for it in wakuren if it.odds_min is not None],
            key=lambda it: (it.odds_min, it.legs),
        )
        last_odds: float | None = None
        rank = 0
        for i, it in enumerate(ranked):
            if last_odds is None or it.odds_min != last_odds:
                rank = i + 1  # competition ranking (ties share rank; next rank skips)
                last_odds = it.odds_min
            it.popularity = rank
        return {"wakuren": wakuren, "wakutan": []}

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
