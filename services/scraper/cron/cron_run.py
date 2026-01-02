from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request


def _log(msg: str) -> None:
    sys.stderr.write(f"{msg}\n")


def _fetch_schedule(base_url: str) -> dict:
    url = f"{base_url.rstrip('/')}/control/schedule"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as res:
        if res.status != 200:
            raise RuntimeError(f"schedule status={res.status}")
        body = res.read().decode("utf-8")
    return json.loads(body)


def _build_cmd(
    baba_codes: list[int],
    *,
    snapshot_kinds: list[str] | None,
    prefetch_days: int | None,
) -> list[str]:
    cmd = ["python", "-m", "scraper_service.cli", "scrape", "scheduled"]
    for code in baba_codes:
        cmd += ["--baba-code", str(code)]
    if snapshot_kinds:
        for k in snapshot_kinds:
            cmd += ["--snapshot-kind", k]
    if prefetch_days is not None:
        cmd += ["--prefetch-days", str(prefetch_days)]
    return cmd


def main() -> int:
    base_url = os.getenv("SCRAPER_CONTROL_URL", "").strip()
    if not base_url:
        _log("SCRAPER_CONTROL_URL is required")
        return 2

    try:
        schedule = _fetch_schedule(base_url)
    except Exception as exc:
        _log(f"failed to fetch schedule: {exc}")
        return 1

    if not schedule.get("enabled", False):
        _log("schedule disabled; skip")
        return 0

    baba_codes = schedule.get("baba_codes") or []
    if not isinstance(baba_codes, list):
        baba_codes = []

    snapshot_kinds = schedule.get("snapshot_kinds")
    if not isinstance(snapshot_kinds, list):
        snapshot_kinds = None
    else:
        snapshot_kinds = [str(x) for x in snapshot_kinds if str(x).strip()]

    prefetch_days = schedule.get("prefetch_days")
    try:
        prefetch_days = int(prefetch_days) if prefetch_days is not None else None
    except (TypeError, ValueError):
        prefetch_days = None

    cmd = _build_cmd(
        [int(x) for x in baba_codes],
        snapshot_kinds=snapshot_kinds,
        prefetch_days=prefetch_days,
    )
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        _log(f"scrape failed: {exc}")
        return int(exc.returncode) if exc.returncode else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
