from __future__ import annotations

import re
from bs4 import BeautifulSoup
from bs4.element import Tag

from scraper_service.keiba.models import RaceEntryUpsert, RaceKey
from scraper_service.parsers.common import normalize_space, extract_ints


def _parse_float(s: str):
    try:
        return float(s)
    except Exception:
        return None


def _parse_int(s: str):
    try:
        return int(s)
    except Exception:
        return None


def _parse_body_weight(cell: str) -> tuple[int | None, int | None]:
    t = normalize_space(cell)
    if not t or "計不" in t:
        return (None, None)
    # examples: "480(+2)", "480(-4)", "480(±0)"
    m = re.search(r"(\d+)\s*\(\s*([+\-−±]?\d+)\s*\)", t)
    if m:
        bw = _parse_int(m.group(1))
        diff_raw = m.group(2).replace("−", "-").replace("±", "0")
        diff = _parse_int(diff_raw)
        return (bw, diff)
    # fallback: plain int
    ints = extract_ints(t)
    if ints:
        return (ints[0], None)
    return (None, None)


def _find_table_with_headers(
    soup: BeautifulSoup, *, required: list[str]
) -> tuple[list[str], Tag] | None:
    for table in soup.find_all("table"):
        header_row = table.find("tr")
        if not header_row:
            continue
        ths = header_row.find_all("th")
        if not ths:
            continue
        headers = [normalize_space(th.get_text(" ", strip=True)) for th in ths]
        if all(any(req in h for h in headers) for req in required):
            return (headers, table)
    return None


def parse_deba_table(html: bytes, *, race_date: str, baba_code: int, race_no: int) -> list[RaceEntryUpsert]:
    """Parse DebaTable into race entries.

    Best-effort:
    - scans table rows and expects to find horse_number and horse_name.
    """
    soup = BeautifulSoup(html, "lxml")
    rk = RaceKey(race_date=race_date, baba_code=baba_code, race_no=race_no)
    entries: list[RaceEntryUpsert] = []

    found = _find_table_with_headers(soup, required=["馬番", "馬名"])
    if found is not None:
        headers, table = found

        def idx_of(*keys: str) -> int | None:
            for i, h in enumerate(headers):
                if any(k in h for k in keys):
                    return i
            return None

        idx_waku = idx_of("枠")
        idx_horse_no = idx_of("馬番")
        idx_horse_name = idx_of("馬名")
        idx_handicap = idx_of("斤量")
        idx_jockey = idx_of("騎手")
        idx_trainer = idx_of("調教師")
        idx_body_weight = idx_of("馬体重")

        for tr in table.find_all("tr")[1:]:
            tds = tr.find_all("td")
            if not tds:
                continue
            row = [normalize_space(td.get_text(" ", strip=True)) for td in tds]

            if idx_horse_no is None or idx_horse_name is None:
                continue
            if idx_horse_no >= len(row) or idx_horse_name >= len(row):
                continue

            hn_ints = extract_ints(row[idx_horse_no])
            if not hn_ints:
                continue
            horse_number = hn_ints[0]
            if horse_number < 1 or horse_number > 18:
                continue

            horse_name = row[idx_horse_name]
            if not horse_name:
                continue

            post_position = None
            if idx_waku is not None and idx_waku < len(row):
                w = extract_ints(row[idx_waku])
                if w:
                    post_position = w[0]

            handicap = None
            if idx_handicap is not None and idx_handicap < len(row):
                # "54.0" or "54" or "54kg"
                m = re.search(r"(\d+(?:\.\d+)?)", row[idx_handicap])
                if m:
                    handicap = _parse_float(m.group(1))

            jockey_name = None
            if idx_jockey is not None and idx_jockey < len(row):
                jockey_name = row[idx_jockey] or None

            trainer_name = None
            if idx_trainer is not None and idx_trainer < len(row):
                trainer_name = row[idx_trainer] or None

            body_weight = None
            body_weight_diff = None
            if idx_body_weight is not None and idx_body_weight < len(row):
                body_weight, body_weight_diff = _parse_body_weight(row[idx_body_weight])

            entries.append(
                RaceEntryUpsert(
                    race_key=rk,
                    horse_id=None,
                    post_position=post_position,
                    horse_number=horse_number,
                    horse_name=horse_name,
                    jockey_name=jockey_name,
                    trainer_name=trainer_name,
                    handicap_kg=handicap,
                    body_weight=body_weight,
                    body_weight_diff=body_weight_diff,
                )
            )

    if entries:
        # de-dup by horse_number
        seen = set()
        uniq: list[RaceEntryUpsert] = []
        for e in entries:
            if e.horse_number in seen:
                continue
            seen.add(e.horse_number)
            uniq.append(e)
        return uniq

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
