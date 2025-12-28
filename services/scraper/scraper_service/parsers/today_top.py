from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup


def parse_today_race_info_top(html: bytes) -> list[int]:
    """Return list of baba_code (venue codes) for the given day.

    Implementation: find all links that contain k_babaCode in query params.
    """
    soup = BeautifulSoup(html, "lxml")
    codes: set[int] = set()
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        if "k_babaCode" not in href:
            continue
        q = parse_qs(urlparse(href).query)
        if "k_babaCode" in q and q["k_babaCode"]:
            try:
                codes.add(int(q["k_babaCode"][0]))
            except ValueError:
                continue
    return sorted(codes)
