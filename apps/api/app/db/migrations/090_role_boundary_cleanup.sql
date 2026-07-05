DELETE FROM role_permissions
WHERE role_id = (SELECT id FROM roles WHERE code = 'viewer')
  AND permission_code IN ('devops.read', 'insight.read');

DELETE FROM role_permissions
WHERE role_id = (SELECT id FROM roles WHERE code = 'reviewer')
  AND permission_code = 'audit.read';

DELETE FROM role_menu_grants
WHERE role_id = (SELECT id FROM roles WHERE code = 'viewer')
  AND menu_code IN ('devops.metrics', 'insight.center');

DELETE FROM role_menu_grants
WHERE role_id = (SELECT id FROM roles WHERE code = 'reviewer')
  AND menu_code IN ('governance', 'audit.events');

UPDATE role_definitions
SET
  menu_scope = COALESCE((
    SELECT jsonb_agg(scope_item ORDER BY scope_item)
    FROM jsonb_array_elements_text(menu_scope) AS menu_values(scope_item)
    WHERE scope_item NOT IN ('日志监控', '用户洞察')
  ), '[]'::jsonb),
  permissions = COALESCE((
    SELECT jsonb_agg(permission_code ORDER BY permission_code)
    FROM jsonb_array_elements_text(permissions) AS permission_values(permission_code)
    WHERE permission_code NOT IN ('devops.read', 'insight.read')
  ), '[]'::jsonb),
  updated_at = now()
WHERE code = 'viewer';

UPDATE role_definitions
SET
  menu_scope = COALESCE((
    SELECT jsonb_agg(scope_item ORDER BY scope_item)
    FROM jsonb_array_elements_text(menu_scope) AS menu_values(scope_item)
    WHERE scope_item NOT IN ('审计与运行')
  ), '[]'::jsonb),
  permissions = COALESCE((
    SELECT jsonb_agg(permission_code ORDER BY permission_code)
    FROM jsonb_array_elements_text(permissions) AS permission_values(permission_code)
    WHERE permission_code <> 'audit.read'
  ), '[]'::jsonb),
  updated_at = now()
WHERE code = 'reviewer';
