from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.odds import OddsItem as OddsItemModel
from app.db.models.odds import OddsSnapshot as OddsSnapshotModel
from app.db.models.payout import Payout as PayoutModel
from app.db.models.race import Race as RaceModel
from app.db.models.race_entry import RaceEntry as RaceEntryModel
from app.db.models.race_result import RaceResult as RaceResultModel
from app.db.models.venue import Venue as VenueModel
from app.schemas.odds import (
    BetType,
    OddsItem,
    OddsSnapshot,
    OddsSnapshotQueryResponse,
    SnapshotKind,
)
from app.schemas.payout import Payout, PayoutListResponse
from app.schemas.race import (
    Race,
    RaceEntry,
    RaceEntryListResponse,
    RaceEntryWithRace,
    RaceEntryWithRaceListResponse,
    RaceEntryResultWithRace,
    RaceEntryResultWithRaceListResponse,
    RaceKey,
    RaceListResponse,
    RaceResult,
    RaceResultListResponse,
    RaceSummary,
)
from app.schemas.venue import Venue, VenueListResponse


class RaceService:
    def __init__(self, db: Session):
        self.db = db

    def list_venues(self) -> VenueListResponse:
        items = (
            self.db.query(VenueModel)
            .order_by(VenueModel.baba_code.asc())
            .all()
        )
        return VenueListResponse(
            items=[
                Venue(baba_code=v.baba_code, venue_name=v.venue_name)
                for v in items
            ]
        )

    def list_races(
        self,
        *,
        race_date: dt.date,
        baba_code: Optional[int],
        page: int,
        page_size: int,
    ) -> RaceListResponse:
        q = self.db.query(RaceModel).filter(RaceModel.race_date == race_date)
        if baba_code is not None:
            q = q.filter(RaceModel.baba_code == baba_code)

        q = q.order_by(RaceModel.baba_code.asc(), RaceModel.race_no.asc())
        rows = q.offset((page - 1) * page_size).limit(page_size).all()

        items: list[RaceSummary] = []
        for r in rows:
            rk = RaceKey(
                race_date=r.race_date, baba_code=r.baba_code, race_no=r.race_no
            )
            items.append(
                RaceSummary(
                    race_id=r.race_id,
                    race_key=rk,
                    start_time=r.start_time,
                    race_name=r.race_name,
                    status=r.status,
                )
            )
        return RaceListResponse(items=items, page=page, page_size=page_size)

    def get_race(self, race_id: int) -> Race:
        r = (
            self.db.query(RaceModel)
            .filter(RaceModel.race_id == race_id)
            .one_or_none()
        )
        if r is None:
            raise AppError.not_found("race not found")
        rk = RaceKey(
            race_date=r.race_date, baba_code=r.baba_code, race_no=r.race_no
        )
        return Race(
            race_id=r.race_id,
            race_key=rk,
            start_time=r.start_time,
            distance_m=r.distance_m,
            course=r.course,
            weather=r.weather,
            track_condition=r.track_condition,
            race_name=r.race_name,
            field_size=r.field_size,
            status=r.status,
        )

    def get_entries(self, race_id: int) -> RaceEntryListResponse:
        exists = (
            self.db.query(RaceModel)
            .filter(RaceModel.race_id == race_id)
            .count()
            > 0
        )
        if not exists:
            raise AppError.not_found("race not found")
        rows = (
            self.db.query(RaceEntryModel)
            .filter(RaceEntryModel.race_id == race_id)
            .order_by(RaceEntryModel.horse_number.asc())
            .all()
        )
        return RaceEntryListResponse(
            items=[
                RaceEntry(
                    race_entry_id=e.race_entry_id,
                    race_id=e.race_id,
                    horse_id=e.horse_id,
                    post_position=e.post_position,
                    horse_number=e.horse_number,
                    horse_name=e.horse_name,
                    jockey_name=e.jockey_name,
                    trainer_name=e.trainer_name,
                    handicap_kg=e.handicap_kg,
                    body_weight=e.body_weight,
                    body_weight_diff=e.body_weight_diff,
                )
                for e in rows
            ]
        )

    def list_race_entries(
        self,
        *,
        race_date: dt.date,
        baba_code: Optional[int],
        page: int,
        page_size: int,
    ) -> RaceEntryWithRaceListResponse:
        q = (
            self.db.query(RaceEntryModel, RaceModel)
            .join(RaceModel, RaceEntryModel.race_id == RaceModel.race_id)
            .filter(RaceModel.race_date == race_date)
        )
        if baba_code is not None:
            q = q.filter(RaceModel.baba_code == baba_code)

        q = q.order_by(
            RaceModel.baba_code.asc(),
            RaceModel.race_no.asc(),
            RaceEntryModel.horse_number.asc(),
        )
        rows = q.offset((page - 1) * page_size).limit(page_size).all()

        items: list[RaceEntryWithRace] = []
        for e, r in rows:
            rk = RaceKey(
                race_date=r.race_date, baba_code=r.baba_code, race_no=r.race_no
            )
            items.append(
                RaceEntryWithRace(
                    race_entry_id=e.race_entry_id,
                    race_id=e.race_id,
                    race_key=rk,
                    start_time=r.start_time,
                    race_name=r.race_name,
                    status=r.status,
                    horse_id=e.horse_id,
                    post_position=e.post_position,
                    horse_number=e.horse_number,
                    horse_name=e.horse_name,
                    jockey_name=e.jockey_name,
                    trainer_name=e.trainer_name,
                    handicap_kg=e.handicap_kg,
                    body_weight=e.body_weight,
                    body_weight_diff=e.body_weight_diff,
                )
            )
        return RaceEntryWithRaceListResponse(items=items, page=page, page_size=page_size)

    def list_race_entry_results(
        self,
        *,
        race_date: dt.date,
        baba_code: Optional[int],
        page: int,
        page_size: int,
    ) -> RaceEntryResultWithRaceListResponse:
        q = (
            self.db.query(RaceEntryModel, RaceModel, RaceResultModel)
            .join(RaceModel, RaceEntryModel.race_id == RaceModel.race_id)
            .outerjoin(
                RaceResultModel,
                and_(
                    RaceResultModel.race_id == RaceEntryModel.race_id,
                    RaceResultModel.horse_number == RaceEntryModel.horse_number,
                ),
            )
            .filter(RaceModel.race_date == race_date)
        )
        if baba_code is not None:
            q = q.filter(RaceModel.baba_code == baba_code)

        q = q.order_by(
            RaceModel.baba_code.asc(),
            RaceModel.race_no.asc(),
            RaceEntryModel.horse_number.asc(),
        )
        rows = q.offset((page - 1) * page_size).limit(page_size).all()

        items: list[RaceEntryResultWithRace] = []
        for e, r, res in rows:
            rk = RaceKey(
                race_date=r.race_date, baba_code=r.baba_code, race_no=r.race_no
            )
            items.append(
                RaceEntryResultWithRace(
                    race_entry_id=e.race_entry_id,
                    race_id=e.race_id,
                    race_key=rk,
                    start_time=r.start_time,
                    race_name=r.race_name,
                    status=r.status,
                    horse_id=e.horse_id,
                    post_position=e.post_position,
                    horse_number=e.horse_number,
                    horse_name=e.horse_name,
                    jockey_name=e.jockey_name,
                    trainer_name=e.trainer_name,
                    handicap_kg=e.handicap_kg,
                    body_weight=e.body_weight,
                    body_weight_diff=e.body_weight_diff,
                    race_result_id=res.race_result_id if res else None,
                    finish_position=res.finish_position if res else None,
                    time_str=res.time_str if res else None,
                    margin=res.margin if res else None,
                    last3f=res.last3f if res else None,
                    popularity=res.popularity if res else None,
                    corner1=res.corner1 if res else None,
                    corner2=res.corner2 if res else None,
                    corner3=res.corner3 if res else None,
                    corner4=res.corner4 if res else None,
                )
            )
        return RaceEntryResultWithRaceListResponse(items=items, page=page, page_size=page_size)

    def get_odds(
        self,
        *,
        race_id: int,
        snapshot_kind: SnapshotKind,
        bet_type: BetType,
        odds_flg: int | None,
    ) -> OddsSnapshotQueryResponse:
        exists = (
            self.db.query(RaceModel)
            .filter(RaceModel.race_id == race_id)
            .count()
            > 0
        )
        if not exists:
            raise AppError.not_found("race not found")

        q = self.db.query(OddsSnapshotModel).filter(
            OddsSnapshotModel.race_id == race_id,
            OddsSnapshotModel.snapshot_kind == snapshot_kind,
            OddsSnapshotModel.bet_type == bet_type.value,
        )
        if odds_flg is not None:
            q = q.filter(OddsSnapshotModel.odds_flg == odds_flg)

        snap = q.order_by(desc(OddsSnapshotModel.captured_at)).first()
        if snap is None:
            raise AppError.not_found("odds snapshot not found")

        items = (
            self.db.query(OddsItemModel)
            .filter(OddsItemModel.odds_snapshot_id == snap.odds_snapshot_id)
            .order_by(OddsItemModel.odds_item_id.asc())
            .all()
        )

        snap_schema = OddsSnapshot(
            odds_snapshot_id=snap.odds_snapshot_id,
            race_id=snap.race_id,
            bet_type=BetType(snap.bet_type),
            snapshot_kind=snap.snapshot_kind,
            captured_at=snap.captured_at,
            source_url=snap.source_url,
            odds_flg=snap.odds_flg,
            is_final=bool(snap.is_final),
        )
        item_schemas = [
            OddsItem(
                odds_item_id=i.odds_item_id,
                odds_snapshot_id=i.odds_snapshot_id,
                legs=list(i.legs or []),
                is_ordered=bool(i.is_ordered),
                odds_min=i.odds_min,
                odds_max=i.odds_max,
                popularity=i.popularity,
                raw_text=i.raw_text,
            )
            for i in items
        ]
        return OddsSnapshotQueryResponse(
            snapshot=snap_schema, items=item_schemas
        )

    def get_results(self, race_id: int) -> RaceResultListResponse:
        exists = (
            self.db.query(RaceModel)
            .filter(RaceModel.race_id == race_id)
            .count()
            > 0
        )
        if not exists:
            raise AppError.not_found("race not found")
        rows = (
            self.db.query(RaceResultModel)
            .filter(RaceResultModel.race_id == race_id)
            .order_by(RaceResultModel.finish_position.asc())
            .all()
        )
        return RaceResultListResponse(
            items=[
                RaceResult(
                    race_result_id=r.race_result_id,
                    race_id=r.race_id,
                    finish_position=r.finish_position,
                    horse_number=r.horse_number,
                    time_str=r.time_str,
                    margin=r.margin,
                    last3f=r.last3f,
                    popularity=r.popularity,
                    corner1=r.corner1,
                    corner2=r.corner2,
                    corner3=r.corner3,
                    corner4=r.corner4,
                )
                for r in rows
            ]
        )

    def get_payouts(self, race_id: int) -> PayoutListResponse:
        exists = (
            self.db.query(RaceModel)
            .filter(RaceModel.race_id == race_id)
            .count()
            > 0
        )
        if not exists:
            raise AppError.not_found("race not found")
        rows = (
            self.db.query(PayoutModel)
            .filter(PayoutModel.race_id == race_id)
            .order_by(PayoutModel.payout_id.asc())
            .all()
        )
        return PayoutListResponse(
            items=[
                Payout(
                    payout_id=p.payout_id,
                    race_id=p.race_id,
                    bet_type=BetType(p.bet_type),
                    legs=list(p.legs or []),
                    is_ordered=bool(p.is_ordered),
                    payout_yen=p.payout_yen,
                    popularity=p.popularity,
                )
                for p in rows
            ]
        )
