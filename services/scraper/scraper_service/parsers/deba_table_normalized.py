from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional

from bs4 import BeautifulSoup
from bs4.element import Tag
from pydantic import BaseModel

from scraper_service.keiba.models import RaceKey
from scraper_service.parsers.common import extract_ints, normalize_space


PersonRole = Literal["jockey", "trainer", "owner"]


class RaceNormalized(BaseModel):
    race_id: str
    race_date: str
    baba_code: int
    race_no: int
    post_time: Optional[str] = None  # HH:MM
    race_name: Optional[str] = None
    surface: Optional[str] = None
    distance_m: Optional[int] = None
    direction: Optional[str] = None
    weather: Optional[str] = None
    track_condition: Optional[str] = None


class PersonNormalized(BaseModel):
    person_key: str
    role: PersonRole
    name: str
    affiliation: str = ""


class HorseNormalized(BaseModel):
    horse_key: str
    horse_name: str
    sex: Optional[str] = None
    age: Optional[int] = None
    coat: Optional[str] = None
    birth_month: Optional[int] = None
    birth_day: Optional[int] = None
    birth_md_raw: Optional[str] = None
    sire: Optional[str] = None
    dam: Optional[str] = None
    dam_sire: Optional[str] = None
    breeder: Optional[str] = None


class PerfNormalized(BaseModel):
    perf_key: str
    horse_key: str
    first_cnt: int
    second_cnt: int
    third_cnt: int
    out_cnt: int
    starts: int


class BestTimeNormalized(BaseModel):
    best_time_key: str
    horse_key: str
    baba_code: int
    surface: Optional[str] = None
    distance_m: Optional[int] = None
    best_time_raw: str = ""
    best_time_sec: Optional[float] = None
    best_time_good_raw: str = ""
    best_time_good_sec: Optional[float] = None


class RaceEntryNormalized(BaseModel):
    race_id: str
    horse_no: int
    waku: Optional[int] = None
    horse_key: str
    burden_weight: Optional[float] = None
    burden_mark: str = ""
    body_weight: Optional[int] = None
    body_weight_diff: Optional[int] = None
    win_odds: Optional[float] = None
    popularity: Optional[int] = None
    jockey_person_key: Optional[str] = None
    trainer_person_key: Optional[str] = None
    owner_person_key: Optional[str] = None
    perf_total_key: Optional[str] = None
    perf_dirt_left_key: Optional[str] = None
    perf_dirt_right_key: Optional[str] = None
    perf_track_key: Optional[str] = None
    perf_distance_key: Optional[str] = None
    best_time_key: Optional[str] = None


class Last5RaceNormalized(BaseModel):
    race_id: str
    horse_no: int
    order_in_last5: int  # 1..5 (前走..5走前)
    finish_pos: Optional[int] = None
    past_race_date: Optional[str] = None  # YYYY-MM-DD
    track_condition: Optional[str] = None
    runners: Optional[int] = None
    place: Optional[str] = None
    direction: Optional[str] = None
    distance_m: Optional[int] = None
    horse_no_in_race: Optional[int] = None
    popularity: Optional[int] = None
    body_weight: Optional[int] = None
    jockey_name: Optional[str] = None
    burden_weight: Optional[float] = None
    time_raw: Optional[str] = None
    time_sec: Optional[float] = None
    passing_order_raw: Optional[str] = None
    passing_order_arr: Optional[list[int]] = None
    last3f: Optional[float] = None
    time_diff: Optional[float] = None
    winner_name: Optional[str] = None


class DebaTableNormalized(BaseModel):
    race_key: RaceKey
    race: RaceNormalized
    persons: list[PersonNormalized]
    horses: list[HorseNormalized]
    race_entries: list[RaceEntryNormalized]
    perf_total: list[PerfNormalized]
    perf_dirt_left: list[PerfNormalized]
    perf_dirt_right: list[PerfNormalized]
    perf_track: list[PerfNormalized]
    perf_distance: list[PerfNormalized]
    best_time: list[BestTimeNormalized]
    last5: list[Last5RaceNormalized]


_ALLOWANCE_SYMBOLS = {"★", "▲", "△", "◇", "☆"}


def _race_id(*, baba_code: int, race_date: str, race_no: int) -> str:
    return f"{baba_code}_{race_date}_{race_no:02d}"


def _horse_key(horse_name: str) -> str:
    return f"horse:{horse_name}"


def _person_key(*, role: PersonRole, name: str, affiliation: str) -> str:
    if affiliation:
        return f"{role}:{name}:{affiliation}"
    return f"{role}:{name}"


def _strip_parens(s: str) -> str:
    t = normalize_space(s)
    if not t:
        return ""
    if (t.startswith("（") and t.endswith("）")) or (t.startswith("(") and t.endswith(")")):
        return t[1:-1].strip()
    return t


def _parse_float(text: str) -> Optional[float]:
    m = re.search(r"(\d+(?:\.\d+)?)", normalize_space(text))
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _parse_int(text: str) -> Optional[int]:
    ints = extract_ints(text)
    return ints[0] if ints else None


def _parse_time_sec(time_raw: str) -> Optional[float]:
    t = normalize_space(time_raw)
    if not t or ":" not in t:
        return None
    m = re.match(r"^(?P<m>\d+):(?P<s>\d+)(?:\.(?P<d>\d+))?$", t)
    if not m:
        return None
    minutes = int(m.group("m"))
    seconds = int(m.group("s"))
    dec = m.group("d")
    frac = float(f"0.{dec}") if dec else 0.0
    return minutes * 60.0 + seconds + frac


def _parse_passing_order_arr(raw: str) -> Optional[list[int]]:
    t = normalize_space(raw)
    if not t or "-" not in t:
        return None
    parts = [p for p in re.split(r"[-－]", t) if p.strip()]
    out: list[int] = []
    for p in parts:
        try:
            out.append(int(p))
        except ValueError:
            return None
    return out or None


def _parse_body_weight(text: str) -> tuple[Optional[int], Optional[int]]:
    t = normalize_space(text)
    if not t or "計不" in t:
        return (None, None)
    m = re.search(r"(\d+)\s*\(\s*([+\-−±]?\d+)\s*\)", t)
    if m:
        bw = int(m.group(1))
        diff_raw = m.group(2).replace("−", "-").replace("±", "0")
        try:
            diff = int(diff_raw)
        except ValueError:
            diff = None
        return (bw, diff)
    ints = extract_ints(t)
    if ints:
        return (ints[0], None)
    return (None, None)


@dataclass(frozen=True)
class _Last5Meta:
    finish_pos: Optional[int]
    past_race_date: Optional[str]
    track_condition: Optional[str]
    runners: Optional[int]
    place: Optional[str]
    direction: Optional[str]
    distance_m: Optional[int]
    horse_no_in_race: Optional[int]


def _parse_last5_meta(div: Tag) -> _Last5Meta:
    txt = normalize_space(div.get_text(" ", strip=True))
    if not txt or txt in {"&nbsp;"}:
        return _Last5Meta(None, None, None, None, None, None, None, None)

    finish_pos: Optional[int] = None
    rank_tag = div.find("span", class_=lambda c: c and "pastRank" in c)
    if rank_tag is not None:
        finish_pos = _parse_int(rank_tag.get_text(" ", strip=True))

    date: Optional[str] = None
    cond: Optional[str] = None
    runners: Optional[int] = None
    m = re.search(r"(?P<yy>\d{2})\.(?P<mm>\d{2})\.(?P<dd>\d{2})\s*(?P<cond>\S+)\s*(?P<r>\d+)頭", txt)
    if m:
        yy = int(m.group("yy"))
        yyyy = 1900 + yy if yy >= 70 else 2000 + yy
        date = f"{yyyy:04d}-{int(m.group('mm')):02d}-{int(m.group('dd')):02d}"
        cond = m.group("cond")
        runners = int(m.group("r"))

    place: Optional[str] = None
    direction: Optional[str] = None
    distance_m: Optional[int] = None
    horse_no_in_race: Optional[int] = None
    m2 = re.search(r"(?P<place>\S+)\s*(?P<dir>[左右直])\s*(?P<dist>\d+)\s*(?P<no>\d+)番", txt)
    if m2:
        place = m2.group("place")
        direction = m2.group("dir")
        distance_m = int(m2.group("dist"))
        horse_no_in_race = int(m2.group("no"))

    return _Last5Meta(
        finish_pos=finish_pos,
        past_race_date=date,
        track_condition=cond,
        runners=runners,
        place=place,
        direction=direction,
        distance_m=distance_m,
        horse_no_in_race=horse_no_in_race,
    )


def _parse_last5_stats(td: Tag) -> tuple[Optional[int], Optional[int], Optional[str], Optional[float]]:
    txt = normalize_space(td.get_text(" ", strip=True))
    if not txt or txt in {"&nbsp;"}:
        return (None, None, None, None)
    m = re.match(r"^(?P<pop>\d+)人\s+(?P<bw>\d+)\s+(?P<jockey>.+?)\s+(?P<burden>\d+(?:\.\d+)?)$", txt)
    if not m:
        return (None, None, None, None)
    pop = int(m.group("pop"))
    bw = int(m.group("bw"))
    jockey = normalize_space(m.group("jockey"))
    if jockey and jockey[0] in _ALLOWANCE_SYMBOLS:
        jockey = jockey[1:]
    try:
        burden = float(m.group("burden"))
    except ValueError:
        burden = None
    return (pop, bw, jockey or None, burden)


def _parse_last5_time(td: Tag) -> tuple[Optional[str], Optional[float], Optional[str], Optional[list[int]], Optional[float]]:
    txt = normalize_space(td.get_text(" ", strip=True))
    if not txt or txt in {"&nbsp;"}:
        return (None, None, None, None, None)
    parts = txt.split(" ")
    time_raw = parts[0] if parts else None
    passing_raw = parts[1] if len(parts) >= 2 else None
    last3f = _parse_float(parts[2]) if len(parts) >= 3 else None
    return (
        time_raw,
        _parse_time_sec(time_raw or ""),
        passing_raw,
        _parse_passing_order_arr(passing_raw or "") if passing_raw else None,
        last3f,
    )


def _parse_last5_diff(td: Tag) -> tuple[Optional[float], Optional[str]]:
    txt = normalize_space(td.get_text(" ", strip=True))
    if not txt or txt in {"&nbsp;"}:
        return (None, None)
    parts = txt.split(" ", 1)
    diff = _parse_float(parts[0])
    winner = normalize_space(parts[1]) if len(parts) == 2 else None
    return (diff, winner or None)


def _parse_race_header(
    soup: BeautifulSoup, *, race_date: str, baba_code: int, race_no: int
) -> RaceNormalized:
    race_id = _race_id(baba_code=baba_code, race_date=race_date, race_no=race_no)
    h4 = soup.select_one("article.raceCard h4")
    post_time: Optional[str] = None
    if h4 is not None:
        m = re.search(r"(\d{1,2}:\d{2})発走", normalize_space(h4.get_text(" ", strip=True)))
        if m:
            post_time = m.group(1)

    race_name = None
    h3 = soup.select_one("section.raceTitle h3")
    if h3 is not None:
        race_name = normalize_space(h3.get_text(" ", strip=True)) or None

    surface = None
    direction = None
    distance_m: Optional[int] = None
    weather = None
    track_condition = None
    li = soup.select_one("section.raceTitle ul.dataArea li")
    if li is not None:
        txt = normalize_space(li.get_text(" ", strip=True))
        # e.g. "ダート 1400ｍ（右） 天候：晴 馬場：良 ..."
        m = re.search(r"^(?P<surface>\S+)\s+(?P<dist>\d+)ｍ（(?P<dir>[^）]+)）", txt)
        if m:
            surface = m.group("surface")
            distance_m = int(m.group("dist"))
            direction = m.group("dir")
        m = re.search(r"天候：(?P<w>\S+)", txt)
        if m:
            weather = m.group("w")
        m = re.search(r"馬場：(?P<b>\S+)", txt)
        if m:
            track_condition = m.group("b")

    return RaceNormalized(
        race_id=race_id,
        race_date=race_date,
        baba_code=baba_code,
        race_no=race_no,
        post_time=post_time,
        race_name=race_name,
        surface=surface,
        distance_m=distance_m,
        direction=direction,
        weather=weather,
        track_condition=track_condition,
    )


def _parse_person_text(text: str) -> tuple[str, str]:
    """Parse 'name（affiliation）' into (name, affiliation)."""
    t = normalize_space(text)
    if not t:
        return ("", "")
    if "（" in t and "）" in t:
        name = normalize_space(t.split("（", 1)[0])
        aff = normalize_space(t.split("（", 1)[1].split("）", 1)[0])
        return (name, aff)
    return (t, "")


def _parse_arrival_table(arrival: Tag) -> tuple[dict[str, tuple[int, int, int, int]], tuple[str, str]]:
    counts: dict[str, tuple[int, int, int, int]] = {}
    best_time_raw = ""
    best_time_good_raw = ""
    for tr in arrival.find_all("tr", recursive=False):
        tds = tr.find_all("td", recursive=False)
        if not tds:
            continue
        label = normalize_space(tds[0].get_text(" ", strip=True)).replace("\xa0", "")
        if label in {"全", "左", "右", "場", "距"} and len(tds) >= 5:
            first = extract_ints(tds[1].get_text(" ", strip=True))
            second = extract_ints(tds[2].get_text(" ", strip=True))
            third = extract_ints(tds[3].get_text(" ", strip=True))
            out = extract_ints(tds[4].get_text(" ", strip=True))
            if not (first and second and third and out):
                continue
            counts[label] = (first[0], second[0], third[0], out[0])
            continue

        # best time row: <td colspan="2">1:32.2</td><td colspan="3">良1:32.2</td>
        if len(tds) == 2:
            t1 = normalize_space(tds[0].get_text(" ", strip=True))
            t2 = normalize_space(tds[1].get_text(" ", strip=True))
            if ":" in t1:
                best_time_raw = t1
                best_time_good_raw = t2.lstrip("良").strip() if t2.startswith("良") else t2
    return counts, (best_time_raw, best_time_good_raw)


def parse_deba_table_normalized(
    html: bytes, *, race_date: str, baba_code: int, race_no: int
) -> DebaTableNormalized:
    soup = BeautifulSoup(html, "lxml")
    rk = RaceKey(race_date=race_date, baba_code=baba_code, race_no=race_no)
    race = _parse_race_header(soup, race_date=race_date, baba_code=baba_code, race_no=race_no)

    table = soup.select_one("section.cardTable table")
    if table is None:
        raise ValueError("DebaTable table not found")

    race_id = race.race_id
    surface = race.surface
    distance_m = race.distance_m

    persons: dict[str, PersonNormalized] = {}
    horses: list[HorseNormalized] = []
    entries: list[RaceEntryNormalized] = []
    perf_total: list[PerfNormalized] = []
    perf_dirt_left: list[PerfNormalized] = []
    perf_dirt_right: list[PerfNormalized] = []
    perf_track: list[PerfNormalized] = []
    perf_distance: list[PerfNormalized] = []
    best_time_rows: list[BestTimeNormalized] = []
    last5_rows: list[Last5RaceNormalized] = []

    for tr0 in table.select("tr.tBorder"):
        # group 5 rows per horse
        group: list[Tag] = [tr0]
        sib: Optional[Tag] = tr0
        while len(group) < 5:
            sib = sib.find_next_sibling("tr") if sib is not None else None
            if sib is None:
                break
            if "tBorder" in (sib.get("class") or []):
                break
            group.append(sib)
        if len(group) < 4:
            continue

        tr1 = group[1] if len(group) >= 2 else None
        tr2 = group[2] if len(group) >= 3 else None
        tr3 = group[3] if len(group) >= 4 else None
        tr4 = group[4] if len(group) >= 5 else None

        td_waku = tr0.find("td", class_=lambda c: c and "courseNum" in c)
        td_horse_no = tr0.find("td", class_="horseNum")
        waku = _parse_int(td_waku.get_text(" ", strip=True)) if td_waku is not None else None
        horse_no = _parse_int(td_horse_no.get_text(" ", strip=True)) if td_horse_no is not None else None
        if horse_no is None:
            continue

        a_horse = tr0.find("a", class_="horseName")
        horse_name = normalize_space(a_horse.get_text(" ", strip=True)) if a_horse is not None else ""
        if not horse_name:
            continue
        horse_key = _horse_key(horse_name)

        a_jockey = tr0.find("a", class_="jockeyName")
        jockey_name, jockey_aff = ("", "")
        if a_jockey is not None:
            jockey_name, jockey_aff = _parse_person_text(a_jockey.get_text(" ", strip=True))
        jockey_key = _person_key(role="jockey", name=jockey_name, affiliation=jockey_aff) if jockey_name else None
        if jockey_key and jockey_key not in persons:
            persons[jockey_key] = PersonNormalized(
                person_key=jockey_key, role="jockey", name=jockey_name, affiliation=jockey_aff
            )

        # win odds + popularity (from row0 odds cell)
        win_odds: Optional[float] = None
        popularity: Optional[int] = None
        odds_cell = tr0.find("td", class_="odds_weight")
        if odds_cell is not None:
            span = odds_cell.find("span")
            if span is not None:
                win_odds = _parse_float(span.get_text(" ", strip=True))
            txt = normalize_space(odds_cell.get_text(" ", strip=True))
            m = re.search(r"\((\d+)人気\)", txt)
            if m:
                popularity = int(m.group(1))

        # arrival/perf + best time
        perf_counts: dict[str, tuple[int, int, int, int]] = {}
        best_time_raw = ""
        best_time_good_raw = ""
        td_result = tr0.find("td", class_="result")
        if td_result is not None:
            arrival = td_result.find("table", class_="arrival")
            if arrival is not None:
                perf_counts, (best_time_raw, best_time_good_raw) = _parse_arrival_table(arrival)

        def make_perf(kind: str, counts: tuple[int, int, int, int]) -> PerfNormalized:
            first, second, third, out = counts
            starts = first + second + third + out
            return PerfNormalized(
                perf_key=f"{kind}:{horse_name}:{race_id}",
                horse_key=horse_key,
                first_cnt=first,
                second_cnt=second,
                third_cnt=third,
                out_cnt=out,
                starts=starts,
            )

        if "全" in perf_counts:
            perf_total.append(make_perf("perf_total", perf_counts["全"]))
        if "左" in perf_counts:
            perf_dirt_left.append(make_perf("perf_dirt_left", perf_counts["左"]))
        if "右" in perf_counts:
            perf_dirt_right.append(make_perf("perf_dirt_right", perf_counts["右"]))
        if "場" in perf_counts:
            perf_track.append(make_perf("perf_track", perf_counts["場"]))
        if "距" in perf_counts:
            perf_distance.append(make_perf("perf_distance", perf_counts["距"]))

        best_key = f"best_time:{horse_name}:{race_id}"
        best_time_rows.append(
            BestTimeNormalized(
                best_time_key=best_key,
                horse_key=horse_key,
                baba_code=baba_code,
                surface=surface,
                distance_m=distance_m,
                best_time_raw=best_time_raw,
                best_time_sec=_parse_time_sec(best_time_raw) if best_time_raw else None,
                best_time_good_raw=best_time_good_raw,
                best_time_good_sec=_parse_time_sec(best_time_good_raw) if best_time_good_raw else None,
            )
        )

        # horse attributes (row1)
        sex: Optional[str] = None
        age: Optional[int] = None
        coat: Optional[str] = None
        birth_md_raw: Optional[str] = None
        birth_month: Optional[int] = None
        birth_day: Optional[int] = None
        burden_weight: Optional[float] = None
        burden_mark = ""
        if tr1 is not None:
            tds = tr1.find_all("td", recursive=False)
            if len(tds) >= 4:
                sex_age = normalize_space(tds[0].get_text(" ", strip=True))
                if sex_age:
                    sex = sex_age[0]
                    m = re.search(r"(\d+)", sex_age)
                    if m:
                        age = int(m.group(1))
                coat = normalize_space(tds[1].get_text(" ", strip=True)) or None
                bm = re.search(r"(\d{2})\.(\d{2})生", normalize_space(tds[2].get_text(" ", strip=True)))
                if bm:
                    birth_md_raw = f"{bm.group(1)}.{bm.group(2)}"
                    birth_month = int(bm.group(1))
                    birth_day = int(bm.group(2))
                burden_cell = normalize_space(tds[3].get_text(" ", strip=True))
                m = re.search(r"([★▲△◇☆])?\s*(\d+(?:\.\d+)?)", burden_cell)
                if m:
                    burden_mark = m.group(1) or ""
                    try:
                        burden_weight = float(m.group(2))
                    except ValueError:
                        burden_weight = None

        sire = None
        trainer_name = ""
        trainer_aff = ""
        body_weight = None
        body_weight_diff = None
        if tr2 is not None:
            tds = tr2.find_all("td", recursive=False)
            if len(tds) >= 3:
                sire = normalize_space(tds[0].get_text(" ", strip=True)) or None
                trainer_name, trainer_aff = ("", "")
                trainer_tag = tds[1].find("a") if len(tds) >= 2 else None
                if trainer_tag is not None:
                    trainer_name, trainer_aff = _parse_person_text(trainer_tag.get_text(" ", strip=True))
                if len(tds) >= 3:
                    body_weight, body_weight_diff = _parse_body_weight(tds[2].get_text(" ", strip=True))

        trainer_key = _person_key(role="trainer", name=trainer_name, affiliation=trainer_aff) if trainer_name else None
        if trainer_key and trainer_key not in persons:
            persons[trainer_key] = PersonNormalized(
                person_key=trainer_key, role="trainer", name=trainer_name, affiliation=trainer_aff
            )

        dam = None
        owner_name = ""
        if tr3 is not None:
            tds = tr3.find_all("td", recursive=False)
            if len(tds) >= 2:
                dam = normalize_space(tds[0].get_text(" ", strip=True)) or None
                owner_name = normalize_space(tds[1].get_text(" ", strip=True))

        owner_key = _person_key(role="owner", name=owner_name, affiliation="") if owner_name else None
        if owner_key and owner_key not in persons:
            persons[owner_key] = PersonNormalized(
                person_key=owner_key, role="owner", name=owner_name, affiliation=""
            )

        dam_sire = None
        breeder = None
        if tr4 is not None:
            tds = tr4.find_all("td", recursive=False)
            if len(tds) >= 2:
                dam_sire = _strip_parens(tds[0].get_text(" ", strip=True)) or None
                breeder = normalize_space(tds[1].get_text(" ", strip=True)) or None

        horses.append(
            HorseNormalized(
                horse_key=horse_key,
                horse_name=horse_name,
                sex=sex,
                age=age,
                coat=coat,
                birth_month=birth_month,
                birth_day=birth_day,
                birth_md_raw=birth_md_raw,
                sire=sire,
                dam=dam,
                dam_sire=dam_sire,
                breeder=breeder,
            )
        )

        entries.append(
            RaceEntryNormalized(
                race_id=race_id,
                horse_no=horse_no,
                waku=waku,
                horse_key=horse_key,
                burden_weight=burden_weight,
                burden_mark=burden_mark,
                body_weight=body_weight,
                body_weight_diff=body_weight_diff,
                win_odds=win_odds,
                popularity=popularity,
                jockey_person_key=jockey_key,
                trainer_person_key=trainer_key,
                owner_person_key=owner_key,
                perf_total_key=f"perf_total:{horse_name}:{race_id}" if "全" in perf_counts else None,
                perf_dirt_left_key=f"perf_dirt_left:{horse_name}:{race_id}" if "左" in perf_counts else None,
                perf_dirt_right_key=f"perf_dirt_right:{horse_name}:{race_id}" if "右" in perf_counts else None,
                perf_track_key=f"perf_track:{horse_name}:{race_id}" if "場" in perf_counts else None,
                perf_distance_key=f"perf_distance:{horse_name}:{race_id}" if "距" in perf_counts else None,
                best_time_key=best_key,
            )
        )

        # last5 extraction (best-effort; skip empty columns)
        meta_divs = tr0.select("div.raceInfo")
        stats_tds = tr2.find_all("td", recursive=False)[3:8] if tr2 is not None else []
        time_tds = tr3.find_all("td", recursive=False)[2:7] if tr3 is not None else []
        diff_tds = tr4.find_all("td", recursive=False)[3:8] if tr4 is not None else []

        for i, meta_div in enumerate(meta_divs[:5]):
            meta = _parse_last5_meta(meta_div)
            if meta.past_race_date is None:
                continue
            pop, bw, jockey_n, burden_w = _parse_last5_stats(stats_tds[i]) if i < len(stats_tds) else (None, None, None, None)
            t_raw, t_sec, pass_raw, pass_arr, last3f = (
                _parse_last5_time(time_tds[i]) if i < len(time_tds) else (None, None, None, None, None)
            )
            diff, winner = _parse_last5_diff(diff_tds[i]) if i < len(diff_tds) else (None, None)
            last5_rows.append(
                Last5RaceNormalized(
                    race_id=race_id,
                    horse_no=horse_no,
                    order_in_last5=i + 1,
                    finish_pos=meta.finish_pos,
                    past_race_date=meta.past_race_date,
                    track_condition=meta.track_condition,
                    runners=meta.runners,
                    place=meta.place,
                    direction=meta.direction,
                    distance_m=meta.distance_m,
                    horse_no_in_race=meta.horse_no_in_race,
                    popularity=pop,
                    body_weight=bw,
                    jockey_name=jockey_n,
                    burden_weight=burden_w,
                    time_raw=t_raw,
                    time_sec=t_sec,
                    passing_order_raw=pass_raw,
                    passing_order_arr=pass_arr,
                    last3f=last3f,
                    time_diff=diff,
                    winner_name=winner,
                )
            )

    # stable ordering for tests/exports
    horses.sort(key=lambda h: h.horse_name)
    entries.sort(key=lambda e: e.horse_no)
    last5_rows.sort(key=lambda r: (r.horse_no, r.order_in_last5))

    def _sort_perf(items: list[PerfNormalized]) -> None:
        items.sort(key=lambda p: p.perf_key)

    _sort_perf(perf_total)
    _sort_perf(perf_dirt_left)
    _sort_perf(perf_dirt_right)
    _sort_perf(perf_track)
    _sort_perf(perf_distance)
    best_time_rows.sort(key=lambda b: b.best_time_key)

    persons_list = list(persons.values())
    persons_list.sort(key=lambda p: p.person_key)

    return DebaTableNormalized(
        race_key=rk,
        race=race,
        persons=persons_list,
        horses=horses,
        race_entries=entries,
        perf_total=perf_total,
        perf_dirt_left=perf_dirt_left,
        perf_dirt_right=perf_dirt_right,
        perf_track=perf_track,
        perf_distance=perf_distance,
        best_time=best_time_rows,
        last5=last5_rows,
    )
