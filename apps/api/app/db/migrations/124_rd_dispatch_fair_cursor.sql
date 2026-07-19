CREATE TABLE IF NOT EXISTS rd_dispatch_sweep_cursors (
  id text PRIMARY KEY,
  last_run_id text,
  version bigint NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_rd_dispatch_sweep_cursor_singleton CHECK (id = 'automatic_dispatch'),
  CONSTRAINT ck_rd_dispatch_sweep_cursor_version CHECK (version > 0)
);

CREATE TABLE IF NOT EXISTS rd_dispatch_run_cursors (
  collaboration_run_id text PRIMARY KEY
    REFERENCES rd_collaboration_runs(id) ON DELETE CASCADE,
  cursor_next_dispatch_at timestamptz,
  cursor_priority integer NOT NULL,
  cursor_work_item_id text NOT NULL,
  version bigint NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_rd_dispatch_run_cursor_version CHECK (version > 0)
);

CREATE INDEX IF NOT EXISTS idx_rd_work_items_dispatch_due_page
  ON rd_work_items (
    collaboration_run_id,
    (COALESCE(next_dispatch_at, '-infinity'::timestamptz)),
    ((CASE WHEN priority = 0 THEN 100 ELSE priority END)),
    id
  )
  WHERE status IN ('ready', 'rework_required');
