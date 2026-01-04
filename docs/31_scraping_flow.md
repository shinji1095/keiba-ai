# Scraping Flow（スクレイピング→正規化→保存）

本書は scraper-service の「実行トリガ → HTML取得 → 正規化 → 保存（Pi） → （任意）PC同期 → DB反映」までの流れを図示する。

```mermaid
flowchart TD
  subgraph T["Trigger"]
    T1["api-service / cron<br/>POST /control/scrape"] --> CS["scraper_service.control_server<br/>(submit_scrape)"]
    T2["scraper-cron<br/>services/scraper/cron/cron_run.py"] -->|GET /control/schedule| CS
    T2 -->|python -m scraper_service.cli<br/>scrape scheduled| RS["ScrapeRunner.run_scheduled"]
    CS --> RO["ScrapeRunner.run_once"]
  end

  subgraph S["Pi: scrape -> normalize -> save"]
    RO --> F["_fetch(page)"]
    RS --> F

    F --> U["build_url(page_name, race_key, odds_flg)"]
    U --> H["HttpClient.get_html<br/>(requests + retry/backoff)"]
    H --> RAW["raw HTML保存<br/>./data/raw_html/YYYY/MM/DD/{page_name}/{sha256}.html"]
    H --> HTML["HTML bytes"]

    HTML --> P1["parse_race_list"] --> RACE["RaceUpsert"] --> A1["_append_sync('races')"] --> I1["./data/ingest/races.jsonl"]
    HTML --> P2["parse_deba_table"] --> ENTRY["RaceEntryUpsert"] --> A2["_append_sync('race_entries')"] --> I2["./data/ingest/race_entries.jsonl"]
    HTML --> P2B["parse_deba_table_normalized"] --> CARD["DebaTableNormalized"] --> A2B["_append_sync('race_cards')"] --> I2B["./data/ingest/race_cards.jsonl"]
    HTML --> P3["parse_odds_* / parse_generic_odds_table"] --> ODDS["OddsSnapshotUpsertRequest"] --> A3["_append_sync('odds_snapshots')"] --> I3["./data/ingest/odds_snapshots.jsonl"]
    HTML --> P4["parse_race_mark_table"] --> RESULT["RaceResultUpsert"] --> A4["_append_sync('race_results')"] --> I4["./data/ingest/race_results.jsonl"]
    HTML --> P5["parse_refund_money_list"] --> PAY["PayoutUpsert"] --> A5["_append_sync('payouts')"] --> I5["./data/ingest/payouts.jsonl"]
  end

  subgraph O["Optional: PC pull -> DB (api-service)"]
    I1 -->|/control/export/* (list_latest)| X["api-service sync pull"]
    I2 -->|/control/export/*| X
    I2B -->|/control/export/*| X
    I3 -->|/control/export/*| X
    I4 -->|/control/export/*| X
    I5 -->|/control/export/*| X
    X --> API["POST /scrape/*"]
    API --> DB[(PostgreSQL upsert)]
  end
```
