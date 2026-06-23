INSERT INTO permissions (code, name, category, description, risk_level, is_system, status)
VALUES
  (
    'diagnostics.execution_traces.read',
    '查看执行诊断',
    'diagnostics',
    '查看定时作业、插件调用、Runner、模型网关、代码巡检和审计事件聚合后的执行链路。',
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
  (
    'diagnostics.execution_traces',
    '执行诊断',
    '/governance/execution-traces',
    'governance',
    'page',
    'NodeIndexOutlined',
    54,
    '["diagnostics.execution_traces.read"]'::jsonb,
    true,
    'active'
  )
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

UPDATE menu_resources
SET sort_order = 55, updated_at = now()
WHERE code = 'code_inspection.reports' AND sort_order <= 54;

WITH admin_role AS (
  SELECT id FROM roles WHERE code = 'admin'
)
INSERT INTO role_permissions (role_id, permission_code, granted_by)
SELECT admin_role.id, 'diagnostics.execution_traces.read', 'user_admin'
FROM admin_role
ON CONFLICT (role_id, permission_code) DO UPDATE SET
  granted_by = EXCLUDED.granted_by,
  updated_at = now();

WITH admin_role AS (
  SELECT id FROM roles WHERE code = 'admin'
)
INSERT INTO role_menu_grants (role_id, menu_code, granted_by)
SELECT admin_role.id, 'diagnostics.execution_traces', 'user_admin'
FROM admin_role
ON CONFLICT (role_id, menu_code) DO UPDATE SET
  granted_by = EXCLUDED.granted_by,
  updated_at = now();

UPDATE role_definitions
SET
  permissions = (
    SELECT jsonb_agg(permission_code ORDER BY permission_code)
    FROM (
      SELECT DISTINCT permission_code
      FROM jsonb_array_elements_text(
        role_definitions.permissions
        || '["diagnostics.execution_traces.read"]'::jsonb
      ) AS permission_values(permission_code)
    ) AS merged_permissions
  ),
  updated_at = now()
WHERE code = 'admin';
