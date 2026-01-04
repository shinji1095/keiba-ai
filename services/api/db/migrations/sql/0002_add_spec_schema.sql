-- 0002_add_spec_schema.sql
-- Add spec-aligned normalized schema (PostgreSQL).
--
-- NOTE:
-- - This migration is additive: it does not modify existing api-service tables.
-- - The DDL is based on spec/04_postgresql_schema.md.

CREATE TABLE IF NOT EXISTS racecourse (
  baba_code SMALLINT PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS race_day (
  race_date DATE NOT NULL,
  baba_code SMALLINT NOT NULL REFERENCES racecourse(baba_code),
  PRIMARY KEY (race_date, baba_code)
);

CREATE TABLE IF NOT EXISTS race (
  race_id TEXT PRIMARY KEY, -- e.g. '27_2026-01-02_01'
  race_date DATE NOT NULL,
  baba_code SMALLINT NOT NULL,
  race_no SMALLINT NOT NULL,
  post_time TIME,
  race_name TEXT NOT NULL,
  surface TEXT,             -- 'ダート' / '芝' / NULL
  direction TEXT,
  distance_m INTEGER,
  weather TEXT,
  track_condition TEXT,
  headcount INTEGER,
  notes TEXT,
  UNIQUE (race_date, baba_code, race_no),
  FOREIGN KEY (race_date, baba_code) REFERENCES race_day(race_date, baba_code)
);

CREATE TABLE IF NOT EXISTS person (
  person_id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('jockey','trainer','owner')),
  affiliation TEXT
);

-- UNIQUE (name, role, affiliation) but affiliation can be NULL and must be part of uniqueness.
-- Use COALESCE to treat NULL as a sentinel value (same technique as odds_snapshots).
CREATE UNIQUE INDEX IF NOT EXISTS uq_person_name_role_affiliation
  ON person (name, role, COALESCE(affiliation,''));

CREATE TABLE IF NOT EXISTS horse (
  horse_id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  nar_horse_id TEXT UNIQUE, -- 取得できるなら格納
  sex TEXT CHECK (sex IN ('牡','牝','セ')),
  age SMALLINT,             -- 出馬表時点の年齢
  birth_month SMALLINT,
  birth_day SMALLINT,
  birth_md_raw TEXT,
  coat TEXT,
  sire TEXT,
  dam TEXT,
  dam_sire TEXT,
  breeder TEXT
);

-- 着別成績（定義: 1着-2着-3着-4着以下）
CREATE TABLE IF NOT EXISTS perf_total (
  perf_total_id BIGSERIAL PRIMARY KEY,
  horse_id BIGINT NOT NULL REFERENCES horse(horse_id),
  first_cnt INTEGER NOT NULL,
  second_cnt INTEGER NOT NULL,
  third_cnt INTEGER NOT NULL,
  out_cnt INTEGER NOT NULL,
  starts INTEGER GENERATED ALWAYS AS (first_cnt + second_cnt + third_cnt + out_cnt) STORED,
  UNIQUE (horse_id)
);

CREATE TABLE IF NOT EXISTS perf_dirt_left (
  perf_dirt_left_id BIGSERIAL PRIMARY KEY,
  horse_id BIGINT NOT NULL REFERENCES horse(horse_id),
  first_cnt INTEGER NOT NULL,
  second_cnt INTEGER NOT NULL,
  third_cnt INTEGER NOT NULL,
  out_cnt INTEGER NOT NULL,
  starts INTEGER GENERATED ALWAYS AS (first_cnt + second_cnt + third_cnt + out_cnt) STORED,
  UNIQUE (horse_id)
);

CREATE TABLE IF NOT EXISTS perf_dirt_right (
  perf_dirt_right_id BIGSERIAL PRIMARY KEY,
  horse_id BIGINT NOT NULL REFERENCES horse(horse_id),
  first_cnt INTEGER NOT NULL,
  second_cnt INTEGER NOT NULL,
  third_cnt INTEGER NOT NULL,
  out_cnt INTEGER NOT NULL,
  starts INTEGER GENERATED ALWAYS AS (first_cnt + second_cnt + third_cnt + out_cnt) STORED,
  UNIQUE (horse_id)
);

CREATE TABLE IF NOT EXISTS perf_track (
  perf_track_id BIGSERIAL PRIMARY KEY,
  horse_id BIGINT NOT NULL REFERENCES horse(horse_id),
  baba_code SMALLINT NOT NULL REFERENCES racecourse(baba_code),
  surface TEXT NOT NULL,
  first_cnt INTEGER NOT NULL,
  second_cnt INTEGER NOT NULL,
  third_cnt INTEGER NOT NULL,
  out_cnt INTEGER NOT NULL,
  starts INTEGER GENERATED ALWAYS AS (first_cnt + second_cnt + third_cnt + out_cnt) STORED,
  UNIQUE (horse_id, baba_code, surface)
);

CREATE TABLE IF NOT EXISTS perf_distance (
  perf_distance_id BIGSERIAL PRIMARY KEY,
  horse_id BIGINT NOT NULL REFERENCES horse(horse_id),
  baba_code SMALLINT NOT NULL REFERENCES racecourse(baba_code),
  surface TEXT NOT NULL,
  distance_m INTEGER NOT NULL,
  first_cnt INTEGER NOT NULL,
  second_cnt INTEGER NOT NULL,
  third_cnt INTEGER NOT NULL,
  out_cnt INTEGER NOT NULL,
  starts INTEGER GENERATED ALWAYS AS (first_cnt + second_cnt + third_cnt + out_cnt) STORED,
  UNIQUE (horse_id, baba_code, surface, distance_m)
);

-- 最高タイム（秒に変換して保存。良馬場のみも併記）
CREATE TABLE IF NOT EXISTS best_time (
  best_time_id BIGSERIAL PRIMARY KEY,
  horse_id BIGINT NOT NULL REFERENCES horse(horse_id),
  baba_code SMALLINT NOT NULL REFERENCES racecourse(baba_code),
  surface TEXT NOT NULL,
  distance_m INTEGER NOT NULL,
  best_time_sec NUMERIC(6,2),
  best_time_good_sec NUMERIC(6,2),
  best_time_raw TEXT,
  best_time_good_raw TEXT,
  UNIQUE (horse_id, baba_code, surface, distance_m)
);

CREATE TABLE IF NOT EXISTS race_entry (
  race_id TEXT NOT NULL REFERENCES race(race_id),
  horse_no SMALLINT NOT NULL,
  waku SMALLINT,
  horse_id BIGINT REFERENCES horse(horse_id),

  burden_weight_display NUMERIC(4,1) NOT NULL, -- 画面表示の負担重量（減量後）
  apprentice_allowance_symbol CHAR(1),        -- 減量記号（★/▲/△/◇/☆）。記号なしはNULL
  apprentice_allowance_kg SMALLINT,          -- 減量kg（4/3/2/1）。記号なしは0/NULL
  burden_weight_base NUMERIC(4,1),           -- 基準重量（推測: burden_weight_display + apprentice_allowance_kg）

  body_weight INTEGER,
  body_weight_diff INTEGER,
  win_odds NUMERIC(8,1),
  popularity INTEGER,

  jockey_person_id BIGINT REFERENCES person(person_id),
  trainer_person_id BIGINT REFERENCES person(person_id),
  owner_person_id BIGINT REFERENCES person(person_id),

  perf_total_id BIGINT REFERENCES perf_total(perf_total_id),
  perf_dirt_left_id BIGINT REFERENCES perf_dirt_left(perf_dirt_left_id),
  perf_dirt_right_id BIGINT REFERENCES perf_dirt_right(perf_dirt_right_id),
  perf_track_id BIGINT REFERENCES perf_track(perf_track_id),
  perf_distance_id BIGINT REFERENCES perf_distance(perf_distance_id),
  best_time_id BIGINT REFERENCES best_time(best_time_id),

  PRIMARY KEY (race_id, horse_no)
);

-- 直近5走（要約）
CREATE TABLE IF NOT EXISTS entry_last5_race (
  race_id TEXT NOT NULL,
  horse_no SMALLINT NOT NULL,
  order_in_last5 SMALLINT NOT NULL,  -- 1..5（前走..5走前）

  finish_pos SMALLINT,
  past_race_date DATE,
  track_condition TEXT,
  runners INTEGER,
  place TEXT,
  direction TEXT,
  distance_m INTEGER,

  horse_no_in_race SMALLINT,
  popularity INTEGER,
  body_weight INTEGER,
  jockey_name TEXT,

  burden_weight NUMERIC(4,1),
  time_raw TEXT,
  time_sec NUMERIC(7,2),           -- 例: 1:32.9 -> 92.90
  passing_order_raw TEXT,
  passing_order_arr INT[],         -- 例: (4, 4, 3, 2)
  last3f NUMERIC(4,1),
  time_diff NUMERIC(4,1),
  winner_name TEXT,

  note TEXT,
  PRIMARY KEY (race_id, horse_no, order_in_last5),
  FOREIGN KEY (race_id, horse_no) REFERENCES race_entry(race_id, horse_no)
);

-- オッズ（単勝・複勝）スナップショット
CREATE TABLE IF NOT EXISTS odds_tanfuku_snapshot (
  race_id TEXT NOT NULL REFERENCES race(race_id),
  horse_no SMALLINT NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  snapshot_type TEXT NOT NULL DEFAULT 'final',
  win_odds NUMERIC(8,1),
  place_odds_min NUMERIC(8,1),
  place_odds_max NUMERIC(8,1),
  source_url TEXT,
  PRIMARY KEY (race_id, horse_no, captured_at, snapshot_type)
);

-- 減量記号マスタ（JRA表記を参照してルール化。keiba.go.jp側にも同趣旨の注記あり）
CREATE TABLE IF NOT EXISTS weight_allowance_symbol (
  symbol CHAR(1) PRIMARY KEY,   -- '★','▲','△','◇','☆'
  allowance_kg SMALLINT NOT NULL,
  note TEXT
);

-- オッズ（枠連）スナップショット
CREATE TABLE IF NOT EXISTS odds_wakuren_snapshot (
  race_id TEXT NOT NULL REFERENCES race(race_id),
  waku_1 SMALLINT NOT NULL,
  waku_2 SMALLINT NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  snapshot_type TEXT NOT NULL DEFAULT 'final',
  odds NUMERIC(10,1) NOT NULL,
  popularity_rank_derived INTEGER, -- 人気順が取得できない場合は派生値
  source_url TEXT,
  PRIMARY KEY (race_id, waku_1, waku_2, captured_at, snapshot_type)
);

-- オッズ（馬連）スナップショット（順序なし）
CREATE TABLE IF NOT EXISTS odds_umaren_snapshot (
  race_id TEXT NOT NULL REFERENCES race(race_id),
  horse_no_1 SMALLINT NOT NULL,
  horse_no_2 SMALLINT NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  snapshot_type TEXT NOT NULL DEFAULT 'final',
  odds NUMERIC(10,1) NOT NULL,
  popularity_rank INTEGER,
  source_url TEXT,
  PRIMARY KEY (race_id, horse_no_1, horse_no_2, captured_at, snapshot_type)
);

-- オッズ（馬単）スナップショット（順序あり: 1着=horse_no_1, 2着=horse_no_2）
CREATE TABLE IF NOT EXISTS odds_umatan_snapshot (
  race_id TEXT NOT NULL REFERENCES race(race_id),
  horse_no_1 SMALLINT NOT NULL,
  horse_no_2 SMALLINT NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  snapshot_type TEXT NOT NULL DEFAULT 'final',
  odds NUMERIC(10,1) NOT NULL,
  popularity_rank INTEGER,
  source_url TEXT,
  PRIMARY KEY (race_id, horse_no_1, horse_no_2, captured_at, snapshot_type)
);

-- オッズ（ワイド）スナップショット（レンジ表記）
CREATE TABLE IF NOT EXISTS odds_wide_snapshot (
  race_id TEXT NOT NULL REFERENCES race(race_id),
  horse_no_1 SMALLINT NOT NULL,
  horse_no_2 SMALLINT NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  snapshot_type TEXT NOT NULL DEFAULT 'final',
  odds_min NUMERIC(10,1) NOT NULL,
  odds_max NUMERIC(10,1) NOT NULL,
  popularity_rank_min_odds INTEGER,
  source_url TEXT,
  PRIMARY KEY (race_id, horse_no_1, horse_no_2, captured_at, snapshot_type)
);
