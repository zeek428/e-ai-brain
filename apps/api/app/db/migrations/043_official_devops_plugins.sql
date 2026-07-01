ALTER TABLE IF EXISTS integration_plugins
  ADD COLUMN IF NOT EXISTS is_system boolean NOT NULL DEFAULT false;

ALTER TABLE IF EXISTS integration_plugins
  DROP CONSTRAINT IF EXISTS ck_integration_plugins_protocol;

ALTER TABLE IF EXISTS integration_plugins
  ADD CONSTRAINT ck_integration_plugins_protocol CHECK (
    protocol IN (
      'http',
      'internal_read_model',
      'mcp_http',
      'mcp_stdio',
      'runner_polling',
      'runner_websocket'
    )
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
    'plugin_standard_ai_executor',
    'ai_executor',
    'AI 执行器',
    '官方标准 AI 执行器插件，用于通过受控 Runner 向 Codex、Claude、Hermes、OpenClaw 等执行器下达指令、等待执行结果并同步回写。',
    'runner_polling',
    'ai_service',
    'high',
    'active',
    true,
    'system'
  ),
  (
    'plugin_standard_gitlab',
    'gitlab',
    'GitLab',
    '官方标准 GitLab 插件，用于连接 GitLab API、读取项目、分支、提交、MR 和代码质量数据。',
    'http',
    'devops',
    'medium',
    'active',
    true,
    'system'
  ),
  (
    'plugin_standard_github',
    'github',
    'GitHub',
    '官方标准 GitHub 插件，用于连接 GitHub API、读取仓库、分支、提交、PR 和代码质量数据。',
    'http',
    'devops',
    'medium',
    'active',
    true,
    'system'
  ),
  (
    'plugin_standard_email',
    'email',
    '邮箱',
    '官方标准邮箱插件，用于连接企业邮件网关、SMTP/IMAP/POP3 或邮件 API，收取邮件或发送代码巡检、定时作业和业务通知。',
    'http',
    'collaboration',
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
