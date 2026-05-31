CREATE TABLE IF NOT EXISTS role_definitions (
  code text PRIMARY KEY,
  name text NOT NULL,
  description text NOT NULL,
  category text NOT NULL DEFAULT 'workspace',
  business_roles jsonb NOT NULL DEFAULT '[]'::jsonb,
  responsibilities jsonb NOT NULL DEFAULT '[]'::jsonb,
  data_scope text NOT NULL DEFAULT '',
  decision_scope text NOT NULL DEFAULT '',
  menu_scope jsonb NOT NULL DEFAULT '[]'::jsonb,
  limitations jsonb NOT NULL DEFAULT '[]'::jsonb,
  permissions jsonb NOT NULL DEFAULT '[]'::jsonb,
  is_assignable boolean NOT NULL DEFAULT true,
  sort_order integer NOT NULL DEFAULT 0,
  status text NOT NULL DEFAULT 'active',
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE role_definitions ADD COLUMN IF NOT EXISTS category text NOT NULL DEFAULT 'workspace';
ALTER TABLE role_definitions ADD COLUMN IF NOT EXISTS business_roles jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE role_definitions ADD COLUMN IF NOT EXISTS responsibilities jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE role_definitions ADD COLUMN IF NOT EXISTS data_scope text NOT NULL DEFAULT '';
ALTER TABLE role_definitions ADD COLUMN IF NOT EXISTS decision_scope text NOT NULL DEFAULT '';
ALTER TABLE role_definitions ADD COLUMN IF NOT EXISTS menu_scope jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE role_definitions ADD COLUMN IF NOT EXISTS limitations jsonb NOT NULL DEFAULT '[]'::jsonb;

INSERT INTO role_definitions (
  code,
  name,
  description,
  category,
  business_roles,
  responsibilities,
  data_scope,
  decision_scope,
  menu_scope,
  limitations,
  permissions,
  is_assignable,
  sort_order,
  status
)
VALUES
  (
    'admin',
    '系统管理员',
    '负责用户、角色、模型网关、审计与系统级配置管理。',
    'system',
    '["平台管理员"]'::jsonb,
    '["管理本地用户账号、状态和角色分配。", "维护 OpenAI-compatible 模型网关配置。", "查看审计与运行状态，处理系统级异常。"]'::jsonb,
    '全平台系统配置、审计事件和授权业务数据。',
    '账号、角色、模型网关和系统配置治理；不替代业务负责人做产品取舍。',
    '["系统管理", "审计与运行", "产品资产", "需求交付", "任务中心"]'::jsonb,
    '["不代替产品负责人、研发负责人或评审负责人做业务最终决策。", "所有系统配置、用户和模型网关变更必须写入审计。"]'::jsonb,
    '["system.users.manage", "system.model_gateway.manage", "audit.read", "workspace.read", "workspace.write"]'::jsonb,
    true,
    10,
    'active'
  ),
  (
    'product_owner',
    '产品负责人',
    '负责产品配置、版本模块、需求审批、任务生成和产品侧交付闭环。',
    'delivery',
    '["产品负责人"]'::jsonb,
    '["维护产品、版本、模块和相关系统上下文。", "审批需求并从已批准需求生成 AI 任务。", "确认产品详细设计、采纳或驳回迭代建议。"]'::jsonb,
    '所负责产品、版本和模块下的需求、AI 任务、Bug、知识引用和看板摘要。',
    '需求审批、产品详细设计确认、迭代规划采纳和产品侧优先级决策。',
    '["需求管理", "产品管理", "任务管理", "Bug 管理", "首页 IT 团队看板"]'::jsonb,
    '["不能确认技术方案或代码 Review 报告。", "不能维护系统用户、角色或模型网关密钥。"]'::jsonb,
    '["product.manage", "requirement.create", "requirement.approve", "requirement.task_generate", "planning.decide", "bug.manage", "workspace.read", "workspace.write"]'::jsonb,
    true,
    20,
    'active'
  ),
  (
    'rd_owner',
    '研发负责人',
    '负责研发任务执行、技术方案确认、Bug 处理和研发知识沉淀。',
    'delivery',
    '["研发负责人"]'::jsonb,
    '["创建并启动研发 AI 任务，推进技术方案闭环。", "确认技术方案和研发侧人工 Review。", "处理 Bug、沉淀研发知识并维护研发执行上下文。"]'::jsonb,
    '授权产品下的 AI 任务、技术方案、GitLab 只读快照、Bug 和研发知识。',
    '技术方案确认、研发任务推进、Bug 处理和研发知识沉淀决策。',
    '["任务管理", "Bug 管理", "知识中心", "研发运营看板", "首页 IT 团队看板"]'::jsonb,
    '["不能维护系统用户、角色或模型网关密钥。", "产品优先级和迭代采纳仍由产品负责人确认。"]'::jsonb,
    '["task.create", "task.execute", "review.decide", "gitlab.read", "knowledge.manage", "bug.manage", "workspace.read", "workspace.write"]'::jsonb,
    true,
    30,
    'active'
  ),
  (
    'reviewer',
    '评审负责人',
    '负责高影响 AI 输出、需求分析、设计方案和代码评审的人工确认。',
    'review',
    '["指定评审人", "研发负责人"]'::jsonb,
    '["确认产品详细设计、技术方案或代码 Review 报告。", "在信息不足时要求补充，并保留评审原因。", "守住高影响 AI 动作的人审门禁。"]'::jsonb,
    '分配给评审人的 AI 任务、Review 检查点、MR 只读快照和评审报告。',
    '对高影响 AI 输出执行批准、修改后批准、拒绝或要求补充信息。',
    '["任务管理", "审计与运行"]'::jsonb,
    '["不能维护产品主数据或审批需求。", "不能启动非评审范围内的 AI 任务。"]'::jsonb,
    '["review.decide", "task.read", "gitlab.review", "workspace.read"]'::jsonb,
    true,
    40,
    'active'
  ),
  (
    'knowledge_owner',
    '知识负责人',
    '负责知识文档导入、权限角色维护、检索治理和沉淀审核。',
    'knowledge',
    '["文档/知识维护者"]'::jsonb,
    '["导入和维护知识文档及索引状态。", "维护知识访问角色，确保检索前完成权限过滤。", "审核任务产出的知识沉淀候选。"]'::jsonb,
    '知识文档、chunk、检索结果、权限角色和知识沉淀候选。',
    '知识导入、权限配置、索引治理和沉淀候选审核。',
    '["知识中心", "审计与运行"]'::jsonb,
    '["不能审批需求、确认技术方案或创建代码 Review 任务。", "知识权限只能从已定义角色目录中选择。"]'::jsonb,
    '["knowledge.manage", "knowledge.search", "knowledge.deposit.decide", "workspace.read"]'::jsonb,
    true,
    50,
    'active'
  ),
  (
    'viewer',
    '查看者',
    '只能查看有权限访问的工作台数据、任务结果、知识和看板摘要。',
    'readonly',
    '["IT 管理者", "测试负责人", "测试人员", "只读参与者"]'::jsonb,
    '["查看授权范围内的业务数据和任务结果。", "查看知识、审计摘要和后续阶段真实空状态。"]'::jsonb,
    '授权范围内的列表、详情、任务结果、知识检索结果和看板摘要。',
    '无写入或审批决策权限。',
    '["首页 IT 团队看板", "授权业务列表", "知识检索"]'::jsonb,
    '["不能执行写操作、审批或配置变更。", "只能读取已授权产品、任务或知识范围内的数据。"]'::jsonb,
    '["workspace.read"]'::jsonb,
    true,
    60,
    'active'
  )
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  category = EXCLUDED.category,
  business_roles = EXCLUDED.business_roles,
  responsibilities = EXCLUDED.responsibilities,
  data_scope = EXCLUDED.data_scope,
  decision_scope = EXCLUDED.decision_scope,
  menu_scope = EXCLUDED.menu_scope,
  limitations = EXCLUDED.limitations,
  permissions = EXCLUDED.permissions,
  is_assignable = EXCLUDED.is_assignable,
  sort_order = EXCLUDED.sort_order,
  status = EXCLUDED.status,
  updated_at = now();
