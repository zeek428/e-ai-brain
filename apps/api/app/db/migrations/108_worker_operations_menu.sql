INSERT INTO menu_resources (
  code, name, path, parent_code, menu_type, icon, sort_order,
  required_permissions, is_system, status
)
VALUES (
  'governance.worker_operations',
  'Worker 运维',
  '/governance/worker-operations',
  'governance',
  'page',
  'ClusterOutlined',
  56,
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

UPDATE menu_resources
SET sort_order = 57, updated_at = now()
WHERE code = 'code_inspection.reports';

INSERT INTO role_menu_grants (role_id, menu_code, granted_by)
SELECT id, 'governance.worker_operations', 'user_admin'
FROM roles
WHERE code = 'admin'
ON CONFLICT (role_id, menu_code) DO UPDATE SET
  granted_by = EXCLUDED.granted_by,
  updated_at = now();
