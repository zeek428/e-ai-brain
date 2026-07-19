CREATE INDEX IF NOT EXISTS idx_rd_collaboration_runs_status_id
  ON rd_collaboration_runs (status, id);
