INSERT INTO permissions (code, name, category, description, risk_level, is_system, status)
VALUES
  (
    'system.internal_data_source.detail',
    '查看内部数据源详情字段',
    'system',
    '允许内部数据源 detail 模式返回受字段权限保护的详情字段。',
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

INSERT INTO role_permissions (role_id, permission_code, granted_by)
SELECT id, 'system.internal_data_source.detail', 'user_admin'
FROM roles
WHERE code = 'admin'
ON CONFLICT (role_id, permission_code) DO UPDATE SET
  granted_by = EXCLUDED.granted_by,
  updated_at = now();

UPDATE role_definitions
SET
  permissions = (
    SELECT jsonb_agg(permission_code ORDER BY permission_code)
    FROM (
      SELECT DISTINCT permission_code
      FROM jsonb_array_elements_text(
        role_definitions.permissions || '["system.internal_data_source.detail"]'::jsonb
      ) AS permission_values(permission_code)
    ) AS merged_permissions
  ),
  updated_at = now()
WHERE code = 'admin';
