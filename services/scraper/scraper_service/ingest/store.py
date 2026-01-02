from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from scraper_service.utils.time import iso_now_jst


def _race_key_tuple(payload: dict) -> Optional[tuple[str, int, int]]:
    race_key = payload.get("race_key")
    if not isinstance(race_key, dict):
        return None
    race_date = race_key.get("race_date")
    baba_code = race_key.get("baba_code")
    race_no = race_key.get("race_no")
    if not isinstance(race_date, str) or not race_date:
        return None
    try:
        baba_code = int(baba_code)
        race_no = int(race_no)
    except (TypeError, ValueError):
        return None
    return (race_date, baba_code, race_no)


def _legs_key(value: object) -> Optional[str]:
    if not isinstance(value, list) or not value:
        return None
    try:
        return "-".join(str(int(x)) for x in value)
    except (TypeError, ValueError):
        return None


def _payload_key(kind: str, payload: dict) -> Optional[str]:
    race_key = _race_key_tuple(payload)
    if race_key is None:
        return None
    key = f"{race_key[0]}:{race_key[1]}:{race_key[2]}"
    if kind == "races":
        return key
    if kind == "race_entries":
        horse_number = payload.get("horse_number")
        try:
            horse_number = int(horse_number)
        except (TypeError, ValueError):
            return None
        return f"{key}|{horse_number}"
    if kind == "race_results":
        finish_position = payload.get("finish_position")
        try:
            finish_position = int(finish_position)
        except (TypeError, ValueError):
            return None
        return f"{key}|{finish_position}"
    if kind == "payouts":
        bet_type = payload.get("bet_type")
        legs = _legs_key(payload.get("legs"))
        is_ordered = payload.get("is_ordered")
        if not isinstance(bet_type, str) or not bet_type or legs is None:
            return None
        return f"{key}|{bet_type}|{legs}|{bool(is_ordered)}"
    if kind == "race_changes":
        change_type = payload.get("change_type")
        captured_at = payload.get("captured_at")
        if not isinstance(change_type, str) or not isinstance(captured_at, str):
            return None
        return f"{key}|{change_type}|{captured_at}"
    if kind == "odds_snapshots":
        bet_type = payload.get("bet_type")
        snapshot_kind = payload.get("snapshot_kind")
        odds_flg = payload.get("odds_flg")
        if not isinstance(bet_type, str) or not isinstance(snapshot_kind, str):
            return None
        odds_key = "" if odds_flg is None else str(odds_flg)
        return f"{key}|{bet_type}|{snapshot_kind}|{odds_key}"
    return None


def _matches_filter(
    payload: dict,
    *,
    race_date: Optional[str],
    baba_code: Optional[int],
    race_no: Optional[int],
) -> bool:
    if race_date is None and baba_code is None and race_no is None:
        return True
    race_key = _race_key_tuple(payload)
    if race_key is None:
        return False
    if race_date is not None and race_key[0] != race_date:
        return False
    if baba_code is not None and race_key[1] != baba_code:
        return False
    if race_no is not None and race_key[2] != race_no:
        return False
    return True


@dataclass
class IngestStore:
    root: Path

    def __post_init__(self) -> None:
        self._lock = threading.Lock()

    def append(self, *, kind: str, payloads: Iterable[dict]) -> int:
        items = list(payloads)
        if not items:
            return 0
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{kind}.jsonl"
        received_at = iso_now_jst()
        with self._lock, path.open("a", encoding="utf-8") as f:
            for payload in items:
                record = {
                    "received_at": received_at,
                    "kind": kind,
                    "payload": payload,
                }
                f.write(json.dumps(record, ensure_ascii=True))
                f.write("\n")
        return len(items)

    def list_latest(
        self,
        *,
        kind: str,
        race_date: Optional[str] = None,
        baba_code: Optional[int] = None,
        race_no: Optional[int] = None,
    ) -> list[dict]:
        path = self.root / f"{kind}.jsonl"
        if not path.exists():
            return []
        latest: dict[str, dict] = {}
        with self._lock, path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = record.get("payload")
                if not isinstance(payload, dict):
                    continue
                if not _matches_filter(
                    payload,
                    race_date=race_date,
                    baba_code=baba_code,
                    race_no=race_no,
                ):
                    continue
                key = _payload_key(kind, payload)
                if key is None:
                    continue
                latest[key] = payload
        return list(latest.values())
