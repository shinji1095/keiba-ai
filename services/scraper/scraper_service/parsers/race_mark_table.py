from __future__ import annotations

import re
from bs4 import BeautifulSoup

from scraper_service.keiba.models import RaceKey, RaceResultUpsert
from scraper_service.parsers.common import extract_ints, normalize_space


def parse_race_mark_table(html: bytes, *, race_date: str, baba_code: int, race_no: int) -> list[RaceResultUpsert]:
    """Parse RaceMarkTable into race results (best-effort)."""
    soup = BeautifulSoup(html, "lxml")
    rk = RaceKey(race_date=race_date, baba_code=baba_code, race_no=race_no)
    results: list[RaceResultUpsert] = []

    # Heuristic: find rows that start with finish_position (1..18)
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        row_text = normalize_space(tr.get_text(" ", strip=True))
        ints = extract_ints(row_text)
        if not ints:
            continue
        finish_pos = ints[0]
        if finish_pos < 1 or finish_pos > 18:
            continue

        horse_number = None
        if len(ints) >= 2 and 1 <= ints[1] <= 18:
            horse_number = ints[1]

        # time_str: detect pattern 1:23.4 or 1.23.4 etc
        time_str = None
        m = re.search(r"\b\d+:\d{2}\.\d\b", row_text)
        if m:
            time_str = m.group(0)

        results.append(
            RaceResultUpsert(
                race_key=rk,
                finish_position=finish_pos,
                horse_number=horse_number,
                time_str=time_str,
            )
        )

    # de-dup by finish_position
    out: dict[int, RaceResultUpsert] = {}
    for r in results:
        out[r.finish_position] = r
    return [out[k] for k in sorted(out.keys())]
