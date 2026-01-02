from __future__ import annotations

from typing import Optional

from scraper_service.keiba import constants as C

ODDS_PAGES = {
    C.PAGE_ODDS_TANFUKU,
    C.PAGE_ODDS_WAKU,
    C.PAGE_ODDS_UMAREN,
    C.PAGE_ODDS_UMATAN,
    C.PAGE_ODDS_WIDE,
    C.PAGE_ODDS_3LENFUKU,
    C.PAGE_ODDS_3LENTAN,
}

VENUE_PAGES = {
    C.PAGE_RACE_LIST,
    C.PAGE_REFUND_MONEY_LIST,
}

RACE_PAGES = {
    C.PAGE_DEBA_TABLE,
    C.PAGE_RACE_MARK_TABLE,
} | ODDS_PAGES


def build_scope_key(*, page_type: str, race_date: Optional[str], baba_code: Optional[int], race_no: Optional[int]) -> str:
    if not race_date:
        raise ValueError("race_date is required for scope key")

    if page_type in VENUE_PAGES:
        if baba_code is None:
            raise ValueError("baba_code is required for venue scope")
        return f"{race_date}:{baba_code}"
    if page_type in RACE_PAGES:
        if baba_code is None or race_no is None:
            raise ValueError("baba_code and race_no are required for race scope")
        return f"{race_date}:{baba_code}:{race_no}"

    raise ValueError(f"unsupported page_type: {page_type}")


def build_diff_key(
    *,
    page_type: str,
    race_date: Optional[str],
    baba_code: Optional[int],
    race_no: Optional[int],
    snapshot_kind: Optional[str] = None,
    odds_flg: Optional[int] = None,
) -> tuple[str, str, Optional[str], Optional[int]]:
    scope_key = build_scope_key(page_type=page_type, race_date=race_date, baba_code=baba_code, race_no=race_no)
    return (scope_key, page_type, snapshot_kind, odds_flg)


def should_sync_by_fingerprint(prev_fingerprint: Optional[str], current_fingerprint: Optional[str]) -> bool:
    if not current_fingerprint:
        return True
    return current_fingerprint != prev_fingerprint
