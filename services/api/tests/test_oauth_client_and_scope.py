from __future__ import annotations

from datetime import datetime, timezone


def _login_admin(client) -> str:
    r = client.post(
        "/auth/login", json={"username": "admin", "password": "adminpass"}
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_client_credentials_and_scrape_no_auth(client):
    admin_token = _login_admin(client)

    r = client.post(
        "/admin/oauth-clients",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "scraper",
            "scopes": ["scrape:write"],
            "is_active": True,
        },
    )
    assert r.status_code in (200, 201), r.text
    created = r.json()["client"]
    client_id = created["client_id"]
    client_secret = created["client_secret"]

    r2 = client.post(
        "/auth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "scrape:write",
        },
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["access_token"]

    # no auth required for scrape ingest; payload validation still applies
    r3 = client.post("/scrape/raw-fetch-logs", json={"items": []})
    assert r3.status_code == 400

    payload = {
        "items": [
            {
                "race_key": None,
                "page_type": "odds",
                "url": "https://example.invalid/odds",
                "http_status": 200,
                "sha256": None,
                "storage_path": None,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "note": "test",
            }
        ]
    }
    r4 = client.post("/scrape/raw-fetch-logs", json=payload)
    assert r4.status_code in (200, 201), r4.text
    body = r4.json()
    assert body["accepted"] == 1
    assert body["upserted"] == 1
