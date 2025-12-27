from worker_service.celery_app import create_celery


def test_ping_task():
    app = create_celery()
    r = app.send_task("worker.ping")
    assert r.get(timeout=5) == "pong"
