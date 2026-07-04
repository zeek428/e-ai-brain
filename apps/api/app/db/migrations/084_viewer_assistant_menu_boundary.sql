DELETE FROM role_permissions
WHERE role_id = (SELECT id FROM roles WHERE code = 'viewer')
  AND permission_code = 'assistant.chat';

DELETE FROM role_menu_grants
WHERE role_id = (SELECT id FROM roles WHERE code = 'viewer')
  AND menu_code IN ('assistant.chat', 'assistant.drafts');

UPDATE role_definitions
SET
  menu_scope = COALESCE((
    SELECT jsonb_agg(scope_item ORDER BY scope_item)
    FROM jsonb_array_elements_text(menu_scope) AS menu_values(scope_item)
    WHERE scope_item NOT IN ('AI 助手', '草案任务台', '草案工作台')
  ), '[]'::jsonb),
  permissions = COALESCE((
    SELECT jsonb_agg(permission_code ORDER BY permission_code)
    FROM jsonb_array_elements_text(permissions) AS permission_values(permission_code)
    WHERE permission_code <> 'assistant.chat'
  ), '[]'::jsonb),
  updated_at = now()
WHERE code = 'viewer';
