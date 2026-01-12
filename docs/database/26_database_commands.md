# データベース参照コマンド集（Docker/Compose）

本書は、Docker（`docker compose`）経由で **DB情報を参照する** ためのコマンド集です。  
本リポジトリの標準DBは **PostgreSQL**（Compose上の `postgres` サービス）です。ローカル検証用に **SQLite** 構成（`services/api/compose.yml`）もあるため、末尾に補足を載せます。

---

## 0. 前提（Composeファイルの選び方）

用途に応じて Compose ファイルを選び、以降のコマンドの `COMPOSE` を置き換えて使ってください。

**重要**：`COMPOSE="docker compose ..."` のように文字列で持つと `COMPOSE ps` は実行できません。  
このドキュメントでは、コピペで事故りにくいよう **bash 配列**で定義して `"${COMPOSE[@]}" ...` で実行します。

### 0.1 PC（フル構成）

`docker-compose.pc.yaml` を使います（環境変数は `env.example` をベースに設定）。

```bash
COMPOSE=(docker compose -f docker-compose.pc.yaml --env-file env.example)
```

### 0.2 開発用（deploy/compose）

`deploy/compose/compose.dev.yaml` はデフォルト値付きです（必要に応じて `--env-file` を追加）。

```bash
COMPOSE=(docker compose -f deploy/compose/compose.dev.yaml)
```

---

## 1. 稼働状況・接続情報の確認

### 1.1 サービス一覧 / 稼働状況

```bash
"${COMPOSE[@]}" ps
```

### 1.2 Postgres のログ

```bash
"${COMPOSE[@]}" logs -n 200 postgres
```

### 1.3 Postgres のポート（ホスト側公開）確認

```bash
"${COMPOSE[@]}" port postgres 5432
```

### 1.4 Postgres の環境変数（DB名/ユーザー等）

```bash
"${COMPOSE[@]}" exec postgres env | egrep 'POSTGRES_(DB|USER|PASSWORD)|TZ' || true
```

---

## 2. psql で接続（推奨：コンテナ内から）

### 2.1 対話で入る（psql）

```bash
"${COMPOSE[@]}" exec postgres sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\""
```

### 2.2 1回だけSQL実行（-c）

```bash
"${COMPOSE[@]}" exec -T postgres sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -c \"select now();\""
```

> `-T` はTTYを割り当てず、CI/リダイレクトなどで安定します。

---

## 3. 参照系コマンド（psql メタコマンド）

以下は `psql` に入った後に実行するコマンドです。

- **DB一覧**: `\l`
- **接続先/ユーザー確認**: `\conninfo`
- **スキーマ一覧**: `\dn`
- **テーブル一覧**: `\dt`
- **テーブル一覧（サイズ等も表示）**: `\dt+`
- **ビュー一覧**: `\dv`
- **インデックス一覧**: `\di`
- **シーケンス一覧**: `\ds`
- **テーブル定義（列/制約）**: `\d <table>`
- **テーブル定義（詳細）**: `\d+ <table>`
- **拡張表示（縦持ち表示）**: `\x on` / `\x off`

---

## 4. 参照SQL（コピー&ペースト）

### 4.1 スキーマ/テーブル一覧

```bash
"${COMPOSE[@]}" exec -T postgres sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -c \"select table_schema, table_name from information_schema.tables where table_type = 'BASE TABLE' and table_schema not in ('pg_catalog','information_schema') order by table_schema, table_name;\""
```

### 4.2 列定義（information_schema）

```bash
"${COMPOSE[@]}" exec -T postgres sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -c \"select table_schema, table_name, ordinal_position, column_name, data_type, is_nullable, column_default from information_schema.columns where table_schema not in ('pg_catalog','information_schema') order by table_schema, table_name, ordinal_position;\""
```

### 4.3 制約（PK/UK/FK）確認

```bash
"${COMPOSE[@]}" exec -T postgres sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -c \"select tc.table_schema, tc.table_name, tc.constraint_name, tc.constraint_type from information_schema.table_constraints tc where tc.table_schema not in ('pg_catalog','information_schema') order by tc.table_schema, tc.table_name, tc.constraint_type, tc.constraint_name;\""
```

### 4.4 テーブルサイズ（大きい順）

```bash
"${COMPOSE[@]}" exec -T postgres sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -c \"select n.nspname as schema, c.relname as table, pg_size_pretty(pg_total_relation_size(c.oid)) as total_size from pg_class c join pg_namespace n on n.oid = c.relnamespace where c.relkind = 'r' and n.nspname not in ('pg_catalog','information_schema') order by pg_total_relation_size(c.oid) desc limit 50;\""
```

### 4.5 接続中セッション（重い/詰まり調査の入口）

```bash
"${COMPOSE[@]}" exec -T postgres sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -c \"select pid, usename, application_name, client_addr, state, wait_event_type, wait_event, now() - query_start as running_for, left(query, 200) as query_head from pg_stat_activity where datname = current_database() order by query_start nulls last;\""
```

### 4.6 あるテーブルの情報一覧（見過ぎ防止：列絞り + WHERE/ORDER + LIMIT + 整形）

大量表示を避けるため、まずは以下の方針で確認してください。

- **列を絞る**（`select *` は避ける）
- **WHERE で範囲を絞る**（期間・ID・ステータス等）
- **ORDER BY で並びを固定**（再現性）
- **LIMIT を付ける**（必須）
- **pager を OFF**（`-P pager=off`）で意図しないスクロール地獄を避ける

#### 4.6.1 テンプレ（TABLE/COLS/WHERE/LIMIT を差し替え）

```bash
TABLE="races"
COLS="race_date,baba_code,race_no,start_time,race_name,status"
WHERE="race_date >= current_date - interval '14 days'"
LIMIT=50

SQL="select ${COLS} from ${TABLE} where ${WHERE} order by 1 desc, 4 desc nulls last, 3 desc limit ${LIMIT};"
"${COMPOSE[@]}" exec -T postgres sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -P pager=off -P footer=off -P expanded=auto -c \"$SQL\""
```

#### 4.6.2 件数だけ先に見る（まず全体感を掴む）

```bash
TABLE="races"
"${COMPOSE[@]}" exec -T postgres sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -P pager=off -P footer=off -c \"select count(*) as rows from ${TABLE};\""
```

### 4.7 よく使う一覧コマンド（ユーザー一覧 / レース一覧 など）

#### 4.7.1 ユーザー一覧（legacy: `users`）

出力が増えすぎないよう、**列を絞って LIMIT** します（パスワードハッシュは表示しません）。

```bash
LIMIT=50
SQL="select id, username, role, created_at from users order by created_at desc, id desc limit ${LIMIT};"
"${COMPOSE[@]}" exec -T postgres sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -P pager=off -P footer=off -P expanded=auto -c \"$SQL\""
```

#### 4.7.2 レース一覧（legacy: `races` + `venues`）

直近分に絞って一覧します（競馬場名も表示）。

```bash
LIMIT=50
SQL="select r.race_date, v.venue_name, r.baba_code, r.race_no, r.start_time, r.race_name, r.status from races r join venues v on v.baba_code = r.baba_code where r.race_date >= current_date - interval '14 days' order by r.race_date desc, r.start_time desc nulls last, r.race_no desc limit ${LIMIT};"
"${COMPOSE[@]}" exec -T postgres sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -P pager=off -P footer=off -P expanded=auto -c \"$SQL\""
```

#### 4.7.3 レース一覧（spec: `race` + `racecourse`）

spec準拠スキーマ側（`0002_add_spec_schema.sql`）のテーブル名は `race`（単数）です。

```bash
LIMIT=50
SQL="select r.race_date, rc.name as racecourse, r.baba_code, r.race_no, r.post_time, r.race_name, r.surface, r.distance_m from race r join racecourse rc on rc.baba_code = r.baba_code where r.race_date >= current_date - interval '14 days' order by r.race_date desc, r.post_time desc nulls last, r.race_no desc limit ${LIMIT};"
"${COMPOSE[@]}" exec -T postgres sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -P pager=off -P footer=off -P expanded=auto -c \"$SQL\""
```

#### 4.7.4 直近レースの出走表一覧（legacy: `race_entries`）

「直近レース」をサブクエリで1つだけ特定し、その出走表だけを表示します（頭数分＝最大でも数十行）。

```bash
SQL="with latest_race as (select race_id from races order by race_date desc, start_time desc nulls last, race_no desc limit 1) select e.horse_number, e.horse_name, e.jockey_name, e.trainer_name, e.handicap_kg, e.body_weight, e.body_weight_diff from race_entries e join latest_race lr on lr.race_id = e.race_id order by e.horse_number;"
"${COMPOSE[@]}" exec -T postgres sh -lc "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -P pager=off -P footer=off -P expanded=auto -c \"$SQL\""
```

---

## 5. ホスト側クライアントから参照したい場合（任意）

ホストに `psql` が入っている場合は、Compose のポート公開（例: `5432:5432`）を使って接続できます。

### 5.1 `env.example` を読み込んで接続（推奨）

`env.example` が `KEY=VALUE` 形式なので、そのまま環境変数として読み込めます。

```bash
set -a
source env.example
set +a
psql "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/${POSTGRES_DB}"
```

### 5.2 環境変数を使わずに接続（手で埋める）

```bash
psql "postgresql://<user>:<password>@localhost:5432/<db>"
```

---

## 6. （補足）SQLite 構成（`services/api/compose.yml`）

`services/api/compose.yml` は `DATABASE_URL=sqlite:////app/data/app.db` です。  
この場合、DBファイルは **APIコンテナ内の** `/app/data/app.db` にあります。

### 6.1 起動/稼働確認

```bash
docker compose -f services/api/compose.yml ps
```

### 6.2 テーブル一覧（sqlite3 が入っている場合）

```bash
docker compose -f services/api/compose.yml exec -T api sqlite3 /app/data/app.db ".tables"
```

### 6.3 sqlite3 が無い場合（Python で参照）

```bash
docker compose -f services/api/compose.yml exec -T api python - <<'PY'
import sqlite3
conn = sqlite3.connect("/app/data/app.db")
cur = conn.cursor()
rows = cur.execute("select name from sqlite_master where type='table' order by name").fetchall()
for (name,) in rows:
    print(name)
PY
```


