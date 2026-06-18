INSERT INTO permissions (code, name, category, description, risk_level, is_system, status)
VALUES
  (
    'system.scheduled_jobs.run',
    '执行定时作业',
    'system',
    '允许手动触发定时作业运行并查看运行追踪，不包含创建、编辑、删除作业配置。',
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

WITH target_roles AS (
  SELECT id, code
  FROM roles
  WHERE code IN ('admin', 'product_owner', 'rd_owner', 'test_owner', 'tester', 'release_owner')
)
INSERT INTO role_permissions (role_id, permission_code)
SELECT target_roles.id, 'system.scheduled_jobs.run'
FROM target_roles
ON CONFLICT (role_id, permission_code) DO UPDATE SET
  updated_at = now();

UPDATE role_definitions
SET
  permissions = (
    SELECT jsonb_agg(permission_code ORDER BY permission_code)
    FROM (
      SELECT DISTINCT permission_code
      FROM jsonb_array_elements_text(
        role_definitions.permissions || '["system.scheduled_jobs.run"]'::jsonb
      ) AS permission_values(permission_code)
    ) AS merged_permissions
  ),
  updated_at = now()
WHERE code IN ('admin', 'product_owner', 'rd_owner', 'test_owner', 'tester', 'release_owner');
