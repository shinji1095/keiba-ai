"""Durable monitoring shared by the control and scheduler processes.

Monitoring writes are best effort: a monitoring storage failure must not stop collection.
"""

import hashlib
import json
import logging
import sqlite3
import threading
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from functools import wraps
from pathlib import Path

LOG = logging.getLogger(__name__)


def now_iso():
    return datetime.now(UTC).isoformat()


def best_effort(method):
    @wraps(method)
    def wrapped(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except (sqlite3.Error, OSError, ValueError):
            LOG.exception("monitoring storage unavailable")
            return None

    return wrapped


def scheduled_job_id(plan_version, item_key):
    return hashlib.sha256(f"{plan_version}|{item_key}".encode()).hexdigest()[:32]


def plan_item_key(item):
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


class MonitorStore:
    def __init__(self, control_dir: Path):
        self.path = control_dir / "monitoring.sqlite3"
        self._local = threading.local()

    @contextmanager
    def connection(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=0.5)
        db.row_factory = sqlite3.Row
        try:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS workers (name TEXT PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, worker TEXT NOT NULL, status TEXT NOT NULL,
                    race_date TEXT, baba_code INTEGER, plan_version TEXT,
                    updated_at TEXT NOT NULL, data TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS ix_jobs_date ON jobs(race_date, updated_at);
            """)
            yield db
            db.commit()
        finally:
            db.close()

    @best_effort
    def start_worker(self, name, recover_worker=None):
        with self.connection() as db:
            for row in db.execute("SELECT * FROM jobs WHERE worker=? AND status='running'", (recover_worker or name,)):
                data = json.loads(row["data"])
                data.update(status="interrupted", finished_at=now_iso(), error="プロセス再起動で処理が中断しました")
                db.execute(
                    "UPDATE jobs SET status='interrupted', updated_at=?, data=? WHERE id=?",
                    (now_iso(), json.dumps(data), row["id"]),
                )
            db.execute(
                "INSERT OR REPLACE INTO workers VALUES (?,?)",
                (
                    name,
                    json.dumps({"name": name, "started_at": now_iso(), "heartbeat_at": now_iso(), "phase": "starting"}),
                ),
            )

    @best_effort
    def heartbeat(self, name):
        self.worker(name, heartbeat_at=now_iso())

    @best_effort
    def worker(self, name, **fields):
        with self.connection() as db:
            row = db.execute("SELECT data FROM workers WHERE name=?", (name,)).fetchone()
            data = json.loads(row[0]) if row else {"name": name, "started_at": now_iso()}
            data.update(fields)
            db.execute("INSERT OR REPLACE INTO workers VALUES (?,?)", (name, json.dumps(data)))

    def heartbeat_thread(self, name, stop):
        self.heartbeat(name)

        def loop():
            while not stop.wait(10):
                self.heartbeat(name)

        thread = threading.Thread(target=loop, daemon=True, name=f"heartbeat-{name}")
        thread.start()
        return thread

    @best_effort
    def start_job(self, job_id, worker, target, plan_version=None):
        at = now_iso()
        race_key = target.get("race_key") or target
        with self.connection() as db:
            row = db.execute("SELECT data FROM jobs WHERE id=?", (job_id,)).fetchone()
            prev = json.loads(row[0]) if row else {}
            data = {
                "id": job_id,
                "worker": worker,
                "status": "running",
                "target": target,
                "plan_version": plan_version,
                "started_at": at,
                "finished_at": None,
                "progress_at": at,
                "saved_items": 0,
                "error": None,
                "attempts": prev.get("attempts", 0) + 1,
            }
            db.execute(
                "INSERT OR REPLACE INTO jobs VALUES (?,?,?,?,?,?,?,?)",
                (
                    job_id,
                    worker,
                    "running",
                    race_key.get("race_date"),
                    race_key.get("baba_code"),
                    plan_version,
                    at,
                    json.dumps(data),
                ),
            )
            db.execute("DELETE FROM jobs WHERE updated_at < ?", ((datetime.now(UTC) - timedelta(days=30)).isoformat(),))
        self._local.job_id = job_id

    @best_effort
    def progress(self, saved=0):
        job_id = getattr(self._local, "job_id", None)
        if job_id:
            self.update_job(job_id, saved=saved, progress_at=now_iso())

    @best_effort
    def update_job(self, job_id, saved=0, **fields):
        with self.connection() as db:
            row = db.execute("SELECT data FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                return
            data = json.loads(row[0])
            data.update(fields)
            data["saved_items"] += saved
            db.execute(
                "UPDATE jobs SET status=?,updated_at=?,data=? WHERE id=?",
                (data["status"], now_iso(), json.dumps(data), job_id),
            )

    @best_effort
    def finish_job(self, job_id, error=None, retry=False):
        detail = self.job(job_id)
        status = ("retrying" if retry else "failed") if error else "success" if detail.get("saved_items") else "skipped"
        self.update_job(
            job_id,
            status=status,
            finished_at=now_iso(),
            error=str(error)[:1000] if error else None,
            note="保存対象データなし・未公開または対象なし" if status == "skipped" else None,
        )
        self._local.job_id = None

    def job(self, job_id):
        with self.connection() as db:
            row = db.execute("SELECT data FROM jobs WHERE id=?", (job_id,)).fetchone()
            return json.loads(row[0]) if row else {}

    def jobs(self, race_date=None, baba_code=None, status=None, page=1, page_size=30):
        clauses, params = [], []
        for name, value in (("race_date", race_date), ("baba_code", baba_code), ("status", status)):
            if value is not None:
                clauses.append(f"{name}=?")
                params.append(value)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.connection() as db:
            total = db.execute("SELECT COUNT(*) FROM jobs" + where, params).fetchone()[0]
            rows = db.execute(
                "SELECT data FROM jobs" + where + " ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                [*params, page_size, (page - 1) * page_size],
            ).fetchall()
        return {"items": [json.loads(row[0]) for row in rows], "total": total, "page": page, "page_size": page_size}

    def status(self, plan, completed):
        with self.connection() as db:
            workers = [json.loads(row[0]) for row in db.execute("SELECT data FROM workers")]
            rows = db.execute("SELECT data FROM jobs WHERE status='running'").fetchall()
            running = [json.loads(row[0]) for row in rows]
            version = plan.get("generated_at") if plan else None
            current_jobs = [
                json.loads(r[0])
                for r in db.execute("SELECT data FROM jobs WHERE worker='scheduler' AND plan_version=?", (version,))
            ]
            counts = dict(Counter(job["status"] for job in current_jobs))
        now = datetime.now(UTC)
        for worker in workers:
            heartbeat = worker.get("heartbeat_at")
            age = (now - datetime.fromisoformat(heartbeat)).total_seconds() if heartbeat else None
            worker["age_sec"] = age
            worker["alive"] = age is not None and age < 60
        items = plan.get("items", []) if plan else []
        total = len(items)
        completed_keys = set(completed)
        completed_keys.update(
            plan_item_key(job["target"]) for job in current_jobs if job["status"] in ("success", "skipped")
        )
        done = sum(plan_item_key(item) in completed_keys for item in items)
        counts["planned"] = max(
            0, total - done - counts.get("running", 0) - counts.get("retrying", 0) - counts.get("interrupted", 0)
        )
        upcoming = [
            item["scheduled_at"]
            for item in items
            if item.get("scheduled_at")
            and datetime.fromisoformat(item["scheduled_at"]) > now
            and plan_item_key(item) not in completed_keys
        ]
        overdue = sum(
            1
            for item in items
            if item.get("scheduled_at")
            and plan_item_key(item) not in completed_keys
            and (now - datetime.fromisoformat(item["scheduled_at"])).total_seconds() > plan.get("tolerance_sec", 300)
        )
        for job in running:
            worker = next(
                (w for w in workers if w["name"] == ("control" if job["worker"] == "manual" else job["worker"])),
                None,
            )
            job["worker_alive"] = bool(worker and worker["alive"])
            job["delayed"] = (now - datetime.fromisoformat(job["progress_at"])).total_seconds() > (
                1800 if job["worker"] == "manual" else 600
            )
        return {
            "workers": workers,
            "running": running,
            "progress": {
                "total": total,
                "completed": done,
                "counts": counts,
                "next_at": min(upcoming) if upcoming else None,
                "plan_generated_at": version,
                "plan_available": plan is not None,
                "overdue": overdue,
            },
        }
