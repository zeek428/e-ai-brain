ALTER TABLE IF EXISTS scheduled_jobs
  ADD COLUMN IF NOT EXISTS result_actions jsonb NOT NULL DEFAULT '[]'::jsonb;

CREATE TABLE IF NOT EXISTS code_inspection_reports (
  id text PRIMARY KEY,
  product_id text REFERENCES products(id) ON DELETE SET NULL,
  repository_id text REFERENCES product_git_repositories(id) ON DELETE SET NULL,
  repository jsonb NOT NULL DEFAULT '{}'::jsonb,
  scheduled_job_id text REFERENCES scheduled_jobs(id) ON DELETE SET NULL,
  scheduled_job_run_id text REFERENCES scheduled_job_runs(id) ON DELETE SET NULL,
  collector_run_id text REFERENCES collector_runs(id) ON DELETE SET NULL,
  plugin_invocation_log_id text REFERENCES plugin_invocation_logs(id) ON DELETE SET NULL,
  source_system text,
  branch text,
  commit_sha text,
  summary text NOT NULL DEFAULT '',
  risk_level text NOT NULL DEFAULT 'medium',
  finding_count integer NOT NULL DEFAULT 0,
  severe_finding_count integer NOT NULL DEFAULT 0,
  status text NOT NULL DEFAULT 'completed',
  result_actions jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_bug_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  notification_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_code_inspection_reports_risk_level CHECK (
    risk_level IN ('low', 'medium', 'high', 'critical')
  ),
  CONSTRAINT ck_code_inspection_reports_status CHECK (
    status IN ('completed', 'failed', 'partial')
  )
);

CREATE INDEX IF NOT EXISTS idx_code_inspection_reports_product_created
  ON code_inspection_reports(product_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_code_inspection_reports_repository_created
  ON code_inspection_reports(repository_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_code_inspection_reports_risk_created
  ON code_inspection_reports(risk_level, created_at DESC);

CREATE TABLE IF NOT EXISTS code_inspection_findings (
  id text PRIMARY KEY,
  report_id text NOT NULL REFERENCES code_inspection_reports(id) ON DELETE CASCADE,
  rule_id text,
  category text NOT NULL DEFAULT 'quality',
  severity text NOT NULL DEFAULT 'medium',
  title text NOT NULL,
  description text NOT NULL DEFAULT '',
  file_path text NOT NULL DEFAULT '',
  line_number integer,
  recommendation text NOT NULL DEFAULT '',
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_bug_id text REFERENCES bugs(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_code_inspection_findings_severity CHECK (
    severity IN ('info', 'low', 'medium', 'high', 'critical')
  )
);

CREATE INDEX IF NOT EXISTS idx_code_inspection_findings_report_severity
  ON code_inspection_findings(report_id, severity);

CREATE INDEX IF NOT EXISTS idx_code_inspection_findings_file
  ON code_inspection_findings(file_path);

CREATE TABLE IF NOT EXISTS code_inspection_notifications (
  id text PRIMARY KEY,
  report_id text NOT NULL REFERENCES code_inspection_reports(id) ON DELETE CASCADE,
  channel text NOT NULL,
  target text,
  status text NOT NULL DEFAULT 'recorded',
  message text NOT NULL DEFAULT '',
  request_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  response_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_code_inspection_notifications_channel CHECK (
    channel IN ('email', 'dingtalk', 'webhook')
  ),
  CONSTRAINT ck_code_inspection_notifications_status CHECK (
    status IN ('failed', 'recorded', 'sent')
  )
);

CREATE INDEX IF NOT EXISTS idx_code_inspection_notifications_report
  ON code_inspection_notifications(report_id, created_at ASC);

INSERT INTO permissions (code, name, category, description, risk_level, is_system, status)
VALUES
  ('code_inspection.read', '查看代码审查', 'devops', '查看定期仓库质量、安全和规范巡检报告。', 'normal', true, 'active')
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
  ('code_inspection.reports', '代码审查', '/governance/code-inspections', 'governance', 'page', 'CodeOutlined', 54, '["code_inspection.read"]'::jsonb, true, 'active')
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

WITH role_codes AS (
  SELECT id, code FROM roles WHERE code IN ('admin', 'product_owner', 'rd_owner')
)
INSERT INTO role_permissions (role_id, permission_code)
SELECT role_codes.id, 'code_inspection.read'
FROM role_codes
ON CONFLICT (role_id, permission_code) DO UPDATE SET
  updated_at = now();

WITH role_codes AS (
  SELECT id, code FROM roles WHERE code IN ('admin', 'product_owner', 'rd_owner')
)
INSERT INTO role_menu_grants (role_id, menu_code)
SELECT role_codes.id, 'code_inspection.reports'
FROM role_codes
ON CONFLICT (role_id, menu_code) DO UPDATE SET
  updated_at = now();
