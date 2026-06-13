ALTER TABLE IF EXISTS scheduled_job_runs
  ADD COLUMN IF NOT EXISTS source_run_id text REFERENCES scheduled_job_runs(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_scheduled_job_runs_source_run
  ON scheduled_job_runs(source_run_id);
