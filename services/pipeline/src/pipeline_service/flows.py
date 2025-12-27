from __future__ import annotations

import os
from prefect import flow, task


@task
def example_step() -> str:
    return "ok"


@flow(name="keiba-ai-daily-train")
def daily_train_flow() -> dict[str, str]:
    # NOTE: 実運用では「データ収集→検証→学習→評価→登録→配布」をここに実装します。
    api_base = os.getenv("API_BASE_URL", "http://api:8000")
    _ = api_base
    s = example_step()
    return {"status": s}
