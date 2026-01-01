FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (bcrypt wheels usually available; keep minimal)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates cron \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
COPY requirements-dev.txt /app/requirements-dev.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements-dev.txt

COPY app /app/app
COPY cron /app/cron
RUN chmod +x /app/cron/entrypoint.sh
COPY tests /app/tests
COPY README.md /app/README.md
COPY .env.example /app/.env.example

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
