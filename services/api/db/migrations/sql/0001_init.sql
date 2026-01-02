-- 0001_init.sql
-- Initial schema for api-service (PostgreSQL).
--
-- NOTE:
-- - docs/database/25_database_definition.md を正とするが、本リリースでは物理型の完全一致は必須としない。
-- - 重要な契約（UNIQUE / FK / キー）は一致させる。

-- -----------------------------
-- Master / Auth
-- -----------------------------

CREATE TABLE IF NOT EXISTS schema_migrations (
  version text PRIMARY KEY,
  applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
  id bigserial PRIMARY KEY,
  username text NOT NULL,
  password_hash text NOT NULL,
  role text NOT NULL DEFAULT 'user',
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_users_username UNIQUE (username)
);

CREATE TABLE IF NOT EXISTS oauth_clients (
  client_id text PRIMARY KEY,
  name text NOT NULL,
  client_secret_hash text NOT NULL,
  scopes jsonb NOT NULL DEFAULT '[]'::jsonb,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  revoked_at timestamptz NULL,
  CONSTRAINT uq_oauth_clients_name UNIQUE (name)
);

-- -----------------------------
-- Domain: venues / races
-- -----------------------------

CREATE TABLE IF NOT EXISTS venues (
  baba_code smallint PRIMARY KEY,
  venue_name text NOT NULL
);

CREATE TABLE IF NOT EXISTS races (
  race_id bigserial PRIMARY KEY,
  race_date date NOT NULL,
  baba_code smallint NOT NULL REFERENCES venues(baba_code),
  race_no smallint NOT NULL,
  start_time time NULL,
  distance_m integer NULL,
  course text NULL,
  weather text NULL,
  track_condition text NULL,
  race_name text NULL,
  field_size integer NULL,
  status text NULL,
  CONSTRAINT uq_race_key UNIQUE (race_date, baba_code, race_no)
);

CREATE INDEX IF NOT EXISTS idx_races_date ON races(race_date);
CREATE INDEX IF NOT EXISTS idx_races_date_venue ON races(race_date, baba_code);

-- -----------------------------
-- Facts: entries / results / payouts / odds
-- -----------------------------

CREATE TABLE IF NOT EXISTS race_entries (
  race_entry_id bigserial PRIMARY KEY,
  race_id bigint NOT NULL REFERENCES races(race_id) ON DELETE CASCADE,
  horse_id bigint NULL,
  post_position integer NULL,
  horse_number integer NOT NULL,
  horse_name text NOT NULL,
  jockey_name text NULL,
  trainer_name text NULL,
  handicap_kg numeric NULL,
  body_weight integer NULL,
  body_weight_diff integer NULL,
  CONSTRAINT uq_race_entry_horse_number UNIQUE (race_id, horse_number)
);

CREATE INDEX IF NOT EXISTS idx_entries_race ON race_entries(race_id);

CREATE TABLE IF NOT EXISTS odds_snapshots (
  odds_snapshot_id bigserial PRIMARY KEY,
  race_id bigint NOT NULL REFERENCES races(race_id) ON DELETE CASCADE,
  bet_type text NOT NULL,
  snapshot_kind text NOT NULL,
  captured_at timestamptz NOT NULL,
  source_url text NOT NULL,
  odds_flg integer NULL,
  is_final boolean NOT NULL DEFAULT false
);

-- UNIQUE: (race_id, bet_type, snapshot_kind, odds_flg) but odds_flg can be NULL and must be part of uniqueness.
-- Use COALESCE to treat NULL as a sentinel value.
CREATE UNIQUE INDEX IF NOT EXISTS uq_odds_snapshot_key
  ON odds_snapshots (race_id, bet_type, snapshot_kind, COALESCE(odds_flg, -1));

CREATE INDEX IF NOT EXISTS idx_odds_snap_race ON odds_snapshots(race_id);

CREATE TABLE IF NOT EXISTS odds_items (
  odds_item_id bigserial PRIMARY KEY,
  odds_snapshot_id bigint NOT NULL REFERENCES odds_snapshots(odds_snapshot_id) ON DELETE CASCADE,
  legs smallint[] NOT NULL,
  is_ordered boolean NOT NULL DEFAULT false,
  odds_min numeric NULL,
  odds_max numeric NULL,
  popularity integer NULL,
  raw_text text NULL,
  CONSTRAINT uq_odds_item_key UNIQUE (odds_snapshot_id, legs, is_ordered)
);

CREATE INDEX IF NOT EXISTS idx_odds_items_snap ON odds_items(odds_snapshot_id);

CREATE TABLE IF NOT EXISTS race_results (
  race_result_id bigserial PRIMARY KEY,
  race_id bigint NOT NULL REFERENCES races(race_id) ON DELETE CASCADE,
  finish_position integer NOT NULL,
  horse_number integer NULL,
  time_str text NULL,
  margin text NULL,
  last3f numeric NULL,
  popularity integer NULL,
  corner1 text NULL,
  corner2 text NULL,
  corner3 text NULL,
  corner4 text NULL,
  CONSTRAINT uq_race_finish_position UNIQUE (race_id, finish_position),
  CONSTRAINT uq_race_horse_number UNIQUE (race_id, horse_number)
);

CREATE INDEX IF NOT EXISTS idx_results_race ON race_results(race_id);

CREATE TABLE IF NOT EXISTS payouts (
  payout_id bigserial PRIMARY KEY,
  race_id bigint NOT NULL REFERENCES races(race_id) ON DELETE CASCADE,
  bet_type text NOT NULL,
  legs smallint[] NOT NULL,
  is_ordered boolean NOT NULL DEFAULT false,
  payout_yen integer NULL,
  popularity integer NULL,
  CONSTRAINT uq_payout_key UNIQUE (race_id, bet_type, legs, is_ordered)
);

CREATE INDEX IF NOT EXISTS idx_payout_race ON payouts(race_id);

-- -----------------------------
-- Reserved (future): race_changes
-- -----------------------------

CREATE TABLE IF NOT EXISTS race_changes (
  race_change_id bigserial PRIMARY KEY,
  race_id bigint NOT NULL REFERENCES races(race_id) ON DELETE CASCADE,
  change_type text NOT NULL,
  payload jsonb NOT NULL,
  captured_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_changes_race ON race_changes(race_id);


