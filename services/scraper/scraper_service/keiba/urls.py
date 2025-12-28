from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional
from urllib.parse import urlencode

Device = Literal["pc", "sp"]


PC_BASE = "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/"
SP_BASE = "https://sp.keiba.go.jp/KeibaWebSP/TodayRaceInfo/"


@dataclass(frozen=True)
class RaceKey:
    race_date: str  # YYYY-MM-DD (JST)
    baba_code: int
    race_no: int


def race_date_to_k_raceDate(race_date: str) -> str:
    """Convert YYYY-MM-DD to YYYY/MM/DD.

    NOTE:
      URL encoding ("/" -> "%2F") must be performed exactly once.
      This function returns a plain string, and build_url() applies urlencode().
    """
    y, m, d = race_date.split("-")
    return f"{y}/{int(m):02d}/{int(d):02d}"


def build_url(page_name: str, *, device: Device, race_date: Optional[str] = None, baba_code: Optional[int] = None, race_no: Optional[int] = None, odds_flg: Optional[int] = None) -> str:
    base = PC_BASE if device == "pc" else SP_BASE
    params: dict[str, str] = {}

    if race_date is not None:
        params["k_raceDate"] = race_date_to_k_raceDate(race_date)
    if baba_code is not None:
        params["k_babaCode"] = str(baba_code)
    if race_no is not None:
        params["k_raceNo"] = str(race_no)
    if odds_flg is not None:
        params["odds_flg"] = str(odds_flg)

    if params:
        return base + page_name + "?" + urlencode(params)
    return base + page_name


# Known odds_flg mappings (confirmed in docs)
ODDS_FLG_FIXED: dict[str, list[int]] = {
    # OddsTanFuku: 4=horse order, 5=popularity order
    "OddsTanFuku": [4, 5],
    # OddsWakuLenFukuTan: 6=waku matrix, 5=popularity ranking
    "OddsWakuLenFukuTan": [6, 5],
}
