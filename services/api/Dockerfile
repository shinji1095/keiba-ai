FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (bcrypt wheels usually available; keep minimal)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates cron tzdata supervisor libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
COPY requirements-dev.txt /app/requirements-dev.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements-dev.txt

COPY app /app/app
COPY db /app/db
COPY cron /app/cron
RUN chmod +x /app/cron/entrypoint.sh
COPY tests /app/tests
COPY pyproject.toml /app/pyproject.toml
COPY README.md /app/README.md
COPY supervisord.conf /etc/supervisord.conf

EXPOSE 8001

CMD ["supervisord", "-c", "/etc/supervisord.conf"]
