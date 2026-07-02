CREATE TABLE IF NOT EXISTS ai_executor_approval_requests (
  id text PRIMARY KEY,
  action_id text REFERENCES plugin_actions(id) ON DELETE SET NULL,
  connection_id text REFERENCES plugin_connections(id) ON DELETE SET NULL,
  runner_id text REFERENCES ai_executor_runners(id) ON DELETE SET NULL,
  scheduled_job_id text REFERENCES scheduled_jobs(id) ON DELETE SET NULL,
  scheduled_job_run_id text REFERENCES scheduled_job_runs(id) ON DELETE SET NULL,
  ai_task_id text REFERENCES ai_tasks(id) ON DELETE SET NULL,
  executor_type text NOT NULL,
  workspace_root text NOT NULL,
  risk_level text NOT NULL DEFAULT 'high',
  blocked_operations jsonb NOT NULL DEFAULT '[]'::jsonb,
  approval_request jsonb NOT NULL DEFAULT '{}'::jsonb,
  approval jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'pending',
  requested_by text,
  requested_at timestamptz,
  approved_by text,
  approved_at timestamptz,
  expires_at timestamptz,
  reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_ai_executor_approval_requests_status CHECK (
    status IN ('pending', 'approved', 'rejected', 'expired')
  )
);

CREATE INDEX IF NOT EXISTS idx_ai_executor_approval_requests_status
  ON ai_executor_approval_requests(status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_ai_executor_approval_requests_runner
  ON ai_executor_approval_requests(runner_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_ai_executor_approval_requests_action
  ON ai_executor_approval_requests(action_id, status, updated_at DESC);
