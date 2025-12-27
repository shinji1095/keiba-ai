# docker compose（PC / Pi）

本プロジェクトは PC と Pi を別ホストで運用する前提です。
開発初期は、PC側とPi側でそれぞれ compose を起動してください。

## ローカル開発（PC 1台で全サービス）
```bash
cp .env.example .env
# PC_API_URL を http://reverse-proxy/api に設定
docker compose --env-file .env -f deploy/compose/compose.dev.yaml up --build
```

## PC側（Ubuntu PC）
```bash
cp .env.example .env
docker compose --env-file .env -f deploy/compose/compose.pc.yaml up --build
```

## Pi側（Raspberry Pi 5）
```bash
cp .env.example .env
# PC_API_URL を PC のLANアドレスに変更
docker compose --env-file .env -f deploy/compose/compose.pi.yaml up --build
```


- ドキュメント: `docs/README.md` から読み始めてください。
