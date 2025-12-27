FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src /app/src
ENV PYTHONPATH=/app/src

CMD ["python", "-c", "from pipeline_service.flows import daily_train_flow; print(daily_train_flow())"]
