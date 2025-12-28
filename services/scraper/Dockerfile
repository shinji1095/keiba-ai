FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements/base.txt /app/requirements/base.txt
RUN pip install --no-cache-dir -r /app/requirements/base.txt

# Copy source
COPY scraper_service /app/scraper_service
COPY README.md /app/README.md
COPY pyproject.toml /app/pyproject.toml

# Default command prints help
CMD ["python", "-m", "scraper_service.cli", "--help"]
