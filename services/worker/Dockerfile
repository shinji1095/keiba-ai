FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src /app/src
ENV PYTHONPATH=/app/src

CMD ["python", "-c", "from worker_service.celery_app import celery_app; print(celery_app.main)"]
