CREATE TABLE IF NOT EXISTS rd_task_executor_policies (
  id text PRIMARY KEY,
  name text NOT NULL,
  brain_app_id text NOT NULL DEFAULT 'rd_brain',
  product_id text REFERENCES products(id) ON DELETE SET NULL,
  task_type text NOT NULL,
  executor_type text NOT NULL,
  runner_id text REFERENCES ai_executor_runners(id) ON DELETE SET NULL,
  repository_id text REFERENCES product_git_repositories(id) ON DELETE SET NULL,
  workspace_root text NOT NULL DEFAULT '',
  branch text,
  instruction_template text NOT NULL,
  output_contract jsonb NOT NULL DEFAULT '{}'::jsonb,
  timeout_seconds integer NOT NULL DEFAULT 1800,
  priority integer NOT NULL DEFAULT 100,
  status text NOT NULL DEFAULT 'active',
  code_change_review_mode text NOT NULL DEFAULT 'manual_review',
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_rd_task_executor_policies_executor_type CHECK (
    executor_type IN ('codex', 'claude', 'openclaw')
  ),
  CONSTRAINT ck_rd_task_executor_policies_status CHECK (status IN ('active', 'disabled')),
  CONSTRAINT ck_rd_task_executor_policies_code_change_review_mode CHECK (
    code_change_review_mode IN ('manual_review', 'auto_commit')
  )
);

CREATE INDEX IF NOT EXISTS idx_rd_task_executor_policies_match
  ON rd_task_executor_policies(brain_app_id, product_id, task_type, status, priority ASC);

ALTER TABLE IF EXISTS ai_executor_tasks
  ADD COLUMN IF NOT EXISTS ai_task_id text REFERENCES ai_tasks(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_ai_executor_tasks_ai_task
  ON ai_executor_tasks(ai_task_id, created_at DESC);

INSERT INTO permissions (code, name, category, description, risk_level, is_system, status)
VALUES
  ('delivery.rd_executor_policies.manage', '管理研发执行器策略', 'delivery', '维护研发任务匹配 Codex、Claude Code、OpenClaw 执行器的策略。', 'high', true, 'active')
ON CONFLICT (code) DO NOTHING;

INSERT INTO menu_resources (
  code, name, path, parent_code, menu_type, icon, sort_order,
  required_permissions, is_system, status
)
VALUES
  ('delivery.rd_executor_policies', '研发执行器策略', '/delivery/rd-executor-policies', 'delivery', 'page', 'ControlOutlined', 34, '["delivery.rd_executor_policies.manage"]'::jsonb, true, 'active')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  path = EXCLUDED.path,
  parent_code = EXCLUDED.parent_code,
  menu_type = EXCLUDED.menu_type,
  icon = EXCLUDED.icon,
  sort_order = EXCLUDED.sort_order,
  required_permissions = EXCLUDED.required_permissions,
  is_system = EXCLUDED.is_system,
  status = EXCLUDED.status;

INSERT INTO role_permissions (role_id, permission_code, granted_by)
SELECT id, 'delivery.rd_executor_policies.manage', 'user_admin'
FROM roles
WHERE code IN ('admin', 'rd_owner')
ON CONFLICT (role_id, permission_code) DO UPDATE SET
  granted_by = EXCLUDED.granted_by,
  updated_at = now();

INSERT INTO role_menu_grants (role_id, menu_code, granted_by)
SELECT id, 'delivery.rd_executor_policies', 'user_admin'
FROM roles
WHERE code IN ('admin', 'rd_owner')
ON CONFLICT (role_id, menu_code) DO UPDATE SET
  granted_by = EXCLUDED.granted_by,
  updated_at = now();

UPDATE role_definitions
SET permissions = (
  SELECT jsonb_agg(DISTINCT item ORDER BY item)
  FROM jsonb_array_elements_text(
    role_definitions.permissions || '["delivery.rd_executor_policies.manage"]'::jsonb
  ) AS item
)
WHERE code IN ('admin', 'rd_owner');
