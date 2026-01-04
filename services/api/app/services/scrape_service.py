from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.models.odds import OddsItem as OddsItemModel
from app.db.models.odds import OddsSnapshot as OddsSnapshotModel
from app.db.models.payout import Payout as PayoutModel
from app.db.models.race import Race as RaceModel
from app.db.models.race_change import RaceChange as RaceChangeModel
from app.db.models.race_entry import RaceEntry as RaceEntryModel
from app.db.models.race_result import RaceResult as RaceResultModel
from app.db.models.venue import Venue as VenueModel
from app.schemas.scrape import (
    BatchUpsertResponse,
    OddsSnapshotUpsertRequest,
    OddsSnapshotUpsertResponse,
    PayoutUpsertBatchRequest,
    RaceChangeInsertBatchRequest,
    RaceEntryUpsertBatchRequest,
    RaceResultUpsertBatchRequest,
    RaceUpsertBatchRequest,
)


class ScrapeService:
    def __init__(self, db: Session):
        self.db = db

    def _ensure_venue(self, baba_code: int) -> None:
        v = (
            self.db.query(VenueModel)
            .filter(VenueModel.baba_code == baba_code)
            .one_or_none()
        )
        if v is None:
            self.db.add(
                VenueModel(baba_code=baba_code, venue_name=f"baba_{baba_code}")
            )

    def _get_or_create_race(self, race_key) -> RaceModel:
        self._ensure_venue(race_key.baba_code)
        r = (
            self.db.query(RaceModel)
            .filter(
                RaceModel.race_date == race_key.race_date,
                RaceModel.baba_code == race_key.baba_code,
                RaceModel.race_no == race_key.race_no,
            )
            .one_or_none()
        )
        if r is None:
            r = RaceModel(
                race_date=race_key.race_date,
                baba_code=race_key.baba_code,
                race_no=race_key.race_no,
            )
            self.db.add(r)
            self.db.flush()
        return r

    def upsert_races(
        self, payload: RaceUpsertBatchRequest
    ) -> BatchUpsertResponse:
        accepted = len(payload.items)
        upserted = 0
        warnings: list[str] = []

        for item in payload.items:
            r = self._get_or_create_race(item.race_key)
            changed = False
            for attr in [
                "start_time",
                "distance_m",
                "course",
                "weather",
                "track_condition",
                "race_name",
                "field_size",
                "status",
            ]:
                val = getattr(item, attr)
                if val is not None:
                    setattr(r, attr, val)
                    changed = True
            if changed:
                upserted += 1

        self.db.commit()
        return BatchUpsertResponse(
            accepted=accepted, upserted=upserted, warnings=warnings or None
        )

    def upsert_entries(
        self, payload: RaceEntryUpsertBatchRequest
    ) -> BatchUpsertResponse:
        accepted = len(payload.items)
        upserted = 0
        warnings: list[str] = []

        for item in payload.items:
            r = self._get_or_create_race(item.race_key)
            e = (
                self.db.query(RaceEntryModel)
                .filter(
                    RaceEntryModel.race_id == r.race_id,
                    RaceEntryModel.horse_number == item.horse_number,
                )
                .one_or_none()
            )
            if e is None:
                e = RaceEntryModel(
                    race_id=r.race_id,
                    horse_id=item.horse_id,
                    post_position=item.post_position,
                    horse_number=item.horse_number,
                    horse_name=item.horse_name,
                    jockey_name=item.jockey_name,
                    trainer_name=item.trainer_name,
                    handicap_kg=item.handicap_kg,
                    body_weight=item.body_weight,
                    body_weight_diff=item.body_weight_diff,
                )
                self.db.add(e)
                upserted += 1
            else:
                for attr in [
                    "horse_id",
                    "post_position",
                    "horse_name",
                    "jockey_name",
                    "trainer_name",
                    "handicap_kg",
                    "body_weight",
                    "body_weight_diff",
                ]:
                    val = getattr(item, attr)
                    if val is not None:
                        setattr(e, attr, val)
                upserted += 1

        self.db.commit()
        return BatchUpsertResponse(
            accepted=accepted, upserted=upserted, warnings=warnings or None
        )

    def upsert_odds_snapshot(
        self, payload: OddsSnapshotUpsertRequest
    ) -> OddsSnapshotUpsertResponse:
        r = self._get_or_create_race(payload.race_key)

        # Contract:
        # - UNIQUE: (race_id, bet_type, snapshot_kind, odds_flg)
        # - captured_at は「取得時刻」であり、キーではない（最新を上書きする）
        snaps = (
            self.db.query(OddsSnapshotModel)
            .filter(
                OddsSnapshotModel.race_id == r.race_id,
                OddsSnapshotModel.bet_type == payload.bet_type.value,
                OddsSnapshotModel.snapshot_kind == payload.snapshot_kind,
                OddsSnapshotModel.odds_flg == payload.odds_flg,
            )
            .order_by(desc(OddsSnapshotModel.captured_at))
            .all()
        )

        if not snaps:
            snap = OddsSnapshotModel(
                race_id=r.race_id,
                bet_type=payload.bet_type.value,
                snapshot_kind=payload.snapshot_kind,
                captured_at=payload.captured_at,
                source_url=payload.source_url,
                odds_flg=payload.odds_flg,
                is_final=payload.is_final,
            )
            self.db.add(snap)
            self.db.flush()
        else:
            # 古いスキーマ（captured_at を一意キーに含めていた）からの移行で重複が残る場合に備え、
            # 最新1件に集約して残りは削除する。
            snap = snaps[0]
            for old in snaps[1:]:
                self.db.query(OddsItemModel).filter(
                    OddsItemModel.odds_snapshot_id == old.odds_snapshot_id
                ).delete()
                self.db.delete(old)

            snap.captured_at = payload.captured_at
            snap.source_url = payload.source_url
            snap.is_final = payload.is_final

            # Replace items
            self.db.query(OddsItemModel).filter(
                OddsItemModel.odds_snapshot_id == snap.odds_snapshot_id
            ).delete()

        for it in payload.items:
            self.db.add(
                OddsItemModel(
                    odds_snapshot_id=snap.odds_snapshot_id,
                    legs=list(it.legs),
                    is_ordered=it.is_ordered,
                    odds_min=it.odds_min,
                    odds_max=it.odds_max,
                    popularity=it.popularity,
                    raw_text=it.raw_text,
                )
            )

        self.db.commit()
        return OddsSnapshotUpsertResponse(
            race_id=r.race_id,
            bet_type=payload.bet_type,
            snapshot_kind=payload.snapshot_kind,
            odds_snapshot_id=snap.odds_snapshot_id,
            num_items=len(payload.items),
        )

    def upsert_results(
        self, payload: RaceResultUpsertBatchRequest
    ) -> BatchUpsertResponse:
        accepted = len(payload.items)
        upserted = 0
        warnings: list[str] = []

        # NOTE:
        # race_results has UNIQUE constraints on both:
        # - (race_id, finish_position)
        # - (race_id, horse_number)
        #
        # In real-world scraping, upstream may temporarily emit duplicates (e.g. parser heuristic mismatches).
        # To keep sync idempotent and avoid hard failures, we:
        # - deduplicate within the batch (prefer rows with richer fields)
        # - then treat the batch as authoritative and replace all results for the race.
        if payload.items:
            r = self._get_or_create_race(payload.items[0].race_key)

            def score(x: RaceResultUpsert) -> int:
                return sum(
                    1
                    for v in [
                        x.time_str,
                        x.margin,
                        x.last3f,
                        x.popularity,
                        x.corner1,
                        x.corner2,
                        x.corner3,
                        x.corner4,
                    ]
                    if v is not None
                )

            # best row per horse_number (ignore None)
            best_by_horse: dict[int, RaceResultUpsert] = {}
            for it in payload.items:
                if it.horse_number is None:
                    continue
                cur = best_by_horse.get(it.horse_number)
                if cur is None:
                    best_by_horse[it.horse_number] = it
                    continue
                s_it = score(it)
                s_cur = score(cur)
                if s_it > s_cur or (s_it == s_cur and it.finish_position < cur.finish_position):
                    best_by_horse[it.horse_number] = it

            filtered: list[RaceResultUpsert] = []
            seen_fp: set[int] = set()
            seen_hn: set[int] = set()

            for it in sorted(payload.items, key=lambda x: x.finish_position):
                if it.horse_number is not None:
                    best = best_by_horse.get(it.horse_number)
                    if best is not it:
                        warnings.append(
                            f"duplicate horse_number in results: horse_no={it.horse_number} finish_position={it.finish_position} (dropped)"
                        )
                        continue
                    if it.horse_number in seen_hn:
                        warnings.append(
                            f"duplicate horse_number in results after filtering: horse_no={it.horse_number} (dropped)"
                        )
                        continue
                    seen_hn.add(it.horse_number)

                if it.finish_position in seen_fp:
                    warnings.append(
                        f"duplicate finish_position in results: finish_position={it.finish_position} (dropped)"
                    )
                    continue
                seen_fp.add(it.finish_position)
                filtered.append(it)

            # Replace all rows for this race_id, then insert fresh.
            self.db.query(RaceResultModel).filter(RaceResultModel.race_id == r.race_id).delete()
            for item in filtered:
                self.db.add(
                    RaceResultModel(
                        race_id=r.race_id,
                        finish_position=item.finish_position,
                        horse_number=item.horse_number,
                        time_str=item.time_str,
                        margin=item.margin,
                        last3f=item.last3f,
                        popularity=item.popularity,
                        corner1=item.corner1,
                        corner2=item.corner2,
                        corner3=item.corner3,
                        corner4=item.corner4,
                    )
                )
            upserted = len(filtered)

        self.db.commit()
        return BatchUpsertResponse(
            accepted=accepted, upserted=upserted, warnings=warnings or None
        )

    def upsert_payouts(
        self, payload: PayoutUpsertBatchRequest
    ) -> BatchUpsertResponse:
        accepted = len(payload.items)
        upserted = 0
        warnings: list[str] = []

        for item in payload.items:
            r = self._get_or_create_race(item.race_key)
            q = self.db.query(PayoutModel).filter(
                PayoutModel.race_id == r.race_id,
                PayoutModel.bet_type == item.bet_type.value,
                PayoutModel.is_ordered == bool(item.is_ordered),
            )
            # Legs match: approximate via JSON comparison (works for sqlite/json as text in most cases)
            existing = None
            for cand in q.all():
                if list(cand.legs or []) == list(item.legs):
                    existing = cand
                    break

            if existing is None:
                self.db.add(
                    PayoutModel(
                        race_id=r.race_id,
                        bet_type=item.bet_type.value,
                        legs=list(item.legs),
                        is_ordered=bool(item.is_ordered),
                        payout_yen=item.payout_yen,
                        popularity=item.popularity,
                    )
                )
            else:
                if item.payout_yen is not None:
                    existing.payout_yen = item.payout_yen
                if item.popularity is not None:
                    existing.popularity = item.popularity
            upserted += 1

        self.db.commit()
        return BatchUpsertResponse(
            accepted=accepted, upserted=upserted, warnings=warnings or None
        )

    def insert_race_changes(
        self, payload: RaceChangeInsertBatchRequest
    ) -> BatchUpsertResponse:
        accepted = len(payload.items)
        upserted = 0

        for item in payload.items:
            r = self._get_or_create_race(item.race_key)
            self.db.add(
                RaceChangeModel(
                    race_id=r.race_id,
                    change_type=item.change_type,
                    payload=item.payload,
                    captured_at=item.captured_at,
                )
            )
            upserted += 1

        self.db.commit()
        return BatchUpsertResponse(
            accepted=accepted, upserted=upserted, warnings=None
        )
