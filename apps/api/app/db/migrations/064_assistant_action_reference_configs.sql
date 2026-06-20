CREATE TABLE IF NOT EXISTS assistant_action_reference_configs (
  id text PRIMARY KEY,
  enterprise_id text,
  action_key text NOT NULL,
  title text NOT NULL,
  summary text NOT NULL,
  prompt text NOT NULL,
  url text NOT NULL,
  aliases jsonb NOT NULL DEFAULT '[]'::jsonb,
  roles jsonb NOT NULL DEFAULT '[]'::jsonb,
  permissions jsonb NOT NULL DEFAULT '[]'::jsonb,
  enabled boolean NOT NULL DEFAULT true,
  sort_order integer NOT NULL DEFAULT 0,
  template_version text,
  rollout_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by text,
  updated_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_assistant_action_reference_configs_order
  ON assistant_action_reference_configs(sort_order, action_key);

CREATE INDEX IF NOT EXISTS idx_assistant_action_reference_configs_enterprise
  ON assistant_action_reference_configs(enterprise_id)
  WHERE enterprise_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_assistant_action_reference_configs_scope_unique
  ON assistant_action_reference_configs(
    COALESCE(enterprise_id, ''),
    action_key,
    COALESCE(template_version, '')
  );

INSERT INTO assistant_action_reference_configs (
  id, action_key, title, summary, prompt, url, aliases, roles, permissions,
  enabled, sort_order, rollout_json, metadata_json, created_by, updated_by
)
VALUES
  (
    'assistant_action_reference_config_create_requirement',
    'create_requirement',
    '新建需求',
    '进入需求交付的新建需求流程，先整理需求草案字段。',
    '我要新建需求，请帮我梳理标题、背景、目标、优先级、产品和版本，并生成可提交的需求草案。',
    '/delivery/requirements',
    jsonb_build_array('新建', '新增', '创建', '需求', 'requirement'),
    jsonb_build_array('admin', 'product_owner', 'rd_owner'),
    '[]'::jsonb,
    true,
    10,
    '{}'::jsonb,
    jsonb_build_object('source', 'standard'),
    'system',
    'system'
  ),
  (
    'assistant_action_reference_config_create_bug',
    'create_bug',
    '新建 Bug',
    '进入 Bug 登记流程，先整理复现步骤、严重级别和证据。',
    '我要新建 Bug，请帮我整理标题、复现步骤、严重级别、影响范围、关联需求或任务，并生成 Bug 登记草案。',
    '/delivery/bugs',
    jsonb_build_array('新建', '新增', '创建', 'bug', '缺陷', '问题'),
    jsonb_build_array('admin', 'rd_owner', 'reviewer', 'test_owner', 'tester', 'release_owner'),
    '[]'::jsonb,
    true,
    20,
    '{}'::jsonb,
    jsonb_build_object('source', 'standard'),
    'system',
    'system'
  ),
  (
    'assistant_action_reference_config_create_plugin_connection',
    'create_plugin_connection',
    '新建插件连接',
    '生成可确认的插件连接草案。',
    '请帮我生成插件连接草案，先确认插件类型、Endpoint、认证方式、环境和必填参数。',
    '/tasks/plugins',
    jsonb_build_array('新建', '新增', '创建', '插件', '插件连接', '连接', 'plugin'),
    '[]'::jsonb,
    jsonb_build_array('system.plugins.manage'),
    true,
    30,
    '{}'::jsonb,
    jsonb_build_object('source', 'standard'),
    'system',
    'system'
  ),
  (
    'assistant_action_reference_config_create_plugin_action',
    'create_plugin_action',
    '新建插件动作',
    '生成可确认的插件动作草案。',
    '请帮我生成插件动作草案，先确认插件连接、请求方法、路径、参数映射和结果写入目标。',
    '/tasks/plugins',
    jsonb_build_array('新建', '新增', '创建', '插件', '插件动作', '动作', 'plugin action'),
    '[]'::jsonb,
    jsonb_build_array('system.plugins.manage'),
    true,
    40,
    '{}'::jsonb,
    jsonb_build_object('source', 'standard'),
    'system',
    'system'
  ),
  (
    'assistant_action_reference_config_create_scheduled_job',
    'create_scheduled_job',
    '新建定时作业',
    '生成可确认的定时作业草案。',
    '请帮我生成定时作业配置草案，并说明数据来源、AI处理、结果动作和调度策略。',
    '/tasks/scheduled-jobs',
    jsonb_build_array('新建', '新增', '创建', '定时作业', '定时任务', '任务', '作业', 'scheduled job'),
    '[]'::jsonb,
    jsonb_build_array('system.scheduled_jobs.manage'),
    true,
    50,
    '{}'::jsonb,
    jsonb_build_object('source', 'standard'),
    'system',
    'system'
  ),
  (
    'assistant_action_reference_config_create_knowledge_document',
    'create_knowledge_document',
    '新建知识文档/导入任务',
    '进入知识文档或导入任务创建流程，先整理空间、目录、权限和索引策略。',
    '我要新建知识文档或导入任务，请帮我确认知识空间、目录、来源文件、权限和索引策略。',
    '/assets/knowledge',
    jsonb_build_array('新建', '新增', '创建', '知识', '知识文档', '导入', '导入任务', 'knowledge'),
    jsonb_build_array('admin', 'knowledge_owner'),
    '[]'::jsonb,
    true,
    60,
    '{}'::jsonb,
    jsonb_build_object('source', 'standard'),
    'system',
    'system'
  ),
  (
    'assistant_action_reference_config_create_ai_capability',
    'create_ai_capability',
    '新建 AI 能力配置',
    '进入 AI 能力配置向导，生成 Skill 或 AI角色草案。',
    '我要新增 AI能力配置，请帮我选择创建 Skill 或 AI角色，并生成可确认的配置草案。',
    '/tasks/ai-capabilities',
    jsonb_build_array('新建', '新增', '创建', 'ai能力', 'ai 能力', 'skill', 'ai角色', '角色'),
    '[]'::jsonb,
    jsonb_build_array('system.ai_capabilities.manage'),
    true,
    70,
    '{}'::jsonb,
    jsonb_build_object('source', 'standard'),
    'system',
    'system'
  ),
  (
    'assistant_action_reference_config_diagnose_scheduled_job_run',
    'diagnose_scheduled_job_run',
    '运行诊断',
    '读取定时作业运行、插件调用、模型日志和结果写入记录，解释失败原因。',
    '请诊断最近失败的定时作业运行，并按数据连接、AI处理、结果动作说明原因。',
    '/tasks/scheduled-jobs?tab=runs',
    jsonb_build_array('诊断', '排查', '失败', '运行失败', '定时作业', '定时任务', 'run diagnostic'),
    '[]'::jsonb,
    jsonb_build_array('system.scheduled_jobs.manage', 'system.scheduled_jobs.run'),
    true,
    80,
    '{}'::jsonb,
    jsonb_build_object('source', 'standard'),
    'system',
    'system'
  ),
  (
    'assistant_action_reference_config_explain_assistant_metrics',
    'explain_assistant_metrics',
    '指标解释',
    '汇总 AI 助手草案、引用、运行和失败修复指标。',
    '请解释当前 AI 助手效果指标，包括草案采纳、引用使用、作业运行成功率和失败修复率。',
    '/assistant',
    jsonb_build_array('指标', '效果', '漏斗', '采纳率', '修复率', 'metrics'),
    '[]'::jsonb,
    '[]'::jsonb,
    true,
    90,
    '{}'::jsonb,
    jsonb_build_object('source', 'standard'),
    'system',
    'system'
  )
ON CONFLICT (id) DO NOTHING;
