from __future__ import annotations

import json

from scraper_service.ingest.store import IngestStore


def test_ingest_store_appends_payloads(tmp_path) -> None:
    store = IngestStore(tmp_path)
    payload = {"event_id": "evt-1", "race_key": {"race_date": "2025-12-28", "baba_code": 5, "race_no": 7}}
    count = store.append(kind="races", payloads=[payload])
    assert count == 1

    path = tmp_path / "races.jsonl"
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["kind"] == "races"
    assert record["payload"]["event_id"] == "evt-1"
    assert record["received_at"]
