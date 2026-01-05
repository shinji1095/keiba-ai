from __future__ import annotations

import re
from bs4 import BeautifulSoup

from scraper_service.keiba.models import RaceKey, RaceResultUpsert
from scraper_service.parsers.common import extract_ints, normalize_space


def parse_race_mark_table(html: bytes, *, race_date: str, baba_code: int, race_no: int) -> list[RaceResultUpsert]:
    """Parse RaceMarkTable into race results (best-effort).

    RaceMarkTable contains multiple tables (results, payouts, etc). A naive scan over all
    `<tr>` can accidentally treat payout rows as results, which produces duplicated
    `horse_number` and breaks sync (legacy DB has UNIQUE(race_id, horse_number)).

    We therefore locate the dedicated results table ("成績表") and parse by column positions.
    """
    soup = BeautifulSoup(html, "lxml")
    rk = RaceKey(race_date=race_date, baba_code=baba_code, race_no=race_no)
    results: list[RaceResultUpsert] = []

    def _none_if_blank(s: str | None) -> str | None:
        t = normalize_space(s or "").replace("\xa0", "")
        return t if t and t not in {"-", "—", "―"} else None

    def _to_int(s: str | None) -> int | None:
        ints = extract_ints(normalize_space(s or ""))
        return ints[0] if ints else None

    def _to_float(s: str | None) -> float | None:
        t = normalize_space(s or "")
        m = re.search(r"(\d+(?:\.\d+)?)", t)
        if not m:
            return None
        try:
            return float(m.group(1))
        except ValueError:
            return None

    def _extract_time(s: str | None) -> str | None:
        t = normalize_space(s or "")
        # 0:52.2 or 1:34.4
        m = re.search(r"\b\d+:\d{2}\.\d\b", t)
        return m.group(0) if m else None

    def _parse_corner_orders() -> dict[int, str]:
        """Return {corner_no: order_text} (race-level, best-effort)."""
        el = soup.find(string=lambda x: isinstance(x, str) and "コーナー通過順" in x)
        if not el:
            return {}
        td = el.parent
        # NOTE:
        # - Some pages render 3/4-corner orders as separate <br> lines, others may collapse into one line.
        # - Do NOT normalize whitespace before extracting each corner line; otherwise 3/4 corner can merge.
        raw = td.get_text(" ", strip=True)
        # normalize full-width digits to ASCII
        raw = raw.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
        # Ensure each corner marker starts on its own line (even if the page collapses into one line).
        text = re.sub(r"([1-4])コーナー", r"\n\1コーナー", raw)
        corners: dict[int, str] = {}
        for line in text.split("\n"):
            line = normalize_space(line)
            m = re.search(r"^([1-4])コーナー\s*(.+)$", line)
            if not m:
                continue
            try:
                cno = int(m.group(1))
            except ValueError:
                continue
            corners[cno] = normalize_space(m.group(2))
        return corners

    corners = _parse_corner_orders()

    # Locate the results table via its title cell containing "成績表".
    results_table = None
    for td in soup.find_all("td", class_=lambda c: isinstance(c, str) and "dbtitle" in c):
        if "成績表" in normalize_space(td.get_text(" ", strip=True)):
            results_table = td.find_parent("table")
            break

    if results_table is None:
        # Fallback: keep the old heuristic (less reliable).
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
            results.append(
                RaceResultUpsert(
                    race_key=rk,
                    finish_position=finish_pos,
                    horse_number=horse_number,
                    time_str=_extract_time(row_text),
                )
            )
    else:
        for tr in results_table.find_all("tr"):
            tds = tr.find_all("td")
            # Data rows have 15 columns:
            # finish, waku, horse_no, horse_name, ..., time, margin, last3f, popularity
            if len(tds) < 15:
                continue
            finish_pos = _to_int(tds[0].get_text(" ", strip=True))
            if finish_pos is None or finish_pos < 1 or finish_pos > 18:
                continue

            horse_number = _to_int(tds[2].get_text(" ", strip=True))
            time_str = _extract_time(tds[11].get_text(" ", strip=True))
            margin = _none_if_blank(tds[12].get_text(" ", strip=True))
            last3f = _to_float(tds[13].get_text(" ", strip=True))
            popularity = _to_int(tds[14].get_text(" ", strip=True))

            results.append(
                RaceResultUpsert(
                    race_key=rk,
                    finish_position=finish_pos,
                    horse_number=horse_number,
                    time_str=time_str,
                    margin=margin,
                    last3f=last3f,
                    popularity=popularity,
                    corner1=corners.get(1),
                    corner2=corners.get(2),
                    corner3=corners.get(3),
                    corner4=corners.get(4),
                )
            )

    # de-dup by finish_position
    out: dict[int, RaceResultUpsert] = {}
    for r in results:
        out[r.finish_position] = r
    return [out[k] for k in sorted(out.keys())]
