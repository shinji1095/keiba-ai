from __future__ import annotations

from celery import Celery


def create_celery() -> Celery:
    # NOTE: Broker/backends are placeholders. 本番運用時に Redis 等を追加してください。
    app = Celery("keiba-ai-worker", broker="memory://", backend="cache+memory://")

    @app.task(name="worker.ping")
    def ping() -> str:
        return "pong"

    return app


celery_app = create_celery()
