-- 0003_fix_legacy_types.sql
-- Fix schema mismatches discovered during sync from Pi -> PC.
--
-- 1) Legacy race_results columns were too short (varchar(50)) and could truncate / fail
--    when storing long corner passing orders. Use TEXT.
-- 2) Spec table entry_last5_race.passing_order_arr was created as INT[] in 0002,
--    but the SQLAlchemy model stores it as JSON for SQLite compatibility.
--    Align PostgreSQL to JSONB to avoid insert type mismatch.

ALTER TABLE race_results
  ALTER COLUMN time_str TYPE text,
  ALTER COLUMN margin TYPE text,
  ALTER COLUMN corner1 TYPE text,
  ALTER COLUMN corner2 TYPE text,
  ALTER COLUMN corner3 TYPE text,
  ALTER COLUMN corner4 TYPE text;

DO $$
BEGIN
  -- Convert INT[] -> JSONB (best-effort). If already JSON/JSONB, no-op.
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'entry_last5_race'
      AND column_name = 'passing_order_arr'
      AND data_type = 'ARRAY'
      AND udt_name = '_int4'
  ) THEN
    ALTER TABLE entry_last5_race
      ALTER COLUMN passing_order_arr TYPE jsonb
      USING to_jsonb(passing_order_arr);
  END IF;
END $$;






