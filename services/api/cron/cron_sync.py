from __future__ import annotations

import json
import os
import sys
import urllib.request


def _log(msg: str) -> None:
    sys.stderr.write(f"{msg}\n")


def _post_sync(base_url: str) -> dict:
    url = f"{base_url.rstrip('/')}/scrape/sync/scheduled"
    payload = json.dumps({"reason": "scheduled"}, ensure_ascii=True).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as res:
        body = res.read().decode("utf-8")
        if res.status >= 400:
            raise RuntimeError(f"sync status={res.status}")
    if not body:
        return {}
    return json.loads(body)


def main() -> int:
    base_url = os.getenv("SCRAPE_SYNC_API_URL", "").strip()
    if not base_url:
        base_url = os.getenv("API_BASE_URL", "").strip()
    if not base_url:
        _log("SCRAPE_SYNC_API_URL or API_BASE_URL is required")
        return 2

    try:
        _ = _post_sync(base_url)
    except Exception as exc:
        _log(f"sync failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
