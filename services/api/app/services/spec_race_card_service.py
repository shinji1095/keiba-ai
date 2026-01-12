from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.core.errors import AppError
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
from app.db.models.spec_race_entry import SpecRaceEntry


class SpecRaceCardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_race_card(self, *, baba_code: int, race_date: dt.date, race_no: int) -> dict:
        race = (
            self.db.query(SpecRace)
            .filter(
                SpecRace.race_date == race_date,
                SpecRace.baba_code == baba_code,
                SpecRace.race_no == race_no,
            )
            .first()
        )
        if race is None:
            raise AppError.not_found("spec race not found")

        entries = (
            self.db.query(SpecRaceEntry)
            .filter(SpecRaceEntry.race_id == race.race_id)
            .order_by(SpecRaceEntry.horse_no.asc())
            .all()
        )

        person_ids: set[int] = set()
        horse_ids: set[int] = set()
        for e in entries:
            if e.jockey_person_id:
                person_ids.add(int(e.jockey_person_id))
            if e.trainer_person_id:
                person_ids.add(int(e.trainer_person_id))
            if e.owner_person_id:
                person_ids.add(int(e.owner_person_id))
            if e.horse_id:
                horse_ids.add(int(e.horse_id))

        persons = []
        if person_ids:
            rows = self.db.query(SpecPerson).filter(SpecPerson.person_id.in_(person_ids)).all()
            persons = [
                {
                    "person_id": int(p.person_id),
                    "role": p.role,
                    "name": p.name,
                    "affiliation": p.affiliation,
                }
                for p in rows
            ]
            persons.sort(key=lambda x: (x["role"], x["name"], x["affiliation"]))

        horses = []
        if horse_ids:
            rows = self.db.query(SpecHorse).filter(SpecHorse.horse_id.in_(horse_ids)).all()
            horses = [
                {
                    "horse_id": int(h.horse_id),
                    "name": h.name,
                    "sex": h.sex,
                    "age": h.age,
                    "coat": h.coat,
                    "birth_month": h.birth_month,
                    "birth_day": h.birth_day,
                    "birth_md_raw": h.birth_md_raw,
                    "sire": h.sire,
                    "dam": h.dam,
                    "dam_sire": h.dam_sire,
                    "breeder": h.breeder,
                }
                for h in rows
            ]
            horses.sort(key=lambda x: x["horse_id"])

        # perf tables (best-effort by horse_id)
        perf_total = self._perf_rows(SpecPerfTotal, horse_ids, id_field="perf_total_id")
        perf_dirt_left = self._perf_rows(SpecPerfDirtLeft, horse_ids, id_field="perf_dirt_left_id")
        perf_dirt_right = self._perf_rows(SpecPerfDirtRight, horse_ids, id_field="perf_dirt_right_id")
        perf_track = self._perf_rows(SpecPerfTrack, horse_ids, id_field="perf_track_id")
        perf_distance = self._perf_rows(SpecPerfDistance, horse_ids, id_field="perf_distance_id")

        best_time = []
        if horse_ids:
            rows = self.db.query(SpecBestTime).filter(SpecBestTime.horse_id.in_(horse_ids)).all()
            best_time = [
                {
                    "horse_id": int(b.horse_id),
                    "baba_code": int(b.baba_code),
                    "surface": b.surface,
                    "distance_m": int(b.distance_m),
                    "best_time_sec": float(b.best_time_sec) if b.best_time_sec is not None else None,
                    "best_time_good_sec": float(b.best_time_good_sec) if b.best_time_good_sec is not None else None,
                    "best_time_raw": b.best_time_raw,
                    "best_time_good_raw": b.best_time_good_raw,
                }
                for b in rows
            ]
            best_time.sort(key=lambda x: (x["horse_id"], x["baba_code"], x["surface"], x["distance_m"]))

        last5_rows = (
            self.db.query(SpecEntryLast5Race)
            .filter(SpecEntryLast5Race.race_id == race.race_id)
            .order_by(SpecEntryLast5Race.horse_no.asc(), SpecEntryLast5Race.order_in_last5.asc())
            .all()
        )
        last5 = [
            {
                "race_id": r.race_id,
                "horse_no": int(r.horse_no),
                "order_in_last5": int(r.order_in_last5),
                "finish_pos": r.finish_pos,
                "past_race_date": r.past_race_date,
                "track_condition": r.track_condition,
                "runners": r.runners,
                "place": r.place,
                "direction": r.direction,
                "distance_m": r.distance_m,
                "horse_no_in_race": r.horse_no_in_race,
                "popularity": r.popularity,
                "body_weight": r.body_weight,
                "jockey_name": r.jockey_name,
                "burden_weight": float(r.burden_weight) if r.burden_weight is not None else None,
                "time_raw": r.time_raw,
                "time_sec": float(r.time_sec) if r.time_sec is not None else None,
                "passing_order_raw": r.passing_order_raw,
                "passing_order_arr": r.passing_order_arr,
                "last3f": float(r.last3f) if r.last3f is not None else None,
                "time_diff": float(r.time_diff) if r.time_diff is not None else None,
                "winner_name": r.winner_name,
            }
            for r in last5_rows
        ]

        return {
            "race": {
                "race_id": race.race_id,
                "race_date": race.race_date,
                "baba_code": int(race.baba_code),
                "race_no": int(race.race_no),
                "post_time": race.post_time,
                "race_name": race.race_name,
                "surface": race.surface,
                "distance_m": race.distance_m,
                "direction": race.direction,
                "weather": race.weather,
                "track_condition": race.track_condition,
            },
            "persons": persons,
            "horses": horses,
            "race_entries": [
                {
                    "race_id": e.race_id,
                    "horse_no": int(e.horse_no),
                    "waku": e.waku,
                    "horse_id": e.horse_id,
                    "burden_weight_display": float(e.burden_weight_display),
                    "apprentice_allowance_symbol": e.apprentice_allowance_symbol,
                    "apprentice_allowance_kg": e.apprentice_allowance_kg,
                    "burden_weight_base": float(e.burden_weight_base) if e.burden_weight_base is not None else None,
                    "body_weight": e.body_weight,
                    "body_weight_diff": e.body_weight_diff,
                    "win_odds": float(e.win_odds) if e.win_odds is not None else None,
                    "popularity": e.popularity,
                    "jockey_person_id": e.jockey_person_id,
                    "trainer_person_id": e.trainer_person_id,
                    "owner_person_id": e.owner_person_id,
                    "perf_total_id": e.perf_total_id,
                    "perf_dirt_left_id": e.perf_dirt_left_id,
                    "perf_dirt_right_id": e.perf_dirt_right_id,
                    "perf_track_id": e.perf_track_id,
                    "perf_distance_id": e.perf_distance_id,
                    "best_time_id": e.best_time_id,
                }
                for e in entries
            ],
            "perf_total": perf_total,
            "perf_dirt_left": perf_dirt_left,
            "perf_dirt_right": perf_dirt_right,
            "perf_track": perf_track,
            "perf_distance": perf_distance,
            "best_time": best_time,
            "last5": last5,
        }

    def _perf_rows(self, model, horse_ids: set[int], *, id_field: str) -> list[dict]:
        if not horse_ids:
            return []
        rows = self.db.query(model).filter(model.horse_id.in_(horse_ids)).all()
        out = []
        for r in rows:
            starts = int(r.first_cnt) + int(r.second_cnt) + int(r.third_cnt) + int(r.out_cnt)
            out.append(
                {
                    "horse_id": int(r.horse_id),
                    "first_cnt": int(r.first_cnt),
                    "second_cnt": int(r.second_cnt),
                    "third_cnt": int(r.third_cnt),
                    "out_cnt": int(r.out_cnt),
                    "starts": starts,
                }
            )
        out.sort(key=lambda x: x["horse_id"])
        return out




