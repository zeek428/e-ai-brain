CREATE TABLE IF NOT EXISTS deployment_schemes (
  id text PRIMARY KEY,
  product_id text NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  code text NOT NULL,
  name text NOT NULL,
  environment text NOT NULL DEFAULT 'prod',
  deployment_method text NOT NULL DEFAULT 'manual',
  executor_channel text NOT NULL DEFAULT 'manual',
  runner_id text REFERENCES ai_executor_runners(id) ON DELETE RESTRICT,
  target_code text,
  jenkins_connection_id text REFERENCES plugin_connections(id) ON DELETE RESTRICT,
  jenkins_job_name text,
  timeout_seconds integer NOT NULL DEFAULT 1800,
  config_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  is_default boolean NOT NULL DEFAULT false,
  status text NOT NULL DEFAULT 'active',
  version integer NOT NULL DEFAULT 1,
  created_by text REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_deployment_schemes_product_code UNIQUE (product_id, code),
  CONSTRAINT ck_deployment_schemes_method CHECK (
    deployment_method IN ('manual', 'ssh', 'docker', 'jenkins')
  ),
  CONSTRAINT ck_deployment_schemes_channel CHECK (
    executor_channel IN ('manual', 'runner', 'integration')
  ),
  CONSTRAINT ck_deployment_schemes_status CHECK (
    status IN ('active', 'disabled')
  ),
  CONSTRAINT ck_deployment_schemes_timeout CHECK (timeout_seconds BETWEEN 30 AND 86400),
  CONSTRAINT ck_deployment_schemes_version CHECK (version > 0),
  CONSTRAINT ck_deployment_schemes_binding CHECK (
    (
      deployment_method = 'manual'
      AND executor_channel = 'manual'
      AND runner_id IS NULL
      AND target_code IS NULL
      AND jenkins_connection_id IS NULL
      AND jenkins_job_name IS NULL
    )
    OR (
      deployment_method IN ('ssh', 'docker')
      AND executor_channel = 'runner'
      AND runner_id IS NOT NULL
      AND NULLIF(target_code, '') IS NOT NULL
      AND jenkins_connection_id IS NULL
      AND jenkins_job_name IS NULL
    )
    OR (
      deployment_method = 'jenkins'
      AND executor_channel = 'integration'
      AND runner_id IS NULL
      AND target_code IS NULL
      AND jenkins_connection_id IS NOT NULL
      AND NULLIF(jenkins_job_name, '') IS NOT NULL
    )
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_deployment_schemes_one_active_default
  ON deployment_schemes (product_id, environment)
  WHERE is_default = true AND status = 'active';

CREATE INDEX IF NOT EXISTS idx_deployment_schemes_product_environment
  ON deployment_schemes (product_id, environment, status, updated_at DESC);

ALTER TABLE deployment_requests
  ADD COLUMN IF NOT EXISTS deployment_scheme_id text
    REFERENCES deployment_schemes(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS deployment_method text NOT NULL DEFAULT 'manual',
  ADD COLUMN IF NOT EXISTS executor_channel text NOT NULL DEFAULT 'manual',
  ADD COLUMN IF NOT EXISTS scheme_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE deployment_requests
  DROP CONSTRAINT IF EXISTS ck_deployment_request_status;

ALTER TABLE deployment_requests
  ADD CONSTRAINT ck_deployment_request_status CHECK (
    status IN (
      'draft',
      'pending_ops',
      'approved',
      'deploying',
      'cancelling',
      'succeeded',
      'failed',
      'cancelled',
      'rolled_back'
    )
  );

ALTER TABLE deployment_runs
  ADD COLUMN IF NOT EXISTS deployment_method text NOT NULL DEFAULT 'manual',
  ADD COLUMN IF NOT EXISTS executor_channel text NOT NULL DEFAULT 'manual',
  ADD COLUMN IF NOT EXISTS runner_task_id text,
  ADD COLUMN IF NOT EXISTS plugin_invocation_log_id text
    REFERENCES plugin_invocation_logs(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS idempotency_key text,
  ADD COLUMN IF NOT EXISTS external_queue_url text,
  ADD COLUMN IF NOT EXISTS external_build_url text,
  ADD COLUMN IF NOT EXISTS execution_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS logs jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS next_sync_at timestamptz,
  ADD COLUMN IF NOT EXISTS sync_attempts integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS sync_lease_owner text,
  ADD COLUMN IF NOT EXISTS sync_lease_until timestamptz;

ALTER TABLE deployment_runs
  DROP CONSTRAINT IF EXISTS ck_deployment_run_status;

ALTER TABLE deployment_runs
  ADD CONSTRAINT ck_deployment_run_status CHECK (
    status IN (
      'queued',
      'running',
      'cancelling',
      'success',
      'failed',
      'canceled',
      'cancelled',
      'rolled_back'
    )
  );

CREATE UNIQUE INDEX IF NOT EXISTS idx_deployment_runs_idempotency
  ON deployment_runs (idempotency_key)
  WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_deployment_runs_sync_due
  ON deployment_runs (next_sync_at, sync_lease_until)
  WHERE status IN ('queued', 'running', 'cancelling');

ALTER TABLE ai_executor_runners
  ADD COLUMN IF NOT EXISTS capabilities jsonb NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE ai_executor_tasks
  ADD COLUMN IF NOT EXISTS deployment_run_id text
    REFERENCES deployment_runs(id) ON DELETE SET NULL;

ALTER TABLE ai_executor_tasks
  DROP CONSTRAINT IF EXISTS ck_ai_executor_tasks_executor_type;

ALTER TABLE ai_executor_tasks
  ADD CONSTRAINT ck_ai_executor_tasks_executor_type CHECK (
    executor_type IN ('codex', 'claude', 'hermes', 'openclaw', 'deployment')
  );

ALTER TABLE ai_executor_tasks
  DROP CONSTRAINT IF EXISTS ck_ai_executor_tasks_status;

ALTER TABLE ai_executor_tasks
  ADD CONSTRAINT ck_ai_executor_tasks_status CHECK (
    status IN (
      'queued',
      'claimed',
      'running',
      'cancel_requested',
      'succeeded',
      'failed',
      'cancelled',
      'timed_out',
      'dead_letter'
    )
  );

ALTER TABLE deployment_runs
  DROP CONSTRAINT IF EXISTS fk_deployment_runs_runner_task;

ALTER TABLE deployment_runs
  ADD CONSTRAINT fk_deployment_runs_runner_task
    FOREIGN KEY (runner_task_id) REFERENCES ai_executor_tasks(id) ON DELETE SET NULL;

WITH deployment_environments AS (
  SELECT id AS product_id, 'prod'::text AS environment
  FROM products
  UNION
  SELECT product_id, environment
  FROM deployment_requests
)
INSERT INTO deployment_schemes (
  id, product_id, code, name, environment, deployment_method,
  executor_channel, timeout_seconds, config_json, is_default,
  status, version, created_at, updated_at
)
SELECT
  'deployment_scheme_' || substr(md5(product_id || ':' || environment || ':manual'), 1, 20),
  product_id,
  'default-manual-' || environment,
  CASE WHEN environment = 'prod' THEN '默认人工部署' ELSE '默认人工部署-' || environment END,
  environment,
  'manual',
  'manual',
  1800,
  '{}'::jsonb,
  true,
  'active',
  1,
  now(),
  now()
FROM deployment_environments deployment_environment
WHERE NOT EXISTS (
  SELECT 1
  FROM deployment_schemes existing_default
  WHERE existing_default.product_id = deployment_environment.product_id
    AND existing_default.environment = deployment_environment.environment
    AND existing_default.is_default = true
    AND existing_default.status = 'active'
)
ON CONFLICT (product_id, code) DO NOTHING;

UPDATE deployment_requests request
SET deployment_scheme_id = scheme.id,
    deployment_method = scheme.deployment_method,
    executor_channel = scheme.executor_channel,
    scheme_snapshot = jsonb_build_object(
      'id', scheme.id,
      'code', scheme.code,
      'name', scheme.name,
      'environment', scheme.environment,
      'deployment_method', scheme.deployment_method,
      'executor_channel', scheme.executor_channel,
      'timeout_seconds', scheme.timeout_seconds,
      'version', scheme.version
    )
FROM deployment_schemes scheme
WHERE request.deployment_scheme_id IS NULL
  AND scheme.product_id = request.product_id
  AND scheme.environment = request.environment
  AND scheme.is_default = true
  AND scheme.status = 'active';

UPDATE deployment_runs run
SET deployment_method = request.deployment_method,
    executor_channel = request.executor_channel
FROM deployment_requests request
WHERE run.deployment_request_id = request.id;

INSERT INTO permissions (code, name, category, description, risk_level, is_system, status)
VALUES (
  'deployment.scheme.manage',
  '管理部署方案',
  'release',
  '配置产品环境的人工、SSH、Docker 或 Jenkins 部署方案。',
  'high',
  true,
  'active'
)
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  category = EXCLUDED.category,
  description = EXCLUDED.description,
  risk_level = EXCLUDED.risk_level,
  is_system = EXCLUDED.is_system,
  status = EXCLUDED.status;

WITH deployment_scheme_role_permissions(role_code, permission_code) AS (
  VALUES
    ('admin', 'deployment.scheme.manage'),
    ('release_owner', 'deployment.scheme.manage')
)
INSERT INTO role_permissions (role_id, permission_code)
SELECT roles.id, deployment_scheme_role_permissions.permission_code
FROM deployment_scheme_role_permissions
JOIN roles ON roles.code = deployment_scheme_role_permissions.role_code
ON CONFLICT (role_id, permission_code) DO UPDATE SET
  updated_at = now();
