from __future__ import annotations

import re
from bs4 import BeautifulSoup

from scraper_service.keiba.models import RaceEntryUpsert, RaceKey
from scraper_service.parsers.common import normalize_space, extract_ints


def _parse_float(s: str):
    try:
        return float(s)
    except Exception:
        return None


def parse_deba_table(html: bytes, *, race_date: str, baba_code: int, race_no: int) -> list[RaceEntryUpsert]:
    """Parse DebaTable into race entries.

    Best-effort:
    - scans table rows and expects to find horse_number and horse_name.
    """
    soup = BeautifulSoup(html, "lxml")
    rk = RaceKey(race_date=race_date, baba_code=baba_code, race_no=race_no)
    entries: list[RaceEntryUpsert] = []

    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        row = [normalize_space(td.get_text(" ", strip=True)) for td in tds]
        # try detect horse number as first integer in row
        ints = extract_ints(" ".join(row[:3]))
        if not ints:
            continue
        horse_number = ints[0]
        if horse_number < 1 or horse_number > 18:
            continue
        # heuristics for horse name: choose longest non-numeric token among first columns
        horse_name = None
        for cell in row:
            if cell and not re.fullmatch(r"[0-9\s\-]+", cell) and "kg" not in cell:
                # ignore obvious headers
                if any(x in cell for x in ["枠", "馬", "印", "性齢", "斤量"]):
                    continue
                horse_name = cell
                break
        if not horse_name:
            continue

        # optional handicap (斤量) and jockey/trainer
        handicap = None
        for cell in row:
            m = re.search(r"(\d+(?:\.\d+)?)\s*kg", cell)
            if m:
                handicap = _parse_float(m.group(1))
                break

        entries.append(
            RaceEntryUpsert(
                race_key=rk,
                horse_number=horse_number,
                horse_name=horse_name,
                handicap_kg=handicap,
            )
        )

    # de-dup by horse_number
    seen = set()
    uniq: list[RaceEntryUpsert] = []
    for e in entries:
        if e.horse_number in seen:
            continue
        seen.add(e.horse_number)
        uniq.append(e)
    return uniq
