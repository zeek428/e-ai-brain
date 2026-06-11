CREATE TABLE IF NOT EXISTS ai_skills (
  id text PRIMARY KEY,
  code text NOT NULL,
  name text NOT NULL,
  version text NOT NULL DEFAULT '1.0.0',
  description text,
  prompt_template text NOT NULL,
  input_schema jsonb NOT NULL DEFAULT '{}'::jsonb,
  output_schema jsonb NOT NULL DEFAULT '{}'::jsonb,
  allowed_tools jsonb NOT NULL DEFAULT '[]'::jsonb,
  required_context jsonb NOT NULL DEFAULT '[]'::jsonb,
  source_type text NOT NULL DEFAULT 'inline',
  package_uri text,
  package_checksum text,
  package_entry text,
  package_files jsonb NOT NULL DEFAULT '[]'::jsonb,
  package_size_bytes integer NOT NULL DEFAULT 0,
  manifest jsonb NOT NULL DEFAULT '{}'::jsonb,
  risk_level text NOT NULL DEFAULT 'medium',
  requires_human_review boolean NOT NULL DEFAULT false,
  status text NOT NULL DEFAULT 'draft',
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (code, version),
  CONSTRAINT ck_ai_skills_status CHECK (status IN ('active', 'draft', 'disabled'))
);

ALTER TABLE IF EXISTS ai_skills
  ADD COLUMN IF NOT EXISTS source_type text NOT NULL DEFAULT 'inline',
  ADD COLUMN IF NOT EXISTS package_uri text,
  ADD COLUMN IF NOT EXISTS package_checksum text,
  ADD COLUMN IF NOT EXISTS package_entry text,
  ADD COLUMN IF NOT EXISTS package_files jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS package_size_bytes integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS manifest jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_ai_skills_status_code
  ON ai_skills(status, code);

CREATE TABLE IF NOT EXISTS ai_agents (
  id text PRIMARY KEY,
  brain_app_id text NOT NULL DEFAULT 'rd_brain',
  code text NOT NULL,
  name text NOT NULL,
  description text,
  model_gateway_config_id text REFERENCES model_gateway_configs(id) ON DELETE SET NULL,
  system_prompt text NOT NULL,
  default_skill_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  tool_policy jsonb NOT NULL DEFAULT '{}'::jsonb,
  execution_policy jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'active',
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (brain_app_id, code),
  CONSTRAINT ck_ai_agents_status CHECK (status IN ('active', 'disabled'))
);

CREATE INDEX IF NOT EXISTS idx_ai_agents_brain_status
  ON ai_agents(brain_app_id, status);

CREATE TABLE IF NOT EXISTS scheduled_jobs (
  id text PRIMARY KEY,
  name text NOT NULL,
  job_type text NOT NULL,
  source_system text NOT NULL,
  product_id text REFERENCES products(id) ON DELETE SET NULL,
  schedule_type text NOT NULL,
  cron_expression text,
  interval_seconds integer,
  timezone text NOT NULL DEFAULT 'Asia/Shanghai',
  enabled boolean NOT NULL DEFAULT true,
  execution_mode text NOT NULL,
  agent_id text REFERENCES ai_agents(id) ON DELETE SET NULL,
  skill_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  model_gateway_config_id text REFERENCES model_gateway_configs(id) ON DELETE SET NULL,
  config_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  max_retry_count integer NOT NULL DEFAULT 0,
  timeout_seconds integer NOT NULL DEFAULT 600,
  lock_ttl_seconds integer NOT NULL DEFAULT 900,
  status text NOT NULL DEFAULT 'active',
  next_run_at timestamptz,
  last_run_at timestamptz,
  last_success_at timestamptz,
  last_failure_at timestamptz,
  last_error_message text,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_scheduled_jobs_schedule_type CHECK (schedule_type IN ('cron', 'interval', 'manual')),
  CONSTRAINT ck_scheduled_jobs_execution_mode CHECK (execution_mode IN ('ai_assisted', 'ai_generated', 'deterministic')),
  CONSTRAINT ck_scheduled_jobs_status CHECK (status IN ('active', 'disabled'))
);

CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_due
  ON scheduled_jobs(enabled, next_run_at)
  WHERE enabled = true;

CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_type_status
  ON scheduled_jobs(job_type, status);

CREATE TABLE IF NOT EXISTS scheduled_job_runs (
  id text PRIMARY KEY,
  scheduled_job_id text NOT NULL REFERENCES scheduled_jobs(id) ON DELETE CASCADE,
  collector_run_id text REFERENCES collector_runs(id) ON DELETE SET NULL,
  trigger_type text NOT NULL DEFAULT 'manual',
  status text NOT NULL DEFAULT 'queued',
  scheduled_for timestamptz,
  started_at timestamptz,
  finished_at timestamptz,
  records_imported integer NOT NULL DEFAULT 0,
  error_code text,
  error_message text,
  config_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  resolved_agent_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  resolved_skill_snapshots jsonb NOT NULL DEFAULT '[]'::jsonb,
  resolved_prompt_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  tool_policy_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  result_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_scheduled_job_runs_status CHECK (
    status IN ('cancelled', 'failed', 'queued', 'running', 'skipped', 'succeeded')
  )
);

CREATE INDEX IF NOT EXISTS idx_scheduled_job_runs_job_started
  ON scheduled_job_runs(scheduled_job_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_scheduled_job_runs_status
  ON scheduled_job_runs(status, started_at DESC);

INSERT INTO permissions (code, name, category, description, risk_level, is_system, status)
VALUES
  ('system.ai_capabilities.manage', '管理 AI 能力配置', 'system', '维护 AI Agent、Skill、工具策略和模型绑定。', 'high', true, 'active'),
  ('system.scheduled_jobs.manage', '管理定时作业', 'system', '维护定时系统作业、手动触发运行并查看运行记录。', 'high', true, 'active')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  category = EXCLUDED.category,
  description = EXCLUDED.description,
  risk_level = EXCLUDED.risk_level,
  is_system = EXCLUDED.is_system,
  status = EXCLUDED.status,
  updated_at = now();

INSERT INTO menu_resources (
  code,
  name,
  path,
  parent_code,
  menu_type,
  icon,
  sort_order,
  required_permissions,
  is_system,
  status
)
VALUES
  ('system.ai_capabilities', 'AI 能力配置', '/tasks/ai-capabilities', 'task', 'page', 'RobotOutlined', 22, '["system.ai_capabilities.manage"]'::jsonb, true, 'active'),
  ('system.scheduled_jobs', '定时作业', '/tasks/scheduled-jobs', 'task', 'page', 'ClockCircleOutlined', 23, '["system.scheduled_jobs.manage"]'::jsonb, true, 'active')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  path = EXCLUDED.path,
  parent_code = EXCLUDED.parent_code,
  menu_type = EXCLUDED.menu_type,
  icon = EXCLUDED.icon,
  sort_order = EXCLUDED.sort_order,
  required_permissions = EXCLUDED.required_permissions,
  is_system = EXCLUDED.is_system,
  status = EXCLUDED.status,
  updated_at = now();

WITH admin_role AS (
  SELECT id FROM roles WHERE code = 'admin'
)
INSERT INTO role_permissions (role_id, permission_code)
SELECT admin_role.id, permission_code
FROM admin_role
CROSS JOIN (
  VALUES
    ('system.ai_capabilities.manage'),
    ('system.scheduled_jobs.manage')
) AS permissions(permission_code)
ON CONFLICT (role_id, permission_code) DO UPDATE SET
  updated_at = now();

WITH admin_role AS (
  SELECT id FROM roles WHERE code = 'admin'
)
INSERT INTO role_menu_grants (role_id, menu_code)
SELECT admin_role.id, menu_code
FROM admin_role
CROSS JOIN (
  VALUES
    ('system.ai_capabilities'),
    ('system.scheduled_jobs')
) AS menus(menu_code)
ON CONFLICT (role_id, menu_code) DO UPDATE SET
  updated_at = now();
