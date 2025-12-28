from __future__ import annotations

from typing import Any
from uuid import uuid4


def _login_admin(client) -> str:
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpass"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _issue_scraper_token(client) -> str:
    admin_token = _login_admin(client)
    client_name = f"scraper-{uuid4().hex[:8]}"
    r = client.post(
        "/admin/oauth-clients",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": client_name,
            "scopes": ["scrape:write"],
            "is_active": True,
        },
    )
    assert r.status_code in (200, 201), r.text
    client_info = r.json()["client"]

    r2 = client.post(
        "/auth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": client_info["client_id"],
            "client_secret": client_info["client_secret"],
            "scope": "scrape:write",
        },
    )
    assert r2.status_code == 200, r2.text
    return r2.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_odds_snapshot_ingest_idempotent(client) -> None:
    scraper_token = _issue_scraper_token(client)

    payload = {
        "race_key": {"race_date": "2025-12-28", "baba_code": 18, "race_no": 1},
        "bet_type": "tansho",
        "snapshot_kind": "t_minus_5m",
        "captured_at": "2025-12-28T00:00:00+00:00",
        "source_url": "https://example.invalid/odds",
        "items": [
            {"legs": [1], "is_ordered": False, "odds_min": 2.3, "odds_max": None, "popularity": 1},
            {"legs": [2], "is_ordered": False, "odds_min": 3.1, "odds_max": None, "popularity": 2},
        ],
    }

    r1 = client.post("/scrape/odds-snapshots", headers=_auth_headers(scraper_token), json=payload)
    assert r1.status_code == 201, r1.text
    body1 = r1.json()

    r2 = client.post("/scrape/odds-snapshots", headers=_auth_headers(scraper_token), json=payload)
    assert r2.status_code == 201, r2.text
    body2 = r2.json()

    assert body2["odds_snapshot_id"] == body1["odds_snapshot_id"]
    assert body2["num_items"] == len(payload["items"])

    user_token = _login_admin(client)
    r3 = client.get(
        f"/races/{body1['race_id']}/odds",
        headers=_auth_headers(user_token),
        params={"snapshot_kind": "t_minus_5m", "bet_type": "tansho"},
    )
    assert r3.status_code == 200, r3.text
    odds = r3.json()
    assert len(odds["items"]) == len(payload["items"])


def test_races_and_related_endpoints(client) -> None:
    scraper_token = _issue_scraper_token(client)
    headers = _auth_headers(scraper_token)

    race_key: dict[str, Any] = {"race_date": "2025-12-28", "baba_code": 5, "race_no": 7}

    r1 = client.post(
        "/scrape/races",
        headers=headers,
        json={
            "items": [
                {
                    "race_key": race_key,
                    "race_name": "Sample Race",
                    "start_time": "12:30",
                    "status": "scheduled",
                }
            ]
        },
    )
    assert r1.status_code == 201, r1.text

    r2 = client.post(
        "/scrape/race-entries",
        headers=headers,
        json={
            "items": [
                {
                    "race_key": race_key,
                    "horse_number": 1,
                    "horse_name": "Sample Horse",
                    "post_position": 1,
                }
            ]
        },
    )
    assert r2.status_code == 201, r2.text

    r3 = client.post(
        "/scrape/race-results",
        headers=headers,
        json={
            "items": [
                {
                    "race_key": race_key,
                    "finish_position": 1,
                    "horse_number": 1,
                    "time_str": "1:34.5",
                }
            ]
        },
    )
    assert r3.status_code == 201, r3.text

    r4 = client.post(
        "/scrape/payouts",
        headers=headers,
        json={
            "items": [
                {
                    "race_key": race_key,
                    "bet_type": "tansho",
                    "legs": [1],
                    "is_ordered": False,
                    "payout_yen": 230,
                    "popularity": 1,
                }
            ]
        },
    )
    assert r4.status_code == 201, r4.text

    r5 = client.post(
        "/scrape/race-changes",
        headers=headers,
        json={
            "items": [
                {
                    "race_key": race_key,
                    "change_type": "status",
                    "payload": {"note": "test"},
                    "captured_at": "2025-12-28T00:10:00+00:00",
                }
            ]
        },
    )
    assert r5.status_code == 201, r5.text

    user_token = _login_admin(client)
    user_headers = _auth_headers(user_token)

    venues = client.get("/venues", headers=user_headers)
    assert venues.status_code == 200, venues.text
    assert any(v["baba_code"] == 5 for v in venues.json()["items"])

    races = client.get(
        "/races",
        headers=user_headers,
        params={"race_date": "2025-12-28", "baba_code": 5, "page": 1, "page_size": 50},
    )
    assert races.status_code == 200, races.text
    races_payload = races.json()
    assert races_payload["page"] == 1
    assert races_payload["page_size"] == 50
    race_items = races_payload["items"]
    assert len(race_items) == 1
    race_id = race_items[0]["race_id"]

    race = client.get(f"/races/{race_id}", headers=user_headers)
    assert race.status_code == 200, race.text
    assert race.json()["race_key"]["race_no"] == 7

    entries = client.get(f"/races/{race_id}/entries", headers=user_headers)
    assert entries.status_code == 200, entries.text
    assert len(entries.json()["items"]) == 1

    results = client.get(f"/races/{race_id}/results", headers=user_headers)
    assert results.status_code == 200, results.text
    assert len(results.json()["items"]) == 1

    payouts = client.get(f"/races/{race_id}/payouts", headers=user_headers)
    assert payouts.status_code == 200, payouts.text
    assert len(payouts.json()["items"]) == 1
