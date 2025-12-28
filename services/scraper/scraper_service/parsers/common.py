from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup


def soup_from_html(content: bytes) -> BeautifulSoup:
    # lxml is installed as parser
    return BeautifulSoup(content, "lxml")


def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def extract_ints(s: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", s)]


_ODDS_RANGE_SEP = re.compile(r"\s*[-–〜～]\s*")


def parse_odds_range(s: str) -> tuple[Optional[float], Optional[float]]:
    """Parse odds string into (min,max) according to the contract.

    Rules (from docs):
    - single value => min=max=float(value)
    - range value (wide/fukusho, etc.) => split by -/–/〜/～ (spaces tolerated)
    - missing markers like '-', '—', '', '発売なし' => (None, None)
    """
    raw = normalize_space(s)
    if raw in {"", "-", "—", "―"}:
        return None, None
    if "発売なし" in raw:
        return None, None

    # normalize full-width dot etc. (best effort)
    raw = raw.replace("．", ".")
    parts = _ODDS_RANGE_SEP.split(raw)
    if len(parts) == 1:
        try:
            v = float(parts[0])
            return v, v
        except ValueError:
            return None, None
    if len(parts) >= 2:
        try:
            a = float(parts[0])
            b = float(parts[1])
            lo, hi = (a, b) if a <= b else (b, a)
            return lo, hi
        except ValueError:
            return None, None
    return None, None
