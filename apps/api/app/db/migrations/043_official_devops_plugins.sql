ALTER TABLE IF EXISTS integration_plugins
  ADD COLUMN IF NOT EXISTS is_system boolean NOT NULL DEFAULT false;

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
    '官方标准邮箱插件，用于连接企业邮件网关或邮件 API，发送代码巡检、定时作业和业务通知。',
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
