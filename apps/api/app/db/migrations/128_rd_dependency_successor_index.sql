CREATE INDEX IF NOT EXISTS idx_rd_work_item_dependencies_successor
  ON rd_work_item_dependencies (
    collaboration_run_id,
    successor_work_item_id,
    predecessor_work_item_id,
    id
  );
