CREATE TABLE IF NOT EXISTS collector_runs (
  id text PRIMARY KEY,
  collector_type text NOT NULL,
  product_id text REFERENCES products(id) ON DELETE SET NULL,
  status text NOT NULL DEFAULT 'running',
  source_system text NOT NULL,
  started_at timestamptz NOT NULL,
  finished_at timestamptz,
  records_imported integer NOT NULL DEFAULT 0,
  error_message text,
  payload_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by text REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_collector_run_type
    CHECK (
      collector_type IN (
        'gitlab_daily_code_metric',
        'jenkins_release',
        'online_log_metric',
        'user_usage_metric',
        'user_feedback',
        'iteration_plan_suggestion'
      )
    ),
  CONSTRAINT ck_collector_run_status
    CHECK (status IN ('running', 'succeeded', 'failed', 'cancelled')),
  CONSTRAINT ck_collector_run_records
    CHECK (records_imported >= 0),
  CONSTRAINT ck_collector_run_source
    CHECK (length(trim(source_system)) > 0),
  CONSTRAINT ck_collector_run_finished_at
    CHECK (
      (status = 'running' AND finished_at IS NULL)
      OR (status <> 'running' AND finished_at IS NOT NULL)
    ),
  CONSTRAINT ck_collector_run_failed_error
    CHECK (status <> 'failed' OR length(trim(COALESCE(error_message, ''))) > 0)
);

CREATE INDEX IF NOT EXISTS idx_collector_runs_type_started
  ON collector_runs (collector_type, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_collector_runs_product_started
  ON collector_runs (product_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_collector_runs_status
  ON collector_runs (status, started_at DESC);
