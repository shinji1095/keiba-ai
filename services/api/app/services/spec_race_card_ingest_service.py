from __future__ import annotations

import datetime as dt
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.models.spec_best_time import SpecBestTime
from app.db.models.spec_entry_last5_race import SpecEntryLast5Race
from app.db.models.spec_horse import SpecHorse
from app.db.models.spec_perf import (
    SpecPerfDirtLeft,
    SpecPerfDirtRight,
    SpecPerfDistance,
    SpecPerfTotal,
    SpecPerfTrack,
)
from app.db.models.spec_person import SpecPerson
from app.db.models.spec_race import SpecRace
from app.db.models.spec_race_day import SpecRaceDay
from app.db.models.spec_race_entry import SpecRaceEntry
from app.db.models.spec_racecourse import SpecRacecourse
from app.db.models.venue import Venue


def _parse_date(v: object) -> Optional[dt.date]:
    if isinstance(v, dt.date):
        return v
    if isinstance(v, str) and v:
        try:
            return dt.date.fromisoformat(v)
        except ValueError:
            return None
    return None


def _parse_time(v: object) -> Optional[dt.time]:
    if isinstance(v, dt.time):
        return v
    if isinstance(v, str) and v:
        try:
            return dt.time.fromisoformat(v)
        except ValueError:
            return None
    return None


class SpecRaceCardIngestService:
    """Ingest scraper's race_cards payload into spec-aligned normalized tables.

    Notes:
    - The spec tables are additive alongside legacy tables (races/race_entries/...).
    - We treat payload keys as best-effort; missing optional fields are stored as NULL.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_race_cards(self, items: list[dict[str, Any]]) -> None:
        # There can be multiple captures for same race_id; apply in captured_at order.
        items_sorted = sorted(
            items,
            key=lambda x: str(x.get("captured_at") or ""),
        )
        for payload in items_sorted:
            self.upsert_race_card(payload)

    def upsert_race_card(self, payload: dict[str, Any]) -> None:
        race = payload.get("race")
        race_key = payload.get("race_key")
        if not isinstance(race, dict) or not isinstance(race_key, dict):
            return

        race_id = str(race.get("race_id") or "")
        if not race_id:
            return
        race_date = _parse_date(race_key.get("race_date"))
        baba_code = race_key.get("baba_code")
        race_no = race_key.get("race_no")
        try:
            baba_code_i = int(baba_code)
            race_no_i = int(race_no)
        except (TypeError, ValueError):
            return
        if race_date is None:
            return

        # racecourse (name comes from legacy venues if available)
        venue = self.db.query(Venue).filter(Venue.baba_code == baba_code_i).first()
        course_name = venue.venue_name if venue else f"baba_{baba_code_i}"
        self._upsert_racecourse(baba_code_i, course_name)
        self._ensure_race_day(race_date, baba_code_i)

        # race (spec)
        self._upsert_race(
            race_id=race_id,
            race_date=race_date,
            baba_code=baba_code_i,
            race_no=race_no_i,
            post_time=_parse_time(race.get("post_time")),
            race_name=str(race.get("race_name") or "UNKNOWN"),
            surface=_none_if_empty(race.get("surface")),
            distance_m=_int_or_none(race.get("distance_m")),
            direction=_none_if_empty(race.get("direction")),
            weather=_none_if_empty(race.get("weather")),
            track_condition=_none_if_empty(race.get("track_condition")),
        )

        # persons
        person_id_by_key: dict[str, int] = {}
        persons = payload.get("persons")
        if isinstance(persons, list):
            for p in persons:
                if not isinstance(p, dict):
                    continue
                k = str(p.get("person_key") or "")
                role = str(p.get("role") or "")
                name = str(p.get("name") or "")
                aff = str(p.get("affiliation") or "")
                if not k or not role or not name:
                    continue
                pid = self._get_or_create_person(role=role, name=name, affiliation=aff)
                person_id_by_key[k] = pid

        # horses
        horse_id_by_key: dict[str, int] = {}
        horses = payload.get("horses")
        if isinstance(horses, list):
            for h in horses:
                if not isinstance(h, dict):
                    continue
                k = str(h.get("horse_key") or "")
                name = str(h.get("horse_name") or h.get("horse") or "")
                if not k or not name:
                    continue
                hid = self._get_or_create_horse(
                    name=name,
                    sex=_none_if_empty(h.get("sex")),
                    age=_int_or_none(h.get("age")),
                    coat=_none_if_empty(h.get("coat")),
                    birth_month=_int_or_none(h.get("birth_month")),
                    birth_day=_int_or_none(h.get("birth_day")),
                    birth_md_raw=_none_if_empty(h.get("birth_md_raw")),
                    sire=_none_if_empty(h.get("sire")),
                    dam=_none_if_empty(h.get("dam")),
                    dam_sire=_none_if_empty(h.get("dam_sire")),
                    breeder=_none_if_empty(h.get("breeder")),
                )
                horse_id_by_key[k] = hid

        # perf_* and best_time
        perf_total_id_by_horse: dict[int, int] = {}
        perf_left_id_by_horse: dict[int, int] = {}
        perf_right_id_by_horse: dict[int, int] = {}
        perf_track_id_by_horse: dict[int, int] = {}
        perf_distance_id_by_horse: dict[int, int] = {}
        best_time_id_by_horse: dict[int, int] = {}

        self._upsert_perf_list(
            payload.get("perf_total"),
            horse_id_by_key,
            table="total",
            baba_code=baba_code_i,
            surface=_none_if_empty(race.get("surface")) or "ダート",
            distance_m=_int_or_none(race.get("distance_m")) or 0,
            out_map=perf_total_id_by_horse,
        )
        self._upsert_perf_list(
            payload.get("perf_dirt_left"),
            horse_id_by_key,
            table="dirt_left",
            baba_code=baba_code_i,
            surface="ダート",
            distance_m=_int_or_none(race.get("distance_m")) or 0,
            out_map=perf_left_id_by_horse,
        )
        self._upsert_perf_list(
            payload.get("perf_dirt_right"),
            horse_id_by_key,
            table="dirt_right",
            baba_code=baba_code_i,
            surface="ダート",
            distance_m=_int_or_none(race.get("distance_m")) or 0,
            out_map=perf_right_id_by_horse,
        )
        self._upsert_perf_list(
            payload.get("perf_track"),
            horse_id_by_key,
            table="track",
            baba_code=baba_code_i,
            surface=_none_if_empty(race.get("surface")) or "ダート",
            distance_m=_int_or_none(race.get("distance_m")) or 0,
            out_map=perf_track_id_by_horse,
        )
        self._upsert_perf_list(
            payload.get("perf_distance"),
            horse_id_by_key,
            table="distance",
            baba_code=baba_code_i,
            surface=_none_if_empty(race.get("surface")) or "ダート",
            distance_m=_int_or_none(race.get("distance_m")) or 0,
            out_map=perf_distance_id_by_horse,
        )
        self._upsert_best_time_list(
            payload.get("best_time"),
            horse_id_by_key,
            out_map=best_time_id_by_horse,
        )

        # race_entry
        entries = payload.get("race_entries")
        if isinstance(entries, list):
            for e in entries:
                if not isinstance(e, dict):
                    continue
                horse_no = _int_or_none(e.get("horse_no"))
                if horse_no is None:
                    continue
                horse_key = str(e.get("horse_key") or "")
                horse_id = horse_id_by_key.get(horse_key)

                bw = _float_or_none(e.get("burden_weight"))
                if bw is None:
                    # spec schema requires burden_weight_display NOT NULL; treat missing as 0.0 (best-effort).
                    bw = 0.0
                symbol = str(e.get("burden_mark") or "") or None
                allowance_kg = _allowance_kg(symbol)
                base_bw = bw + allowance_kg if allowance_kg is not None else None

                self._upsert_race_entry(
                    race_id=race_id,
                    horse_no=horse_no,
                    waku=_int_or_none(e.get("waku")),
                    horse_id=horse_id,
                    burden_weight_display=bw,
                    apprentice_allowance_symbol=symbol,
                    apprentice_allowance_kg=allowance_kg,
                    burden_weight_base=base_bw,
                    body_weight=_int_or_none(e.get("body_weight")),
                    body_weight_diff=_int_or_none(e.get("body_weight_diff")),
                    win_odds=_float_or_none(e.get("win_odds")),
                    popularity=_int_or_none(e.get("popularity")),
                    jockey_person_id=person_id_by_key.get(str(e.get("jockey_person_key") or "")),
                    trainer_person_id=person_id_by_key.get(str(e.get("trainer_person_key") or "")),
                    owner_person_id=person_id_by_key.get(str(e.get("owner_person_key") or "")),
                    perf_total_id=(horse_id and perf_total_id_by_horse.get(horse_id)) or None,
                    perf_dirt_left_id=(horse_id and perf_left_id_by_horse.get(horse_id)) or None,
                    perf_dirt_right_id=(horse_id and perf_right_id_by_horse.get(horse_id)) or None,
                    perf_track_id=(horse_id and perf_track_id_by_horse.get(horse_id)) or None,
                    perf_distance_id=(horse_id and perf_distance_id_by_horse.get(horse_id)) or None,
                    best_time_id=(horse_id and best_time_id_by_horse.get(horse_id)) or None,
                )

        # last5
        last5 = payload.get("last5")
        if isinstance(last5, list):
            for r in last5:
                if not isinstance(r, dict):
                    continue
                horse_no = _int_or_none(r.get("horse_no"))
                order_in_last5 = _int_or_none(r.get("order_in_last5"))
                if horse_no is None or order_in_last5 is None:
                    continue
                self._upsert_last5(
                    race_id=race_id,
                    horse_no=horse_no,
                    order_in_last5=order_in_last5,
                    finish_pos=_int_or_none(r.get("finish_pos")),
                    past_race_date=_parse_date(r.get("past_race_date")),
                    track_condition=_none_if_empty(r.get("track_condition")),
                    runners=_int_or_none(r.get("runners")),
                    place=_none_if_empty(r.get("place")),
                    direction=_none_if_empty(r.get("direction")),
                    distance_m=_int_or_none(r.get("distance_m")),
                    horse_no_in_race=_int_or_none(r.get("horse_no_in_race")),
                    popularity=_int_or_none(r.get("popularity")),
                    body_weight=_int_or_none(r.get("body_weight")),
                    jockey_name=_none_if_empty(r.get("jockey_name")),
                    burden_weight=_float_or_none(r.get("burden_weight")),
                    time_raw=_none_if_empty(r.get("time_raw")),
                    time_sec=_float_or_none(r.get("time_sec")),
                    passing_order_raw=_none_if_empty(r.get("passing_order_raw")),
                    passing_order_arr=_list_int_or_none(r.get("passing_order_arr")),
                    last3f=_float_or_none(r.get("last3f")),
                    time_diff=_float_or_none(r.get("time_diff")),
                    winner_name=_none_if_empty(r.get("winner_name")),
                )

    def _upsert_racecourse(self, baba_code: int, name: str) -> None:
        row = self.db.query(SpecRacecourse).filter(SpecRacecourse.baba_code == baba_code).first()
        if row is None:
            self.db.add(SpecRacecourse(baba_code=baba_code, name=name))
            return
        if row.name != name:
            row.name = name

    def _ensure_race_day(self, race_date: dt.date, baba_code: int) -> None:
        row = (
            self.db.query(SpecRaceDay)
            .filter(SpecRaceDay.race_date == race_date, SpecRaceDay.baba_code == baba_code)
            .first()
        )
        if row is None:
            self.db.add(SpecRaceDay(race_date=race_date, baba_code=baba_code))

    def _upsert_race(
        self,
        *,
        race_id: str,
        race_date: dt.date,
        baba_code: int,
        race_no: int,
        post_time: Optional[dt.time],
        race_name: str,
        surface: Optional[str],
        distance_m: Optional[int],
        direction: Optional[str],
        weather: Optional[str],
        track_condition: Optional[str],
    ) -> None:
        row = self.db.query(SpecRace).filter(SpecRace.race_id == race_id).first()
        if row is None:
            self.db.add(
                SpecRace(
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
            )
            return
        row.race_date = race_date
        row.baba_code = baba_code
        row.race_no = race_no
        row.post_time = post_time
        row.race_name = race_name or row.race_name
        row.surface = surface
        row.distance_m = distance_m
        row.direction = direction
        row.weather = weather
        row.track_condition = track_condition

    def _get_or_create_person(self, *, role: str, name: str, affiliation: str) -> int:
        aff = affiliation or ""
        row = (
            self.db.query(SpecPerson)
            .filter(SpecPerson.role == role, SpecPerson.name == name, SpecPerson.affiliation == aff)
            .first()
        )
        if row is None:
            row = SpecPerson(role=role, name=name, affiliation=aff)
            self.db.add(row)
            self.db.flush()
        return int(row.person_id)

    def _get_or_create_horse(
        self,
        *,
        name: str,
        sex: Optional[str],
        age: Optional[int],
        coat: Optional[str],
        birth_month: Optional[int],
        birth_day: Optional[int],
        birth_md_raw: Optional[str],
        sire: Optional[str],
        dam: Optional[str],
        dam_sire: Optional[str],
        breeder: Optional[str],
    ) -> int:
        # NOTE: no unique constraint on (name, birth_md_raw...). Use a best-effort lookup.
        q = self.db.query(SpecHorse).filter(SpecHorse.name == name)
        if birth_md_raw:
            q = q.filter(SpecHorse.birth_md_raw == birth_md_raw)
        row = q.first()
        if row is None:
            row = SpecHorse(
                name=name,
                nar_horse_id=None,
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
            self.db.add(row)
            self.db.flush()
        else:
            # Update nullable fields (best-effort)
            row.sex = sex or row.sex
            row.age = age if age is not None else row.age
            row.coat = coat or row.coat
            row.birth_month = birth_month if birth_month is not None else row.birth_month
            row.birth_day = birth_day if birth_day is not None else row.birth_day
            row.birth_md_raw = birth_md_raw or row.birth_md_raw
            row.sire = sire or row.sire
            row.dam = dam or row.dam
            row.dam_sire = dam_sire or row.dam_sire
            row.breeder = breeder or row.breeder
        return int(row.horse_id)

    def _upsert_perf_list(
        self,
        perf_list: object,
        horse_id_by_key: dict[str, int],
        *,
        table: str,
        baba_code: int,
        surface: str,
        distance_m: int,
        out_map: dict[int, int],
    ) -> None:
        if not isinstance(perf_list, list):
            return
        for p in perf_list:
            if not isinstance(p, dict):
                continue
            horse_key = str(p.get("horse_key") or "")
            hid = horse_id_by_key.get(horse_key)
            if not hid:
                continue
            first_cnt = _int_or_none(p.get("first_cnt")) or 0
            second_cnt = _int_or_none(p.get("second_cnt")) or 0
            third_cnt = _int_or_none(p.get("third_cnt")) or 0
            out_cnt = _int_or_none(p.get("out_cnt")) or 0

            if table == "total":
                row = self._upsert_perf_single(SpecPerfTotal, "perf_total_id", hid, None, None, None, first_cnt, second_cnt, third_cnt, out_cnt)
                out_map[hid] = row
            elif table == "dirt_left":
                row = self._upsert_perf_single(SpecPerfDirtLeft, "perf_dirt_left_id", hid, None, None, None, first_cnt, second_cnt, third_cnt, out_cnt)
                out_map[hid] = row
            elif table == "dirt_right":
                row = self._upsert_perf_single(SpecPerfDirtRight, "perf_dirt_right_id", hid, None, None, None, first_cnt, second_cnt, third_cnt, out_cnt)
                out_map[hid] = row
            elif table == "track":
                row = self._upsert_perf_single(SpecPerfTrack, "perf_track_id", hid, baba_code, surface, None, first_cnt, second_cnt, third_cnt, out_cnt)
                out_map[hid] = row
            elif table == "distance":
                row = self._upsert_perf_single(SpecPerfDistance, "perf_distance_id", hid, baba_code, surface, distance_m, first_cnt, second_cnt, third_cnt, out_cnt)
                out_map[hid] = row

    def _upsert_perf_single(
        self,
        model,
        id_attr: str,
        horse_id: int,
        baba_code: Optional[int],
        surface: Optional[str],
        distance_m: Optional[int],
        first_cnt: int,
        second_cnt: int,
        third_cnt: int,
        out_cnt: int,
    ) -> int:
        q = self.db.query(model).filter(model.horse_id == horse_id)
        if hasattr(model, "baba_code") and baba_code is not None:
            q = q.filter(model.baba_code == baba_code)
        if hasattr(model, "surface") and surface is not None:
            q = q.filter(model.surface == surface)
        if hasattr(model, "distance_m") and distance_m is not None:
            q = q.filter(model.distance_m == distance_m)
        row = q.first()
        if row is None:
            kwargs = dict(
                horse_id=horse_id,
                first_cnt=first_cnt,
                second_cnt=second_cnt,
                third_cnt=third_cnt,
                out_cnt=out_cnt,
            )
            if hasattr(model, "baba_code") and baba_code is not None:
                kwargs["baba_code"] = baba_code
            if hasattr(model, "surface") and surface is not None:
                kwargs["surface"] = surface
            if hasattr(model, "distance_m") and distance_m is not None:
                kwargs["distance_m"] = distance_m
            row = model(**kwargs)
            self.db.add(row)
            self.db.flush()
        else:
            row.first_cnt = first_cnt
            row.second_cnt = second_cnt
            row.third_cnt = third_cnt
            row.out_cnt = out_cnt
        return int(getattr(row, id_attr))

    def _upsert_best_time_list(
        self,
        best_list: object,
        horse_id_by_key: dict[str, int],
        *,
        out_map: dict[int, int],
    ) -> None:
        if not isinstance(best_list, list):
            return
        for b in best_list:
            if not isinstance(b, dict):
                continue
            horse_key = str(b.get("horse_key") or "")
            hid = horse_id_by_key.get(horse_key)
            if not hid:
                continue
            baba_code = _int_or_none(b.get("baba_code"))
            surface = _none_if_empty(b.get("surface"))
            distance_m = _int_or_none(b.get("distance_m"))
            if baba_code is None or surface is None or distance_m is None:
                continue
            row = (
                self.db.query(SpecBestTime)
                .filter(
                    SpecBestTime.horse_id == hid,
                    SpecBestTime.baba_code == baba_code,
                    SpecBestTime.surface == surface,
                    SpecBestTime.distance_m == distance_m,
                )
                .first()
            )
            if row is None:
                row = SpecBestTime(
                    horse_id=hid,
                    baba_code=baba_code,
                    surface=surface,
                    distance_m=distance_m,
                    best_time_sec=_float_or_none(b.get("best_time_sec")),
                    best_time_good_sec=_float_or_none(b.get("best_time_good_sec")),
                    best_time_raw=str(b.get("best_time_raw") or ""),
                    best_time_good_raw=str(b.get("best_time_good_raw") or ""),
                )
                self.db.add(row)
                self.db.flush()
            else:
                row.best_time_sec = _float_or_none(b.get("best_time_sec"))
                row.best_time_good_sec = _float_or_none(b.get("best_time_good_sec"))
                row.best_time_raw = str(b.get("best_time_raw") or "")
                row.best_time_good_raw = str(b.get("best_time_good_raw") or "")
            out_map[hid] = int(row.best_time_id)

    def _upsert_race_entry(self, **kwargs: Any) -> None:
        race_id = kwargs["race_id"]
        horse_no = kwargs["horse_no"]
        row = (
            self.db.query(SpecRaceEntry)
            .filter(SpecRaceEntry.race_id == race_id, SpecRaceEntry.horse_no == horse_no)
            .first()
        )
        if row is None:
            self.db.add(SpecRaceEntry(**kwargs))
            return
        for k, v in kwargs.items():
            setattr(row, k, v)

    def _upsert_last5(self, **kwargs: Any) -> None:
        race_id = kwargs["race_id"]
        horse_no = kwargs["horse_no"]
        order = kwargs["order_in_last5"]
        row = (
            self.db.query(SpecEntryLast5Race)
            .filter(
                SpecEntryLast5Race.race_id == race_id,
                SpecEntryLast5Race.horse_no == horse_no,
                SpecEntryLast5Race.order_in_last5 == order,
            )
            .first()
        )
        if row is None:
            self.db.add(SpecEntryLast5Race(**kwargs))
            return
        for k, v in kwargs.items():
            setattr(row, k, v)


def _none_if_empty(v: object) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _int_or_none(v: object) -> Optional[int]:
    try:
        if v is None or v == "":
            return None
        return int(v)
    except (TypeError, ValueError):
        return None


def _float_or_none(v: object) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _list_int_or_none(v: object) -> Optional[list[int]]:
    if v is None:
        return None
    if isinstance(v, list):
        out: list[int] = []
        for x in v:
            try:
                out.append(int(x))
            except (TypeError, ValueError):
                continue
        return out or None
    return None


def _allowance_kg(symbol: Optional[str]) -> Optional[int]:
    if not symbol:
        return None
    mapping = {"★": 4, "▲": 3, "△": 2, "◇": 1, "☆": 1}
    return mapping.get(symbol)


