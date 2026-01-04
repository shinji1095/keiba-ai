from __future__ import annotations

from app.db.models.oauth_client import OAuthClient
from app.db.models.odds import OddsItem, OddsSnapshot
from app.db.models.payout import Payout
from app.db.models.race import Race
from app.db.models.race_change import RaceChange
from app.db.models.race_entry import RaceEntry
from app.db.models.race_result import RaceResult
from app.db.models.user import User
from app.db.models.venue import Venue
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

__all__ = [
    "User",
    "OAuthClient",
    "Venue",
    "Race",
    "RaceEntry",
    "OddsSnapshot",
    "OddsItem",
    "RaceResult",
    "Payout",
    "RaceChange",
    # spec-aligned schema (normalized)
    "SpecRacecourse",
    "SpecRaceDay",
    "SpecRace",
    "SpecPerson",
    "SpecHorse",
    "SpecPerfTotal",
    "SpecPerfDirtLeft",
    "SpecPerfDirtRight",
    "SpecPerfTrack",
    "SpecPerfDistance",
    "SpecBestTime",
    "SpecRaceEntry",
    "SpecEntryLast5Race",
]
