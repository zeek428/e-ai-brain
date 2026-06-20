ALTER TABLE IF EXISTS assistant_conversations
  ADD COLUMN IF NOT EXISTS command_signature text,
  ADD COLUMN IF NOT EXISTS source_message_hash text,
  ADD COLUMN IF NOT EXISTS context_scope text;

CREATE INDEX IF NOT EXISTS idx_assistant_conversations_command_signature
  ON assistant_conversations(user_id, context_scope, command_signature, updated_at DESC)
  WHERE command_signature IS NOT NULL;

INSERT INTO permissions (code, name, category, description, risk_level, is_system, status)
VALUES
  (
    'assistant.action_references.manage',
    '管理 AI 助手 @ 能力',
    'assistant',
    '维护 AI 助手 @ 能力候选、启停、排序、灰度、模板版本和权限预览。',
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
  status = EXCLUDED.status;

INSERT INTO menu_resources (
  code, name, path, parent_code, menu_type, icon, sort_order,
  required_permissions, is_system, status
)
VALUES
  (
    'system.assistant_action_references',
    'AI助手 @ 能力',
    '/system/assistant-action-references',
    'system',
    'page',
    'RobotOutlined',
    65,
    '["assistant.action_references.manage"]'::jsonb,
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
  status = EXCLUDED.status;

INSERT INTO role_permissions (role_id, permission_code, granted_by)
SELECT r.id, p.code, 'user_admin'
FROM roles r
JOIN permissions p ON p.code = 'assistant.action_references.manage'
WHERE r.code = 'admin'
ON CONFLICT (role_id, permission_code) DO UPDATE SET
  updated_at = now();

INSERT INTO role_menu_grants (role_id, menu_code)
SELECT r.id, m.code
FROM roles r
JOIN menu_resources m ON m.code = 'system.assistant_action_references'
WHERE r.code = 'admin'
ON CONFLICT (role_id, menu_code) DO NOTHING;
