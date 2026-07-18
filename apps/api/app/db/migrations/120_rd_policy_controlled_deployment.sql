-- P1 bridge: deployment remains owned by the existing deployment domain, but
-- a deployed-target collaboration run may now expose its non-terminal state.

ALTER TABLE IF EXISTS rd_collaboration_runs
  DROP CONSTRAINT IF EXISTS ck_rd_collaboration_runs_status;

ALTER TABLE IF EXISTS rd_collaboration_runs
  ADD CONSTRAINT ck_rd_collaboration_runs_status CHECK (
    status IN (
      'draft', 'planning', 'running', 'waiting_human', 'integrating',
      'verifying', 'ready_for_release', 'deploying', 'completed', 'failed', 'cancelled'
    )
  );

ALTER TABLE IF EXISTS deployment_requests
  ADD COLUMN IF NOT EXISTS rd_collaboration_run_id text
    REFERENCES rd_collaboration_runs(id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_deployment_requests_rd_collaboration_run
  ON deployment_requests (rd_collaboration_run_id)
  WHERE rd_collaboration_run_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_rd_collaboration_runs_deployed_target_ready
  ON rd_collaboration_runs (product_version_id, updated_at DESC)
  WHERE delivery_target = 'deployed'
    AND status IN ('ready_for_release', 'deploying');
