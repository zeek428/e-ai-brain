CREATE INDEX IF NOT EXISTS idx_rd_work_items_dispatch_due
  ON rd_work_items (collaboration_run_id, next_dispatch_at, priority, id)
  WHERE status IN ('ready', 'rework_required');
