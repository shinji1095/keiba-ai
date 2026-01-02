from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# NOTE:
# - 本リポジトリのテストは SQLite を使うため、dialect ごとに型を切り替える。
# - 本番（PostgreSQL）では docs/database/25_database_definition.md の推奨型に寄せる。

# JSONB (PostgreSQL) / JSON (others)
JSONValue = sa.JSON().with_variant(postgresql.JSONB, "postgresql")

# smallint[] (PostgreSQL) / JSON (others)
IntArray = sa.JSON().with_variant(postgresql.ARRAY(sa.SmallInteger), "postgresql")


