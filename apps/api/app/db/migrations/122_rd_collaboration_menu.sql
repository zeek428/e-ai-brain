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
  'delivery.rd_collaboration',
  '研发协同',
  '/delivery/rd-collaboration',
  'delivery',
  'page',
  'ApartmentOutlined',
  36,
  '["delivery.rd_collaboration.read"]'::jsonb,
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

WITH role_menu_seed(role_code, menu_code) AS (
  VALUES
    ('admin', 'delivery.rd_collaboration')
)
INSERT INTO role_menu_grants (role_id, menu_code, granted_by)
SELECT roles.id, role_menu_seed.menu_code, 'user_admin'
FROM role_menu_seed
JOIN roles ON roles.code = role_menu_seed.role_code
ON CONFLICT (role_id, menu_code) DO UPDATE SET
  granted_by = EXCLUDED.granted_by,
  updated_at = now();
