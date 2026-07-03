CREATE TABLE IF NOT EXISTS system_settings (
  setting_key text PRIMARY KEY,
  setting_value jsonb NOT NULL DEFAULT '{}'::jsonb,
  description text NOT NULL DEFAULT '',
  updated_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO permissions (code, name, category, description, risk_level, is_system, status)
VALUES
  (
    'system.settings.manage',
    '管理系统设置',
    'system',
    '查看和维护全局系统设置，例如系统管理员邮箱。',
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
    'system.settings',
    '系统设置',
    '/system/settings',
    'system',
    'page',
    'SettingOutlined',
    64,
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
SET sort_order = 65, updated_at = now()
WHERE code = 'system.model_gateway' AND sort_order < 65;

UPDATE menu_resources
SET sort_order = 66, updated_at = now()
WHERE code = 'system.assistant_action_references' AND sort_order < 66;

UPDATE menu_resources
SET sort_order = 67, updated_at = now()
WHERE code = 'org.departments' AND sort_order < 67;

WITH admin_role AS (
  SELECT id FROM roles WHERE code = 'admin'
)
INSERT INTO role_permissions (role_id, permission_code, granted_by)
SELECT admin_role.id, 'system.settings.manage', 'user_admin'
FROM admin_role
ON CONFLICT (role_id, permission_code) DO UPDATE SET
  granted_by = EXCLUDED.granted_by,
  updated_at = now();

WITH admin_role AS (
  SELECT id FROM roles WHERE code = 'admin'
)
INSERT INTO role_menu_grants (role_id, menu_code, granted_by)
SELECT admin_role.id, 'system.settings', 'user_admin'
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
        COALESCE(role_definitions.permissions, '[]'::jsonb) || '["system.settings.manage"]'::jsonb
      ) AS permission_values(permission_code)
    ) AS merged_permissions
  ),
  updated_at = now()
WHERE code = 'admin';
