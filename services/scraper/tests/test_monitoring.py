import threading
from datetime import UTC, datetime, timedelta

from scraper_service.monitoring import MonitorStore


def test_job_progress_failure_and_restart(tmp_path):
    monitor = MonitorStore(tmp_path)
    monitor.start_worker("manual")
    monitor.start_job("job1", "manual", {"race_date": "2026-10-25", "baba_code": 20})
    monitor.progress(saved=3)
    assert monitor.job("job1")["saved_items"] == 3
    monitor.start_worker("manual")
    assert monitor.job("job1")["status"] == "interrupted"
    monitor.start_job("job1", "manual", {"race_date": "2026-10-25", "baba_code": 20})
    monitor.finish_job("job1", error=RuntimeError("parser error"))
    job = monitor.job("job1")
    assert job["status"] == "failed"
    assert job["attempts"] == 2
    assert job["error"] == "parser error"
    assert monitor.jobs(status="failed", baba_code=20)["total"] == 1
    assert monitor.jobs(baba_code=18)["total"] == 0


def test_empty_data_skipped_and_saved_data_success(tmp_path):
    monitor = MonitorStore(tmp_path)
    monitor.start_job("empty", "manual", {})
    monitor.finish_job("empty")
    assert monitor.job("empty")["status"] == "skipped"
    monitor.start_job("good", "manual", {})
    monitor.progress(saved=2)
    monitor.finish_job("good")
    assert monitor.job("good")["status"] == "success"


def test_heartbeat_marks_stale_worker_and_storage_failure_is_nonfatal(tmp_path):
    monitor = MonitorStore(tmp_path)
    monitor.start_worker("scheduler")
    monitor.worker("scheduler", heartbeat_at=(datetime.now(UTC) - timedelta(seconds=70)).isoformat())
    assert monitor.status(None, [])["workers"][0]["alive"] is False
    monitor.path = tmp_path  # a directory cannot be opened as a SQLite DB
    monitor.start_job("bad", "manual", {})
    monitor.progress(saved=1)
    monitor.finish_job("bad")


def test_heartbeat_continues_during_worker_wait(tmp_path):
    monitor = MonitorStore(tmp_path)
    monitor.start_worker("scheduler")
    stop = threading.Event()
    thread = monitor.heartbeat_thread("scheduler", stop)
    try:
        assert monitor.status(None, [])["workers"][0]["alive"]
    finally:
        stop.set()
        thread.join(timeout=1)


def test_progress_uses_job_results_between_plan_state_saves(tmp_path):
    monitor = MonitorStore(tmp_path)
    at = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    first = {"race_key": {"race_date": "2026-10-25", "baba_code": 20, "race_no": 1}, "scheduled_at": at}
    second = {**first, "race_key": {**first["race_key"], "race_no": 2}}
    monitor.start_job("first", "scheduler", first, at)
    monitor.progress(saved=1)
    monitor.finish_job("first")
    status = monitor.status({"generated_at": at, "items": [first, second], "tolerance_sec": 300}, [])
    assert status["progress"]["completed"] == 1
    assert status["progress"]["overdue"] == 1
    assert status["progress"]["counts"]["planned"] == 1


def test_manual_job_uses_control_heartbeat_and_is_recovered(tmp_path):
    monitor = MonitorStore(tmp_path)
    monitor.start_worker("control", recover_worker="manual")
    monitor.heartbeat("control")
    monitor.start_job("manual1", "manual", {})
    assert monitor.status(None, [])["running"][0]["worker_alive"]
    monitor.start_worker("control", recover_worker="manual")
    assert monitor.job("manual1")["status"] == "interrupted"
