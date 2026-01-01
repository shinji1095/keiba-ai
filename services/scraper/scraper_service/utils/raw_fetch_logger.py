from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from scraper_service.http.client import FetchResult
from scraper_service.keiba.models import RaceKey, RawFetchLogInsert


@dataclass
class RawFetchLogger:
    csv_path: Path

    def __post_init__(self) -> None:
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.csv_path.exists():
            with self.csv_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(
                    [
                        "captured_at",
                        "page_type",
                        "race_date",
                        "baba_code",
                        "race_no",
                        "url",
                        "final_url",
                        "http_status",
                        "sha256",
                        "storage_path",
                        "elapsed_ms",
                        "content_type",
                        "content_encoding",
                        "note",
                    ]
                )

    def record(
        self,
        res: FetchResult,
        *,
        race_date: Optional[str],
        baba_code: Optional[int],
        race_no: Optional[int],
        note: str = "",
    ) -> RawFetchLogInsert:
        with self.csv_path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    res.captured_at,
                    res.page_type,
                    race_date or "",
                    baba_code if baba_code is not None else "",
                    race_no if race_no is not None else "",
                    res.url,
                    res.final_url,
                    res.http_status,
                    res.sha256 or "",
                    res.storage_path or "",
                    res.elapsed_ms,
                    res.content_type or "",
                    res.content_encoding or "",
                    note,
                ]
            )

        race_key = None
        if race_date and baba_code is not None and race_no is not None:
            race_key = RaceKey(race_date=race_date, baba_code=baba_code, race_no=race_no)

        return RawFetchLogInsert(
            race_key=race_key,
            page_type=res.page_type,
            url=res.final_url or res.url,
            http_status=res.http_status,
            sha256=res.sha256,
            storage_path=res.storage_path,
            captured_at=res.captured_at,
            note=note or None,
        )
