FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends supervisor \
    && rm -rf /var/lib/apt/lists/*
COPY requirements /app/requirements
RUN pip install --no-cache-dir -r /app/requirements/dev.txt
COPY scraper_service /app/scraper_service
COPY tests /app/tests
COPY fixtures /app/fixtures
COPY README.md pyproject.toml /app/
COPY supervisord.conf /etc/supervisord.conf
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
