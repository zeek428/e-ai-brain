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
VALUES (
  'system.execution_resources',
  '执行资源授权',
  '/system/execution-resources',
  'system',
  'page',
  'ClusterOutlined',
  69,
  '["system.settings.manage"]'::jsonb,
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

INSERT INTO role_menu_grants (role_id, menu_code, granted_by)
SELECT roles.id, 'system.execution_resources', 'user_admin'
FROM roles
WHERE roles.code = 'admin'
ON CONFLICT (role_id, menu_code) DO UPDATE SET
  granted_by = EXCLUDED.granted_by,
  updated_at = now();
