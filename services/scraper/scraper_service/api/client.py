from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import requests

from scraper_service.keiba.models import (
    OddsSnapshotUpsertRequest,
    PayoutUpsert,
    RaceChangeInsert,
    RaceEntryUpsert,
    RaceResultUpsert,
    RaceUpsert,
    RawFetchLogInsert,
)


@dataclass
class Token:
    access_token: str
    token_type: str
    expires_in: int
    issued_at: Optional[str] = None


class ApiClient:
    def __init__(self, *, base_url: str, access_token: Optional[str], username: Optional[str], password: Optional[str]) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._token: Optional[Token] = None

        if access_token:
            self._token = Token(access_token=access_token, token_type="Bearer", expires_in=900)
        elif username and password:
            self.login(username=username, password=password)

    def login(self, *, username: str, password: str) -> Token:
        r = self._session.post(
            f"{self._base_url}/auth/login",
            json={"username": username, "password": password},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        self._token = Token(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=int(data.get("expires_in", 900)),
            issued_at=data.get("issued_at"),
        )
        return self._token

    def refresh(self) -> Token:
        r = self._session.post(f"{self._base_url}/auth/refresh", timeout=20)
        r.raise_for_status()
        data = r.json()
        self._token = Token(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=int(data.get("expires_in", 900)),
            issued_at=data.get("issued_at"),
        )
        return self._token

    def _headers(self) -> dict[str, str]:
        if not self._token:
            return {}
        return {"Authorization": f"Bearer {self._token.access_token}"}

    def _post(self, path: str, payload: Any) -> requests.Response:
        url = f"{self._base_url}{path}"
        r = self._session.post(url, json=payload, headers=self._headers(), timeout=30)
        if r.status_code == 401:
            # try refresh once (if refresh cookie exists)
            try:
                self.refresh()
                r = self._session.post(url, json=payload, headers=self._headers(), timeout=30)
            except Exception:
                pass
        r.raise_for_status()
        return r

    def post_races(self, items: list[RaceUpsert]) -> None:
        if not items:
            return
        self._post("/scrape/races", {"items": [it.model_dump() for it in items]})

    def post_race_entries(self, items: list[RaceEntryUpsert]) -> None:
        if not items:
            return
        self._post("/scrape/race-entries", {"items": [it.model_dump() for it in items]})

    def post_race_results(self, items: list[RaceResultUpsert]) -> None:
        if not items:
            return
        self._post("/scrape/race-results", {"items": [it.model_dump() for it in items]})

    def post_payouts(self, items: list[PayoutUpsert]) -> None:
        if not items:
            return
        self._post("/scrape/payouts", {"items": [it.model_dump() for it in items]})

    def post_race_changes(self, items: list[RaceChangeInsert]) -> None:
        if not items:
            return
        self._post("/scrape/race-changes", {"items": [it.model_dump() for it in items]})

    def post_raw_fetch_logs(self, items: list[RawFetchLogInsert]) -> None:
        if not items:
            return
        self._post("/scrape/raw-fetch-logs", {"items": [it.model_dump() for it in items]})

    def post_odds_snapshot(self, req: OddsSnapshotUpsertRequest) -> None:
        self._post("/scrape/odds-snapshots", req.model_dump())
