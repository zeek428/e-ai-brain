INSERT INTO role_permissions (role_id, permission_code)
SELECT roles.id, permissions.code
FROM roles
JOIN permissions ON permissions.code = 'product.read'
WHERE roles.code = 'viewer'
ON CONFLICT (role_id, permission_code) DO UPDATE SET
  updated_at = now();

INSERT INTO role_menu_grants (role_id, menu_code)
SELECT roles.id, menu_resources.code
FROM roles
JOIN menu_resources ON menu_resources.code IN ('product.assets', 'product.products')
WHERE roles.code = 'viewer'
ON CONFLICT (role_id, menu_code) DO UPDATE SET
  updated_at = now();

UPDATE role_definitions
SET
  menu_scope = (
    SELECT COALESCE(jsonb_agg(scope_item ORDER BY sort_order), '[]'::jsonb)
    FROM (
      SELECT DISTINCT ON (scope_item) scope_item, sort_order
      FROM (
        SELECT jsonb_array_elements_text(menu_scope) AS scope_item, 1 AS sort_order
        UNION ALL
        SELECT '产品管理', 2
      ) AS menu_values
      ORDER BY scope_item, sort_order
    ) AS deduped_menu_values
  ),
  permissions = (
    SELECT COALESCE(jsonb_agg(permission_code ORDER BY sort_order), '[]'::jsonb)
    FROM (
      SELECT DISTINCT ON (permission_code) permission_code, sort_order
      FROM (
        SELECT jsonb_array_elements_text(permissions) AS permission_code, 1 AS sort_order
        UNION ALL
        SELECT 'product.read', 2
      ) AS permission_values
      ORDER BY permission_code, sort_order
    ) AS deduped_permission_values
  ),
  updated_at = now()
WHERE code = 'viewer';
