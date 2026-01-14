from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from scraper_service.control_server import ScheduleStore
from scraper_service.scheduler.plan_scheduler import PlanScheduler, PlanStateStore


JST = dt.timezone(dt.timedelta(hours=9))


def _write_schedule(path: Path, *, enabled: bool, updated_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "enabled": enabled,
        "baba_codes": [20],
        "snapshot_kinds": ["final"],
        "prefetch_days": 0,
        "updated_at": updated_at,
    }
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def _plan_item(*, race_date: str, scheduled_at: str) -> dict[str, object]:
    return {
        "task_kind": "odds",
        "page_name": "OddsTanFuku",
        "race_key": {"race_date": race_date, "baba_code": 20, "race_no": 1},
        "start_time": "10:00:00",
        "snapshot_kind": "final",
        "odds_flg": None,
        "target_at": scheduled_at,
        "priority": 1,
        "scheduled_at": scheduled_at,
        "within_tolerance": True,
        "delay_sec": 0,
    }


def _write_plan(path: Path, *, race_date: str, generated_at: str, items: list[dict]) -> None:
    payload = {
        "race_date": race_date,
        "snapshot_kinds": ["final"],
        "generated_at": generated_at,
        "interval_sec": 60,
        "tolerance_sec": 300,
        "items": items,
    }
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


class FakeRunner:
    def __init__(self, control_dir: Path) -> None:
        self.control_dir = control_dir
        self.built = 0
        self.executed: list[dict] = []

    def build_plan(
        self,
        *,
        race_date: str,
        baba_codes: list[int],
        snapshot_kinds: list[str],
        prefetch_days: int,
        overwrite: bool,
    ) -> dict:
        _ = (baba_codes, snapshot_kinds, prefetch_days, overwrite)
        self.built += 1
        scheduled_at = f"{race_date}T09:00:00+09:00"
        plan_path = self.control_dir / f"scrape_plan_{race_date}.json"
        _write_plan(
            plan_path,
            race_date=race_date,
            generated_at=scheduled_at,
            items=[_plan_item(race_date=race_date, scheduled_at=scheduled_at)],
        )
        return json.loads(plan_path.read_text(encoding="utf-8"))

    def execute_plan_item(self, item: dict) -> None:
        self.executed.append(item)


def test_plan_scheduler_executes_due_tasks_once(tmp_path: Path) -> None:
    control_dir = tmp_path / "control"
    schedule_path = control_dir / "schedule.json"
    _write_schedule(schedule_path, enabled=True, updated_at="2026-01-14T00:00:00+09:00")

    race_date = "2026-01-14"
    plan_path = control_dir / f"scrape_plan_{race_date}.json"
    past = "2026-01-14T08:00:00+09:00"
    _write_plan(plan_path, race_date=race_date, generated_at=past, items=[_plan_item(race_date=race_date, scheduled_at=past)])

    runner = FakeRunner(control_dir)
    scheduler = PlanScheduler(
        runner=runner,
        schedule_store=ScheduleStore(schedule_path),
        state_store=PlanStateStore(control_dir),
        now_fn=lambda: dt.datetime(2026, 1, 14, 9, 0, tzinfo=JST),
    )

    result1 = scheduler.run_once()
    result2 = scheduler.run_once()

    assert result1.executed == 1
    assert result2.executed == 0
    assert len(runner.executed) == 1


def test_plan_scheduler_builds_plan_when_missing(tmp_path: Path) -> None:
    control_dir = tmp_path / "control"
    schedule_path = control_dir / "schedule.json"
    _write_schedule(schedule_path, enabled=True, updated_at="2026-01-14T00:00:00+09:00")

    runner = FakeRunner(control_dir)
    scheduler = PlanScheduler(
        runner=runner,
        schedule_store=ScheduleStore(schedule_path),
        state_store=PlanStateStore(control_dir),
        now_fn=lambda: dt.datetime(2026, 1, 14, 9, 1, tzinfo=JST),
    )

    result = scheduler.run_once()

    assert result.executed == 1
    assert runner.built == 1
    assert len(runner.executed) == 1


def test_plan_scheduler_skips_when_disabled(tmp_path: Path) -> None:
    control_dir = tmp_path / "control"
    schedule_path = control_dir / "schedule.json"
    _write_schedule(schedule_path, enabled=False, updated_at="2026-01-14T00:00:00+09:00")

    runner = FakeRunner(control_dir)
    scheduler = PlanScheduler(
        runner=runner,
        schedule_store=ScheduleStore(schedule_path),
        state_store=PlanStateStore(control_dir),
        now_fn=lambda: dt.datetime(2026, 1, 14, 9, 1, tzinfo=JST),
    )

    result = scheduler.run_once()

    assert result.status == "disabled"
    assert runner.built == 0
    assert runner.executed == []
