ALTER TABLE IF EXISTS integration_plugins
  DROP CONSTRAINT IF EXISTS ck_integration_plugins_protocol;

ALTER TABLE IF EXISTS integration_plugins
  ADD CONSTRAINT ck_integration_plugins_protocol CHECK (
    protocol IN (
      'http',
      'internal_read_model',
      'mcp_http',
      'mcp_streamable_http',
      'mcp_stdio',
      'runner_polling',
      'runner_websocket'
    )
  );

UPDATE integration_plugins
SET
  protocol = 'runner_polling',
  description = '官方标准 AI 执行器插件，用于通过受控 Runner 向 Codex、Claude、Hermes、OpenClaw 等执行器下达指令、等待执行结果并同步回写。',
  updated_at = now()
WHERE code = 'ai_executor';

CREATE TABLE IF NOT EXISTS ai_executor_runners (
  id text PRIMARY KEY,
  name text NOT NULL,
  protocol text NOT NULL DEFAULT 'runner_polling',
  endpoint_url text NOT NULL DEFAULT 'runner://local',
  executor_types jsonb NOT NULL DEFAULT '[]'::jsonb,
  workspace_roots jsonb NOT NULL DEFAULT '[]'::jsonb,
  token_hash text NOT NULL,
  heartbeat_timeout_seconds integer NOT NULL DEFAULT 120,
  max_concurrent_tasks integer NOT NULL DEFAULT 1,
  status text NOT NULL DEFAULT 'active',
  last_heartbeat_at timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_ai_executor_runners_protocol CHECK (
    protocol IN ('runner_polling', 'runner_websocket', 'mcp_http', 'mcp_stdio')
  ),
  CONSTRAINT ck_ai_executor_runners_status CHECK (status IN ('active', 'disabled', 'offline'))
);

CREATE INDEX IF NOT EXISTS idx_ai_executor_runners_status
  ON ai_executor_runners(status, updated_at DESC);

CREATE TABLE IF NOT EXISTS ai_executor_tasks (
  id text PRIMARY KEY,
  runner_id text REFERENCES ai_executor_runners(id) ON DELETE SET NULL,
  plugin_invocation_log_id text REFERENCES plugin_invocation_logs(id) ON DELETE SET NULL,
  scheduled_job_id text REFERENCES scheduled_jobs(id) ON DELETE SET NULL,
  scheduled_job_run_id text REFERENCES scheduled_job_runs(id) ON DELETE SET NULL,
  executor_type text NOT NULL,
  instruction text NOT NULL,
  workspace_root text NOT NULL,
  timeout_seconds integer NOT NULL DEFAULT 1800,
  input_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  request_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  result_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  logs jsonb NOT NULL DEFAULT '[]'::jsonb,
  status text NOT NULL DEFAULT 'queued',
  error_code text,
  error_message text,
  claimed_at timestamptz,
  finished_at timestamptz,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_ai_executor_tasks_executor_type CHECK (
    executor_type IN ('codex', 'claude', 'hermes', 'openclaw')
  ),
  CONSTRAINT ck_ai_executor_tasks_status CHECK (
    status IN ('queued', 'claimed', 'running', 'succeeded', 'failed', 'cancelled', 'timed_out')
  )
);

CREATE INDEX IF NOT EXISTS idx_ai_executor_tasks_runner_status
  ON ai_executor_tasks(runner_id, status, created_at ASC);

CREATE INDEX IF NOT EXISTS idx_ai_executor_tasks_scheduled_run
  ON ai_executor_tasks(scheduled_job_run_id, created_at DESC);
