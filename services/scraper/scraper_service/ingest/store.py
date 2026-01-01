from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from scraper_service.utils.time import iso_now_jst


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
