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
    'governance.deployments',
    '运维部署',
    '/governance/deployments',
    'governance',
    'page',
    'CloudServerOutlined',
    52,
    '["deployment.read"]'::jsonb,
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
SET sort_order = CASE code
  WHEN 'insight.center' THEN 53
  WHEN 'audit.events' THEN 54
  WHEN 'diagnostics.execution_traces' THEN 55
  WHEN 'code_inspection.reports' THEN 56
  ELSE sort_order
END,
updated_at = now()
WHERE code IN (
  'insight.center',
  'audit.events',
  'diagnostics.execution_traces',
  'code_inspection.reports'
);

WITH role_menu_seed(role_code, menu_code) AS (
  VALUES
    ('admin', 'governance.deployments'),
    ('product_owner', 'governance.deployments'),
    ('rd_owner', 'governance.deployments'),
    ('release_owner', 'governance.deployments'),
    ('test_owner', 'governance.deployments'),
    ('tester', 'governance.deployments')
)
INSERT INTO role_menu_grants (role_id, menu_code, granted_by)
SELECT roles.id, role_menu_seed.menu_code, 'user_admin'
FROM role_menu_seed
JOIN roles ON roles.code = role_menu_seed.role_code
ON CONFLICT (role_id, menu_code) DO UPDATE SET
  granted_by = EXCLUDED.granted_by,
  updated_at = now();

WITH governance_role_seed(role_code) AS (
  VALUES
    ('product_owner'),
    ('test_owner'),
    ('tester')
)
INSERT INTO role_menu_grants (role_id, menu_code, granted_by)
SELECT roles.id, 'governance', 'user_admin'
FROM governance_role_seed
JOIN roles ON roles.code = governance_role_seed.role_code
ON CONFLICT (role_id, menu_code) DO UPDATE SET
  granted_by = EXCLUDED.granted_by,
  updated_at = now();
