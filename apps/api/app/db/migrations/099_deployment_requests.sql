CREATE TABLE IF NOT EXISTS deployment_requests (
  id text PRIMARY KEY,
  product_id text NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  version_id text NOT NULL REFERENCES product_versions(id) ON DELETE CASCADE,
  title text NOT NULL,
  environment text NOT NULL DEFAULT 'prod',
  status text NOT NULL DEFAULT 'pending_ops',
  deploy_window_start timestamptz,
  deploy_window_end timestamptz,
  release_branch text,
  commit_sha text,
  artifact_version text,
  release_readiness_task_id text REFERENCES ai_tasks(id),
  rollback_plan text,
  risk_level text NOT NULL DEFAULT 'medium',
  gate_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  assigned_ops_user text,
  approved_by text,
  started_at timestamptz,
  finished_at timestamptz,
  failure_reason text,
  created_by text NOT NULL REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_deployment_request_status
    CHECK (
      status IN (
        'draft',
        'pending_ops',
        'approved',
        'deploying',
        'succeeded',
        'failed',
        'cancelled',
        'rolled_back'
      )
    ),
  CONSTRAINT ck_deployment_request_risk_level
    CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
  CONSTRAINT ck_deployment_request_window
    CHECK (
      deploy_window_start IS NULL
      OR deploy_window_end IS NULL
      OR deploy_window_end >= deploy_window_start
    )
);

CREATE TABLE IF NOT EXISTS deployment_request_requirements (
  deployment_request_id text NOT NULL REFERENCES deployment_requests(id) ON DELETE CASCADE,
  requirement_id text NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (deployment_request_id, requirement_id)
);

CREATE TABLE IF NOT EXISTS deployment_runs (
  id text PRIMARY KEY,
  deployment_request_id text NOT NULL REFERENCES deployment_requests(id) ON DELETE CASCADE,
  executor_type text NOT NULL DEFAULT 'manual',
  external_job_name text,
  external_build_id text,
  status text NOT NULL DEFAULT 'running',
  log_url text,
  started_at timestamptz,
  finished_at timestamptz,
  failure_reason text,
  created_by text NOT NULL REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_deployment_run_status
    CHECK (status IN ('running', 'success', 'failed', 'canceled', 'rolled_back')),
  CONSTRAINT ck_deployment_run_time
    CHECK (
      started_at IS NULL
      OR finished_at IS NULL
      OR finished_at >= started_at
    )
);

ALTER TABLE jenkins_release_records
  ADD COLUMN IF NOT EXISTS deployment_request_id text REFERENCES deployment_requests(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_deployment_requests_product_status
  ON deployment_requests (product_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_deployment_requests_version_status
  ON deployment_requests (version_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_deployment_request_requirements_requirement
  ON deployment_request_requirements (requirement_id, deployment_request_id);

CREATE INDEX IF NOT EXISTS idx_deployment_runs_request_time
  ON deployment_runs (deployment_request_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_jenkins_release_deployment_request
  ON jenkins_release_records (deployment_request_id);

INSERT INTO permissions (code, name, category, description, risk_level, is_system, status)
VALUES
  ('deployment.read', '查看部署单', 'release', '查看产品范围内的部署申请、执行和结果。', 'normal', true, 'active'),
  ('deployment.create', '发起部署单', 'release', '从测试完成或待发布需求发起运维部署申请。', 'high', true, 'active'),
  ('deployment.execute', '执行部署', 'release', '接单、执行、完成、失败或回滚部署单。', 'high', true, 'active'),
  ('deployment.cancel', '取消部署单', 'release', '取消尚未完成的部署单。', 'high', true, 'active')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  category = EXCLUDED.category,
  description = EXCLUDED.description,
  risk_level = EXCLUDED.risk_level,
  is_system = EXCLUDED.is_system,
  status = EXCLUDED.status;

WITH role_permission_seed(role_code, permission_code) AS (
  VALUES
    ('admin', 'deployment.read'),
    ('admin', 'deployment.create'),
    ('admin', 'deployment.execute'),
    ('admin', 'deployment.cancel'),
    ('product_owner', 'deployment.read'),
    ('product_owner', 'deployment.create'),
    ('product_owner', 'deployment.cancel'),
    ('rd_owner', 'deployment.read'),
    ('rd_owner', 'deployment.create'),
    ('rd_owner', 'deployment.cancel'),
    ('test_owner', 'deployment.read'),
    ('test_owner', 'deployment.create'),
    ('tester', 'deployment.read'),
    ('release_owner', 'deployment.read'),
    ('release_owner', 'deployment.create'),
    ('release_owner', 'deployment.execute'),
    ('release_owner', 'deployment.cancel')
)
INSERT INTO role_permissions (role_id, permission_code)
SELECT roles.id, role_permission_seed.permission_code
FROM role_permission_seed
JOIN roles ON roles.code = role_permission_seed.role_code
ON CONFLICT (role_id, permission_code) DO UPDATE SET
  updated_at = now();
