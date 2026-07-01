CREATE TABLE IF NOT EXISTS integration_plugins (
  id text PRIMARY KEY,
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  description text,
  protocol text NOT NULL,
  category text NOT NULL DEFAULT 'general',
  risk_level text NOT NULL DEFAULT 'medium',
  status text NOT NULL DEFAULT 'active',
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_integration_plugins_protocol CHECK (
    protocol IN (
      'http',
      'internal_read_model',
      'mcp_http',
      'mcp_stdio',
      'runner_polling',
      'runner_websocket'
    )
  ),
  CONSTRAINT ck_integration_plugins_status CHECK (status IN ('active', 'disabled', 'draft'))
);

CREATE INDEX IF NOT EXISTS idx_integration_plugins_protocol_status
  ON integration_plugins(protocol, status);

CREATE TABLE IF NOT EXISTS plugin_connections (
  id text PRIMARY KEY,
  plugin_id text NOT NULL REFERENCES integration_plugins(id) ON DELETE CASCADE,
  name text NOT NULL,
  environment text NOT NULL DEFAULT 'default',
  endpoint_url text NOT NULL,
  auth_type text NOT NULL DEFAULT 'none',
  auth_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  request_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  last_test_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  test_history jsonb NOT NULL DEFAULT '[]'::jsonb,
  timeout_seconds integer NOT NULL DEFAULT 30,
  max_retries integer NOT NULL DEFAULT 0,
  status text NOT NULL DEFAULT 'active',
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_plugin_connections_auth_type CHECK (
    auth_type IN ('none', 'bearer', 'api_key_header', 'basic')
  ),
  CONSTRAINT ck_plugin_connections_status CHECK (status IN ('active', 'disabled', 'draft'))
);

CREATE INDEX IF NOT EXISTS idx_plugin_connections_plugin_status
  ON plugin_connections(plugin_id, status);

CREATE TABLE IF NOT EXISTS plugin_actions (
  id text PRIMARY KEY,
  plugin_id text NOT NULL REFERENCES integration_plugins(id) ON DELETE CASCADE,
  connection_id text REFERENCES plugin_connections(id) ON DELETE SET NULL,
  code text NOT NULL,
  name text NOT NULL,
  description text,
  action_type text NOT NULL,
  input_schema jsonb NOT NULL DEFAULT '{}'::jsonb,
  output_schema jsonb NOT NULL DEFAULT '{}'::jsonb,
  request_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  result_mapping jsonb NOT NULL DEFAULT '{}'::jsonb,
  requires_human_review boolean NOT NULL DEFAULT false,
  status text NOT NULL DEFAULT 'active',
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (plugin_id, code),
  CONSTRAINT ck_plugin_actions_action_type CHECK (action_type IN ('http_request', 'mcp_tool')),
  CONSTRAINT ck_plugin_actions_status CHECK (status IN ('active', 'disabled', 'draft'))
);

CREATE INDEX IF NOT EXISTS idx_plugin_actions_plugin_status
  ON plugin_actions(plugin_id, status);

CREATE TABLE IF NOT EXISTS plugin_invocation_logs (
  id text PRIMARY KEY,
  plugin_id text NOT NULL REFERENCES integration_plugins(id) ON DELETE CASCADE,
  connection_id text REFERENCES plugin_connections(id) ON DELETE SET NULL,
  action_id text NOT NULL REFERENCES plugin_actions(id) ON DELETE CASCADE,
  scheduled_job_id text REFERENCES scheduled_jobs(id) ON DELETE SET NULL,
  scheduled_job_run_id text REFERENCES scheduled_job_runs(id) ON DELETE SET NULL,
  trigger_type text NOT NULL DEFAULT 'manual',
  status text NOT NULL,
  request_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  response_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  latency_ms integer NOT NULL DEFAULT 0,
  error_code text,
  error_message text,
  trace_id text,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_plugin_invocation_logs_status CHECK (status IN ('failed', 'succeeded'))
);

CREATE INDEX IF NOT EXISTS idx_plugin_invocation_logs_action_created
  ON plugin_invocation_logs(action_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_plugin_invocation_logs_scheduled_job
  ON plugin_invocation_logs(scheduled_job_id, created_at DESC);

ALTER TABLE scheduled_jobs
  ADD COLUMN IF NOT EXISTS plugin_action_id text REFERENCES plugin_actions(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS plugin_connection_id text REFERENCES plugin_connections(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS plugin_input_mapping jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS plugin_output_mapping jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE scheduled_job_runs
  ADD COLUMN IF NOT EXISTS resolved_plugin_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS plugin_invocation_log_id text REFERENCES plugin_invocation_logs(id) ON DELETE SET NULL;

INSERT INTO permissions (code, name, category, description, risk_level, is_system, status)
VALUES
  ('system.plugins.manage', '管理集成插件', 'system', '维护三方系统插件、连接、动作和调用日志。', 'high', true, 'active')
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
  ('system.plugins', '插件管理', '/tasks/plugins', 'task', 'page', 'ApiOutlined', 24, '["system.plugins.manage"]'::jsonb, true, 'active')
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
SELECT admin_role.id, 'system.plugins.manage'
FROM admin_role
ON CONFLICT (role_id, permission_code) DO UPDATE SET
  updated_at = now();

WITH admin_role AS (
  SELECT id FROM roles WHERE code = 'admin'
)
INSERT INTO role_menu_grants (role_id, menu_code)
SELECT admin_role.id, 'system.plugins'
FROM admin_role
ON CONFLICT (role_id, menu_code) DO UPDATE SET
  updated_at = now();
