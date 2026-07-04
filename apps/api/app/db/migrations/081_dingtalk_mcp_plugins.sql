ALTER TABLE IF EXISTS integration_plugins
  DROP CONSTRAINT IF EXISTS ck_integration_plugins_protocol;

ALTER TABLE IF EXISTS integration_plugins
  ADD CONSTRAINT ck_integration_plugins_protocol CHECK (
    protocol IN (
      'http',
      'internal_read_model',
      'mcp_http',
      'mcp_streamable_http',
      'mcp_stdio',
      'runner_polling',
      'runner_websocket'
    )
  );

ALTER TABLE IF EXISTS plugin_connections
  DROP CONSTRAINT IF EXISTS ck_plugin_connections_auth_type;

ALTER TABLE IF EXISTS plugin_connections
  ADD CONSTRAINT ck_plugin_connections_auth_type CHECK (
    auth_type IN ('none', 'bearer', 'api_key_header', 'basic', 'url_key')
  );

INSERT INTO integration_plugins (
  id,
  code,
  name,
  description,
  protocol,
  category,
  risk_level,
  status,
  is_system,
  created_by
)
VALUES
  (
    'plugin_standard_dingtalk_aitable',
    'dingtalk_aitable',
    '钉钉 AI 表格',
    '钉钉官方 AI 表格 MCP 插件，用于查询 AI 表格记录作为定时作业输入。',
    'mcp_streamable_http',
    'business_system',
    'medium',
    'active',
    true,
    'system'
  ),
  (
    'plugin_standard_dingtalk_bot',
    'dingtalk_bot',
    '钉钉机器人消息',
    '钉钉官方机器人消息 MCP 插件，用于向用户发送作业结果和业务提醒。',
    'mcp_streamable_http',
    'collaboration',
    'high',
    'active',
    true,
    'system'
  ),
  (
    'plugin_standard_dingtalk_contact',
    'dingtalk_contact',
    '钉钉通讯录',
    '钉钉官方通讯录 MCP 插件，用于按关键词搜索用户和组织成员。',
    'mcp_streamable_http',
    'collaboration',
    'medium',
    'active',
    true,
    'system'
  ),
  (
    'plugin_standard_dingtalk_doc',
    'dingtalk_doc',
    '钉钉文档',
    '钉钉官方文档 MCP 插件，用于搜索、读取和创建钉钉文档。',
    'mcp_streamable_http',
    'knowledge_base',
    'high',
    'active',
    true,
    'system'
  ),
  (
    'plugin_standard_dingtalk_drive',
    'dingtalk_drive',
    '钉钉钉盘',
    '钉钉官方钉盘 MCP 插件，用于列出钉盘文件并作为知识输入。',
    'mcp_streamable_http',
    'knowledge_base',
    'medium',
    'active',
    true,
    'system'
  ),
  (
    'plugin_standard_dingtalk_wiki',
    'dingtalk_wiki',
    '钉钉知识库',
    '钉钉官方知识库 MCP 插件，用于搜索知识库空间和知识入口。',
    'mcp_streamable_http',
    'knowledge_base',
    'medium',
    'active',
    true,
    'system'
  )
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  protocol = EXCLUDED.protocol,
  category = EXCLUDED.category,
  risk_level = EXCLUDED.risk_level,
  status = EXCLUDED.status,
  is_system = true,
  updated_at = now();
