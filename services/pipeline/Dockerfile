FROM python:3.12-slim

WORKDIR /app

# prefect 依存の ruamel.yaml.clibz が環境によっては sdist ビルドになり、
# gcc が無いと失敗するためビルドツールを追加する
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src /app/src
ENV PYTHONPATH=/app/src

CMD ["python", "-c", "from pipeline_service.flows import daily_train_flow; print(daily_train_flow())"]
