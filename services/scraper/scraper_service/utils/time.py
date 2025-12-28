from __future__ import annotations

from datetime import datetime, time, timezone, timedelta


JST = timezone(timedelta(hours=9))


def iso_now_jst() -> str:
    return datetime.now(timezone.utc).astimezone(JST).isoformat(timespec="seconds")


def today_jst_str() -> str:
    return datetime.now(timezone.utc).astimezone(JST).date().isoformat()


def combine_date_time_jst(race_date: str, hhmmss: str) -> datetime:
    y, m, d = [int(x) for x in race_date.split("-")]
    hh, mm, ss = [int(x) for x in hhmmss.split(":")]
    return datetime(y, m, d, hh, mm, ss, tzinfo=JST)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(JST).isoformat(timespec="seconds")


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s)
