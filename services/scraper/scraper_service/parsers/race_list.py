from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from scraper_service.keiba.models import RaceKey, RaceUpsert
from scraper_service.parsers.common import normalize_space


_TIME_PAT = re.compile(r"(\d{1,2}):(\d{2})")


def _parse_time(s: str) -> str | None:
    m = _TIME_PAT.search(s)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2))
    return f"{hh:02d}:{mm:02d}:00"


def parse_race_list(html: bytes, *, race_date: str, baba_code: int) -> list[RaceUpsert]:
    """Parse RaceList to produce RaceUpsert items.

    Best-effort parser:
    - detect race_no from links containing k_raceNo
    - detect start_time from row text
    """
    soup = BeautifulSoup(html, "lxml")
    races: dict[int, RaceUpsert] = {}

    # find candidates by looking at <a href="...k_raceNo=...">
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        if "k_raceNo" not in href:
            continue
        q = parse_qs(urlparse(href).query)
        if not q.get("k_raceNo"):
            continue
        try:
            rn = int(q["k_raceNo"][0])
        except ValueError:
            continue
        if rn < 1 or rn > 12:
            continue

        # find row text (closest tr)
        tr = a.find_parent("tr")
        row_text = normalize_space(tr.get_text(" ", strip=True)) if tr else normalize_space(a.get_text(" ", strip=True))
        start_time = _parse_time(row_text)

        races[rn] = RaceUpsert(
            race_key=RaceKey(race_date=race_date, baba_code=baba_code, race_no=rn),
            start_time=start_time,
            race_name=None,
        )

    # fallback: if no links, try to find rows with pattern "1R 12:30"
    if not races:
        for tr in soup.find_all("tr"):
            t = normalize_space(tr.get_text(" ", strip=True))
            m = re.search(r"\b(\d{1,2})R\b", t)
            if not m:
                continue
            rn = int(m.group(1))
            start_time = _parse_time(t)
            races[rn] = RaceUpsert(
                race_key=RaceKey(race_date=race_date, baba_code=baba_code, race_no=rn),
                start_time=start_time,
            )

    return [races[k] for k in sorted(races.keys())]
