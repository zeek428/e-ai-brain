DO $migration$
DECLARE
  retry_count_nullable boolean;
BEGIN
  IF to_regclass('public.rd_work_items') IS NULL THEN
    RETURN;
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'rd_work_items'
      AND column_name = 'dispatch_failure_count'
  ) THEN
    ALTER TABLE rd_work_items
      ADD COLUMN dispatch_failure_count integer NOT NULL DEFAULT 0;
  ELSE
    IF NOT EXISTS (
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = 'public'
        AND table_name = 'rd_work_items'
        AND column_name = 'dispatch_failure_count'
        AND column_default = '0'
    ) THEN
      ALTER TABLE rd_work_items ALTER COLUMN dispatch_failure_count SET DEFAULT 0;
    END IF;

    SELECT is_nullable = 'YES'
    INTO retry_count_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'rd_work_items'
      AND column_name = 'dispatch_failure_count';
    IF retry_count_nullable THEN
      UPDATE rd_work_items SET dispatch_failure_count = 0 WHERE dispatch_failure_count IS NULL;
      ALTER TABLE rd_work_items ALTER COLUMN dispatch_failure_count SET NOT NULL;
    END IF;
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'rd_work_items'
      AND column_name = 'last_dispatch_error_code'
  ) THEN
    ALTER TABLE rd_work_items ADD COLUMN last_dispatch_error_code text;
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'rd_work_items'
      AND column_name = 'next_dispatch_at'
  ) THEN
    ALTER TABLE rd_work_items ADD COLUMN next_dispatch_at timestamptz;
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conrelid = 'rd_work_items'::regclass
      AND conname = 'ck_rd_work_items_dispatch_failure_count'
  ) THEN
    ALTER TABLE rd_work_items
      ADD CONSTRAINT ck_rd_work_items_dispatch_failure_count
      CHECK (dispatch_failure_count >= 0) NOT VALID;
  END IF;
  IF EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conrelid = 'rd_work_items'::regclass
      AND conname = 'ck_rd_work_items_dispatch_failure_count'
      AND NOT convalidated
  ) THEN
    ALTER TABLE rd_work_items VALIDATE CONSTRAINT ck_rd_work_items_dispatch_failure_count;
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conrelid = 'rd_work_items'::regclass
      AND conname = 'ck_rd_work_items_dispatch_error_code'
  ) THEN
    ALTER TABLE rd_work_items
      ADD CONSTRAINT ck_rd_work_items_dispatch_error_code
      CHECK (
        last_dispatch_error_code IS NULL
        OR last_dispatch_error_code ~ '^[A-Z][A-Z0-9_]{1,127}$'
      ) NOT VALID;
  END IF;
  IF EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conrelid = 'rd_work_items'::regclass
      AND conname = 'ck_rd_work_items_dispatch_error_code'
      AND NOT convalidated
  ) THEN
    ALTER TABLE rd_work_items VALIDATE CONSTRAINT ck_rd_work_items_dispatch_error_code;
  END IF;
END
$migration$;
