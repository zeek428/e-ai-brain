CREATE INDEX IF NOT EXISTS idx_rd_work_items_dispatch_due_page
  ON rd_work_items (
    collaboration_run_id,
    (COALESCE(next_dispatch_at, '-infinity'::timestamptz)),
    ((CASE WHEN priority = 0 THEN 100 ELSE priority END)),
    id
  )
  WHERE status IN ('ready', 'rework_required');
