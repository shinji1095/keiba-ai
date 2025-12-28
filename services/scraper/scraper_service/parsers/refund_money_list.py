from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from bs4 import BeautifulSoup

from scraper_service.keiba.models import PayoutUpsert, RaceKey
from scraper_service.parsers.common import extract_ints, normalize_space


_LABEL_TO_BET_TYPE: list[tuple[str, str]] = [
    ("単勝", "tansho"),
    ("複勝", "fukusho"),
    ("枠連複", "wakuren"),
    ("枠連単", "wakutan"),
    ("馬連単", "umatan"),
    ("馬単", "umatan"),
    ("馬連複", "umaren"),
    ("馬連", "umaren"),
    ("ワイド", "wide"),
    ("三連複", "sanrenpuku"),
    ("三連単", "sanrentan"),
]


def _label_to_bet_type(label: str) -> Optional[str]:
    for k, v in _LABEL_TO_BET_TYPE:
        if k in label:
            return v
    return None


def _is_ordered(bet_type: str) -> bool:
    return bet_type in {"wakutan", "umatan", "sanrentan"}


def _legs_len(bet_type: str) -> int:
    return 1 if bet_type in {"tansho", "fukusho"} else (2 if bet_type in {"wakuren", "wakutan", "umaren", "umatan", "wide"} else 3)


def _parse_yen(s: str) -> Optional[int]:
    raw = normalize_space(s)
    if raw in {"", "-", "—", "―"}:
        return None
    m = re.search(r"(\d[\d,]*)\s*円", raw)
    if not m:
        # fallback: just digits
        digits = re.sub(r"[^0-9]", "", raw)
        return int(digits) if digits else None
    return int(m.group(1).replace(",", ""))


def _parse_popularity(s: str) -> Optional[int]:
    raw = normalize_space(s)
    m = re.search(r"(\d+)\s*人気", raw)
    if m:
        return int(m.group(1))
    # sometimes the cell is just an integer
    ints = extract_ints(raw)
    return ints[0] if ints else None


_RACE_NO_PAT = re.compile(r"(?:第)?\s*(\d+)\s*(?:競走|R)", re.IGNORECASE)


def _find_race_no(text: str) -> Optional[int]:
    m = _RACE_NO_PAT.search(text)
    return int(m.group(1)) if m else None


def parse_refund_money_list(html: bytes, *, race_date: str, baba_code: int, captured_at_iso: Optional[str] = None) -> list[PayoutUpsert]:
    """Parse RefundMoneyList HTML (date x baba_code) into payout upserts.

    This parser is implemented as a best-effort text/table parser.
    The main known tricky part is:
    - fukusho and wide can have continuation rows without bet type label.
    """
    soup = BeautifulSoup(html, "lxml")
    captured_at = captured_at_iso or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    payouts: list[PayoutUpsert] = []
    current_race_no: Optional[int] = None
    current_bet_type: Optional[str] = None

    # iterate through elements in document order and detect race sections
    for el in soup.find_all(["h1", "h2", "h3", "h4", "table", "tr"]):
        if el.name in {"h1", "h2", "h3", "h4"}:
            rn = _find_race_no(el.get_text(" ", strip=True))
            if rn is not None:
                current_race_no = rn
                current_bet_type = None
            continue

        if el.name == "tr":
            if current_race_no is None:
                # sometimes race_no can be found inside row itself
                rn = _find_race_no(el.get_text(" ", strip=True))
                if rn is not None:
                    current_race_no = rn
                    current_bet_type = None
                    continue

            tds = el.find_all(["td", "th"])
            if len(tds) < 3:
                continue

            # heuristic columns:
            # [0]=bet_type label or empty, [1]=komban, [2]=yen, [3]=popularity? (optional)
            label = normalize_space(tds[0].get_text(" ", strip=True))
            komban = normalize_space(tds[1].get_text(" ", strip=True))
            yen = normalize_space(tds[2].get_text(" ", strip=True))
            pop = normalize_space(tds[3].get_text(" ", strip=True)) if len(tds) >= 4 else ""

            bt = _label_to_bet_type(label) if label else None
            if bt is not None:
                current_bet_type = bt
            if current_bet_type is None or current_race_no is None:
                continue

            legs = extract_ints(komban)
            need = _legs_len(current_bet_type)
            if len(legs) < need:
                continue
            legs = legs[:need]

            payouts.append(
                PayoutUpsert(
                    race_key=RaceKey(race_date=race_date, baba_code=baba_code, race_no=current_race_no),
                    bet_type=current_bet_type,  # type: ignore[arg-type]
                    legs=legs,
                    is_ordered=_is_ordered(current_bet_type),
                    payout_yen=_parse_yen(yen),
                    popularity=_parse_popularity(pop),
                )
            )

    return payouts
