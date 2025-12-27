FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY scrapy.cfg /app/scrapy.cfg
COPY src /app/src
ENV PYTHONPATH=/app/src

CMD ["python", "-m", "scraper_service.run"]
