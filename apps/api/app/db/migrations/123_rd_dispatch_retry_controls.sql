ALTER TABLE IF EXISTS rd_work_items
  ADD COLUMN IF NOT EXISTS dispatch_failure_count integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_dispatch_error_code text,
  ADD COLUMN IF NOT EXISTS next_dispatch_at timestamptz;

ALTER TABLE IF EXISTS rd_work_items
  DROP CONSTRAINT IF EXISTS ck_rd_work_items_dispatch_failure_count;

ALTER TABLE IF EXISTS rd_work_items
  ADD CONSTRAINT ck_rd_work_items_dispatch_failure_count
  CHECK (dispatch_failure_count >= 0);

ALTER TABLE IF EXISTS rd_work_items
  DROP CONSTRAINT IF EXISTS ck_rd_work_items_dispatch_error_code;

ALTER TABLE IF EXISTS rd_work_items
  ADD CONSTRAINT ck_rd_work_items_dispatch_error_code
  CHECK (
    last_dispatch_error_code IS NULL
    OR last_dispatch_error_code ~ '^[A-Z][A-Z0-9_]{1,127}$'
  );

CREATE INDEX IF NOT EXISTS idx_rd_work_items_dispatch_due
  ON rd_work_items (collaboration_run_id, next_dispatch_at, priority, id)
  WHERE status IN ('ready', 'rework_required');
