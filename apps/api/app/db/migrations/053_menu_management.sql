INSERT INTO permissions (code, name, category, description, risk_level, is_system, status)
VALUES
  ('system.menus.read', '查看菜单', 'system', '查看系统菜单资源、路由入口和访问权限点配置。', 'normal', true, 'active'),
  ('system.menus.manage', '管理菜单', 'system', '创建、编辑、停用和排序系统菜单资源。', 'high', true, 'active')
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
    'system.menus',
    '菜单管理',
    '/system/menus',
    'system',
    'page',
    'MenuOutlined',
    63,
    '["system.menus.manage"]'::jsonb,
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
SET sort_order = 64, updated_at = now()
WHERE code = 'system.model_gateway' AND sort_order = 63;

WITH admin_role AS (
  SELECT id FROM roles WHERE code = 'admin'
),
admin_permissions(permission_code) AS (
  VALUES ('system.menus.read'), ('system.menus.manage')
)
INSERT INTO role_permissions (role_id, permission_code, granted_by)
SELECT admin_role.id, admin_permissions.permission_code, 'user_admin'
FROM admin_role
CROSS JOIN admin_permissions
ON CONFLICT (role_id, permission_code) DO UPDATE SET
  granted_by = EXCLUDED.granted_by,
  updated_at = now();

WITH admin_role AS (
  SELECT id FROM roles WHERE code = 'admin'
)
INSERT INTO role_menu_grants (role_id, menu_code, granted_by)
SELECT admin_role.id, 'system.menus', 'user_admin'
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
        || '["system.menus.read", "system.menus.manage"]'::jsonb
      ) AS permission_values(permission_code)
    ) AS merged_permissions
  ),
  updated_at = now()
WHERE code = 'admin';
