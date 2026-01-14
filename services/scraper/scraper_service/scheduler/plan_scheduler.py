from __future__ import annotations

import datetime as dt
import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from scraper_service.control_server import ScheduleState, ScheduleStore
from scraper_service.utils.time import JST


def _parse_dt(value: Optional[str]) -> Optional[dt.datetime]:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value)
    except ValueError:
        return None


def _plan_item_key(item: dict) -> str:
    race_key = item.get("race_key") or {}
    odds_flg = item.get("odds_flg")
    return "|".join(
        [
            str(race_key.get("race_date", "")),
            str(race_key.get("baba_code", "")),
            str(race_key.get("race_no", "")),
            str(item.get("task_kind", "")),
            str(item.get("page_name", "")),
            str(item.get("snapshot_kind", "")),
            "" if odds_flg is None else str(odds_flg),
            str(item.get("scheduled_at", "")),
        ]
    )


@dataclass
class PlanState:
    race_date: str
    plan_generated_at: Optional[str] = None
    completed: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, object]:
        return {
            "race_date": self.race_date,
            "plan_generated_at": self.plan_generated_at,
            "completed": sorted(self.completed),
        }


class PlanStateStore:
    def __init__(self, control_dir: Path) -> None:
        self._control_dir = control_dir
        self._lock = threading.Lock()

    @property
    def control_dir(self) -> Path:
        return self._control_dir

    def _path(self, race_date: str) -> Path:
        return self._control_dir / f"scrape_plan_state_{race_date}.json"

    def load(self, race_date: str) -> PlanState:
        path = self._path(race_date)
        with self._lock:
            if not path.exists():
                return PlanState(race_date=race_date)
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return PlanState(race_date=race_date)
        completed = set(data.get("completed") or [])
        return PlanState(
            race_date=str(data.get("race_date") or race_date),
            plan_generated_at=data.get("plan_generated_at"),
            completed=completed,
        )

    def save(self, state: PlanState) -> None:
        path = self._path(state.race_date)
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(state.to_dict(), ensure_ascii=True, indent=2),
                encoding="utf-8",
            )


@dataclass
class PlanRunSummary:
    status: str
    executed: int = 0
    errors: int = 0
    generated_plan: bool = False


class PlanScheduler:
    def __init__(
        self,
        *,
        runner,
        schedule_store: ScheduleStore,
        state_store: PlanStateStore,
        now_fn: Optional[Callable[[], dt.datetime]] = None,
        tick_sec: int = 10,
    ) -> None:
        self._runner = runner
        self._schedule_store = schedule_store
        self._state_store = state_store
        self._now_fn = now_fn or (lambda: dt.datetime.now(JST))
        self._tick_sec = tick_sec
        self._control_dir = state_store.control_dir

    def run_forever(self) -> None:
        while True:
            self.run_once()
            time.sleep(self._tick_sec)

    def run_once(self) -> PlanRunSummary:
        schedule = self._schedule_store.load()
        if not schedule.enabled:
            return PlanRunSummary(status="disabled")

        now = self._now_fn()
        race_date = now.astimezone(JST).date().isoformat()

        plan, generated = self._load_or_build_plan(race_date, schedule)
        if plan is None:
            return PlanRunSummary(status="missing_plan")

        plan_generated_at = plan.get("generated_at")
        state = self._state_store.load(race_date)
        if plan_generated_at and plan_generated_at != state.plan_generated_at:
            state = PlanState(race_date=race_date, plan_generated_at=plan_generated_at)
        elif state.plan_generated_at is None:
            state.plan_generated_at = plan_generated_at

        items = plan.get("items") or []
        if not isinstance(items, list):
            return PlanRunSummary(status="invalid_plan")

        executed = 0
        errors = 0
        for item in _iter_due_items(items, now):
            key = _plan_item_key(item)
            if key in state.completed:
                continue
            try:
                self._runner.execute_plan_item(item)
            except Exception:
                errors += 1
                continue
            state.completed.add(key)
            executed += 1

        if executed or errors or state.plan_generated_at:
            self._state_store.save(state)

        return PlanRunSummary(
            status="ok",
            executed=executed,
            errors=errors,
            generated_plan=generated,
        )

    def _load_or_build_plan(
        self, race_date: str, schedule: ScheduleState
    ) -> tuple[Optional[dict], bool]:
        plan_path = self._control_dir / f"scrape_plan_{race_date}.json"
        schedule_updated_at = _parse_dt(schedule.updated_at)
        plan = None
        if plan_path.exists():
            try:
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                plan = None

        plan_generated_at = _parse_dt(plan.get("generated_at") if isinstance(plan, dict) else None)
        needs_regen = plan is None or plan_generated_at is None
        if (
            not needs_regen
            and schedule_updated_at is not None
            and schedule_updated_at > plan_generated_at
        ):
            needs_regen = True

        if needs_regen:
            plan = self._runner.build_plan(
                race_date=race_date,
                baba_codes=schedule.baba_codes,
                snapshot_kinds=schedule.snapshot_kinds,
                prefetch_days=schedule.prefetch_days,
                overwrite=True,
            )
            return plan, True

        return plan, False


def _iter_due_items(items: list[dict], now: dt.datetime):
    def _scheduled_at(item: dict) -> Optional[dt.datetime]:
        return _parse_dt(item.get("scheduled_at"))

    items_sorted = sorted(
        items,
        key=lambda it: _scheduled_at(it) or dt.datetime.max.replace(tzinfo=JST),
    )
    for item in items_sorted:
        scheduled_at = _scheduled_at(item)
        if scheduled_at is None:
            continue
        if scheduled_at > now:
            break
        yield item
