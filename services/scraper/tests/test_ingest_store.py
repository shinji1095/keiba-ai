from __future__ import annotations

import json

from scraper_service.ingest.store import IngestStore


def test_ingest_store_appends_payloads(tmp_path) -> None:
    store = IngestStore(tmp_path)
    payload = {"race_key": {"race_date": "2025-12-28", "baba_code": 5, "race_no": 7}}
    count = store.append(kind="races", payloads=[payload])
    assert count == 1

    path = tmp_path / "races.jsonl"
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["kind"] == "races"
    assert record["payload"]["race_key"]["baba_code"] == 5
    assert record["received_at"]


def test_ingest_store_lists_latest_payloads(tmp_path) -> None:
    store = IngestStore(tmp_path)
    payload_v1 = {
        "race_key": {"race_date": "2025-12-28", "baba_code": 5, "race_no": 7},
        "horse_number": 1,
        "horse_name": "Horse A",
    }
    payload_v2 = {
        "race_key": {"race_date": "2025-12-28", "baba_code": 5, "race_no": 7},
        "horse_number": 1,
        "horse_name": "Horse B",
    }
    store.append(kind="race_entries", payloads=[payload_v1])
    store.append(kind="race_entries", payloads=[payload_v2])

    items = store.list_latest(kind="race_entries")
    assert len(items) == 1
    assert items[0]["horse_name"] == "Horse B"

    filtered = store.list_latest(
        kind="race_entries", race_date="2025-12-28", baba_code=5, race_no=7
    )
    assert len(filtered) == 1
