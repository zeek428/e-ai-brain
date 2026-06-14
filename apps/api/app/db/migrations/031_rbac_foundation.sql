CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS departments (
  id text PRIMARY KEY DEFAULT ('dept_' || replace(gen_random_uuid()::text, '-', '')),
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  parent_id text REFERENCES departments(id),
  leader_user_id text REFERENCES users(id),
  status text NOT NULL DEFAULT 'active',
  sort_order integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (parent_id, name)
);

CREATE INDEX IF NOT EXISTS idx_departments_parent
  ON departments(parent_id);

CREATE TABLE IF NOT EXISTS external_identities (
  id text PRIMARY KEY DEFAULT ('external_identity_' || replace(gen_random_uuid()::text, '-', '')),
  provider text NOT NULL,
  external_subject text NOT NULL,
  external_email text,
  user_id text REFERENCES users(id),
  status text NOT NULL DEFAULT 'active',
  last_login_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (provider, external_subject)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_external_identities_active_user_provider
  ON external_identities(user_id, provider)
  WHERE status = 'active' AND user_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS user_departments (
  user_id text NOT NULL REFERENCES users(id),
  department_id text NOT NULL REFERENCES departments(id),
  is_primary boolean NOT NULL DEFAULT false,
  position_title text NOT NULL DEFAULT '',
  status text NOT NULL DEFAULT 'active',
  joined_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, department_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_departments_primary
  ON user_departments(user_id)
  WHERE is_primary IS TRUE AND status = 'active';

CREATE TABLE IF NOT EXISTS permissions (
  code text PRIMARY KEY,
  name text NOT NULL,
  category text NOT NULL,
  description text NOT NULL DEFAULT '',
  risk_level text NOT NULL DEFAULT 'normal',
  is_system boolean NOT NULL DEFAULT true,
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_permissions_category_status
  ON permissions(category, status);

CREATE TABLE IF NOT EXISTS menu_resources (
  code text PRIMARY KEY,
  name text NOT NULL,
  path text NOT NULL DEFAULT '',
  parent_code text REFERENCES menu_resources(code),
  menu_type text NOT NULL,
  icon text NOT NULL DEFAULT '',
  sort_order integer NOT NULL DEFAULT 0,
  required_permissions jsonb NOT NULL DEFAULT '[]'::jsonb,
  is_system boolean NOT NULL DEFAULT true,
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (menu_type IN ('group', 'page', 'hidden_page'))
);

CREATE INDEX IF NOT EXISTS idx_menu_resources_parent_sort
  ON menu_resources(parent_code, sort_order);

CREATE TABLE IF NOT EXISTS roles (
  id text PRIMARY KEY DEFAULT ('role_' || replace(gen_random_uuid()::text, '-', '')),
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  description text NOT NULL DEFAULT '',
  category text NOT NULL DEFAULT 'workspace',
  is_system boolean NOT NULL DEFAULT false,
  is_assignable boolean NOT NULL DEFAULT true,
  status text NOT NULL DEFAULT 'active',
  sort_order integer NOT NULL DEFAULT 0,
  created_by text REFERENCES users(id),
  updated_by text REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_roles_category_status
  ON roles(category, status);

CREATE TABLE IF NOT EXISTS role_permissions (
  role_id text NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  permission_code text NOT NULL REFERENCES permissions(code) ON DELETE CASCADE,
  granted_by text REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (role_id, permission_code)
);

CREATE INDEX IF NOT EXISTS idx_role_permissions_permission_code
  ON role_permissions(permission_code);

CREATE TABLE IF NOT EXISTS role_menu_grants (
  role_id text NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  menu_code text NOT NULL REFERENCES menu_resources(code) ON DELETE CASCADE,
  granted_by text REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (role_id, menu_code)
);

CREATE INDEX IF NOT EXISTS idx_role_menu_grants_menu_code
  ON role_menu_grants(menu_code);

CREATE TABLE IF NOT EXISTS user_roles (
  user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id text NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  granted_by text REFERENCES users(id),
  grant_reason text NOT NULL DEFAULT '',
  effective_from timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz,
  status text NOT NULL DEFAULT 'active',
  revoked_by text REFERENCES users(id),
  revoked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, role_id, status)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_roles_active_unique
  ON user_roles(user_id, role_id)
  WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_user_roles_role_status
  ON user_roles(role_id, status);

CREATE TABLE IF NOT EXISTS role_scope_grants (
  role_id text NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  scope_type text NOT NULL,
  scope_id text NOT NULL,
  access_level text NOT NULL DEFAULT 'read',
  granted_by text REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (role_id, scope_type, scope_id, access_level)
);

CREATE INDEX IF NOT EXISTS idx_role_scope_grants_scope
  ON role_scope_grants(scope_type, scope_id);

CREATE TABLE IF NOT EXISTS user_scope_grants (
  user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  scope_type text NOT NULL,
  scope_id text NOT NULL,
  access_level text NOT NULL DEFAULT 'read',
  granted_by text REFERENCES users(id),
  expires_at timestamptz,
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, scope_type, scope_id, access_level, status)
);

CREATE INDEX IF NOT EXISTS idx_user_scope_grants_scope
  ON user_scope_grants(scope_type, scope_id, status);

CREATE TABLE IF NOT EXISTS product_members (
  product_id text NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  member_role text NOT NULL,
  scope_type text NOT NULL DEFAULT 'product',
  scope_id text NOT NULL DEFAULT '*',
  status text NOT NULL DEFAULT 'active',
  granted_by text REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (product_id, user_id, member_role, scope_type, scope_id)
);

CREATE INDEX IF NOT EXISTS idx_product_members_user_status
  ON product_members(user_id, status);

CREATE TABLE IF NOT EXISTS knowledge_spaces (
  id text PRIMARY KEY DEFAULT ('knowledge_space_' || replace(gen_random_uuid()::text, '-', '')),
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  description text NOT NULL DEFAULT '',
  owner_user_id text REFERENCES users(id),
  department_id text REFERENCES departments(id),
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_spaces_department_status
  ON knowledge_spaces(department_id, status);

CREATE TABLE IF NOT EXISTS knowledge_space_products (
  knowledge_space_id text NOT NULL REFERENCES knowledge_spaces(id) ON DELETE CASCADE,
  product_id text NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (knowledge_space_id, product_id)
);

CREATE TABLE IF NOT EXISTS knowledge_space_members (
  knowledge_space_id text NOT NULL REFERENCES knowledge_spaces(id) ON DELETE CASCADE,
  user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  space_role text NOT NULL DEFAULT 'reader',
  status text NOT NULL DEFAULT 'active',
  granted_by text REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (knowledge_space_id, user_id, space_role)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_space_members_user_status
  ON knowledge_space_members(user_id, status);

CREATE TABLE IF NOT EXISTS role_change_events (
  id text PRIMARY KEY DEFAULT ('role_change_' || replace(gen_random_uuid()::text, '-', '')),
  role_id text REFERENCES roles(id) ON DELETE SET NULL,
  event_type text NOT NULL,
  before_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  after_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  actor_id text REFERENCES users(id),
  trace_id text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_role_change_events_role_created
  ON role_change_events(role_id, created_at DESC);

INSERT INTO departments (id, code, name, status, sort_order)
VALUES ('dept_default', 'default', '默认组织', 'active', 10)
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  status = EXCLUDED.status,
  sort_order = EXCLUDED.sort_order,
  updated_at = now();

INSERT INTO permissions (code, name, category, description, risk_level, is_system, status)
VALUES
  ('system.roles.read', '查看角色', 'system', '查看角色、权限点和菜单授权配置。', 'normal', true, 'active'),
  ('system.roles.manage', '管理角色', 'system', '创建、编辑、停用角色并维护权限和菜单授权。', 'high', true, 'active'),
  ('system.menus.read', '查看菜单', 'system', '查看系统菜单资源、路由入口和访问权限点配置。', 'normal', true, 'active'),
  ('system.menus.manage', '管理菜单', 'system', '创建、编辑、停用和排序系统菜单资源。', 'high', true, 'active'),
  ('system.users.read', '查看用户', 'system', '查看系统用户和授权摘要。', 'normal', true, 'active'),
  ('system.users.manage', '管理用户', 'system', '创建用户、维护状态、部门和角色授权。', 'high', true, 'active'),
  ('system.model_gateway.manage', '管理模型网关', 'system', '维护 OpenAI-compatible 模型网关配置。', 'high', true, 'active'),
  ('org.read', '查看组织', 'organization', '查看部门树和成员归属。', 'normal', true, 'active'),
  ('org.department.manage', '管理部门', 'organization', '维护组织部门、负责人和状态。', 'high', true, 'active'),
  ('org.member.manage', '管理组织成员', 'organization', '维护用户部门归属和岗位信息。', 'high', true, 'active'),
  ('product.read', '查看产品', 'product', '查看产品、版本、模块和相关系统上下文。', 'normal', true, 'active'),
  ('product.manage', '管理产品', 'product', '维护产品、版本、模块和产品上下文。', 'high', true, 'active'),
  ('product.scope.manage', '管理产品范围', 'product', '维护产品、版本和模块的数据范围授权。', 'high', true, 'active'),
  ('product.member.read', '查看产品成员', 'product_member', '查看产品成员和产品内职责。', 'normal', true, 'active'),
  ('product.member.manage', '管理产品成员', 'product_member', '维护产品成员、职责和产品范围。', 'high', true, 'active'),
  ('requirement.read', '查看需求', 'requirement', '查看需求台账、分析结果和全链路详情。', 'normal', true, 'active'),
  ('requirement.create', '创建需求', 'requirement', '创建和编辑需求草稿。', 'normal', true, 'active'),
  ('requirement.approve', '审批需求', 'requirement', '批准或驳回需求。', 'high', true, 'active'),
  ('requirement.task_generate', '生成任务', 'requirement', '从已批准需求生成 AI 任务。', 'high', true, 'active'),
  ('task.read', '查看任务', 'task', '查看 AI 任务列表、详情和执行结果。', 'normal', true, 'active'),
  ('task.create', '创建任务', 'task', '创建产品、研发、测试、发布和代码评审任务。', 'normal', true, 'active'),
  ('task.execute', '执行任务', 'task', '启动或继续 AI 任务执行。', 'high', true, 'active'),
  ('task.cancel', '取消任务', 'task', '取消运行中或等待中的 AI 任务。', 'high', true, 'active'),
  ('task.retry', '重试任务', 'task', '重试失败或需重新执行的 AI 任务。', 'high', true, 'active'),
  ('review.read', '查看评审', 'review', '查看人工确认点和评审记录。', 'normal', true, 'active'),
  ('review.decide', '评审决策', 'review', '批准、修改后批准、拒绝或要求补充信息。', 'high', true, 'active'),
  ('bug.read', '查看 Bug', 'bug', '查看 Bug 列表、详情和状态。', 'normal', true, 'active'),
  ('bug.manage', '管理 Bug', 'bug', '创建、分派、更新和关闭 Bug。', 'high', true, 'active'),
  ('test.read', '查看测试', 'testing', '查看测试计划、执行和自动化测试结果。', 'normal', true, 'active'),
  ('test.case.manage', '管理测试用例', 'testing', '维护测试用例和测试计划。', 'normal', true, 'active'),
  ('test.execution.manage', '管理测试执行', 'testing', '维护测试执行记录和测试结论。', 'high', true, 'active'),
  ('test.bug.verify', '验证 Bug', 'testing', '确认自动化或人工测试 Bug 的验证结果。', 'high', true, 'active'),
  ('release.read', '查看发布', 'release', '查看发布准备度和上线后分析。', 'normal', true, 'active'),
  ('release.readiness.manage', '管理发布准备度', 'release', '维护发布准备检查和证据。', 'high', true, 'active'),
  ('release.decide', '发布决策', 'release', '确认发布准备度和上线后分析结果。', 'high', true, 'active'),
  ('knowledge.read', '查看知识', 'knowledge', '查看已授权知识空间和知识文档。', 'normal', true, 'active'),
  ('knowledge.search', '检索知识', 'knowledge', '在已授权知识空间执行关键词或向量检索。', 'normal', true, 'active'),
  ('knowledge.manage', '管理知识', 'knowledge', '导入、维护、索引知识文档。', 'high', true, 'active'),
  ('knowledge.deposit.decide', '知识沉淀审核', 'knowledge', '审核任务输出的知识沉淀候选。', 'high', true, 'active'),
  ('knowledge_space.manage', '管理知识空间', 'knowledge', '维护知识空间、产品关联和成员授权。', 'high', true, 'active'),
  ('devops.read', '查看 DevOps 指标', 'devops', '查看 GitLab、Jenkins 和线上日志指标。', 'normal', true, 'active'),
  ('devops.metrics.manage', '管理 DevOps 指标', 'devops', '采集、修正或维护 DevOps 指标数据。', 'high', true, 'active'),
  ('gitlab.read', '查看 GitLab 快照', 'devops', '兼容现有 GitLab 快照读取权限。', 'normal', true, 'active'),
  ('gitlab.review', '查看代码评审', 'devops', '兼容现有代码评审报告权限。', 'normal', true, 'active'),
  ('insight.read', '查看洞察', 'insight', '查看用户反馈、使用指标和迭代建议。', 'normal', true, 'active'),
  ('insight.feedback.manage', '管理反馈', 'insight', '维护用户反馈、归因和处理状态。', 'normal', true, 'active'),
  ('planning.decide', '迭代决策', 'insight', '采纳、拒绝或调整 AI 迭代建议。', 'high', true, 'active'),
  ('audit.read', '查看审计', 'audit', '查看审计事件和系统运行记录。', 'high', true, 'active'),
  ('assistant.chat', '使用 AI 助手', 'assistant', '访问 AI 助手对话能力。', 'normal', true, 'active'),
  ('workspace.read', '查看工作台', 'workspace', '访问工作台、列表和只读摘要。', 'normal', true, 'active'),
  ('workspace.write', '写入工作台', 'workspace', '执行工作台内受控写操作。', 'normal', true, 'active')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  category = EXCLUDED.category,
  description = EXCLUDED.description,
  risk_level = EXCLUDED.risk_level,
  is_system = EXCLUDED.is_system,
  status = EXCLUDED.status,
  updated_at = now();

INSERT INTO menu_resources (
  code,
  name,
  path,
  parent_code,
  menu_type,
  icon,
  sort_order,
  required_permissions,
  is_system,
  status
)
VALUES
  ('workspace.dashboard', '团队看板', '/welcome', NULL, 'page', 'HomeOutlined', 10, '["workspace.read"]'::jsonb, true, 'active'),
  ('assistant.chat', 'AI 助手', '/assistant', NULL, 'page', 'RobotOutlined', 15, '["assistant.chat"]'::jsonb, true, 'active'),
  ('task', '任务中心', '/tasks', NULL, 'group', 'ProjectOutlined', 20, '[]'::jsonb, true, 'active'),
  ('task.center', '任务管理', '/tasks/management', 'task', 'page', 'UnorderedListOutlined', 21, '["task.read"]'::jsonb, true, 'active'),
  ('delivery', '需求交付', '/delivery', NULL, 'group', 'DeploymentUnitOutlined', 30, '[]'::jsonb, true, 'active'),
  ('delivery.requirements', '需求管理', '/delivery/requirements', 'delivery', 'page', 'FileDoneOutlined', 31, '["requirement.read"]'::jsonb, true, 'active'),
  ('delivery.requirement_full_chain', '需求全链路详情', '/delivery/requirements/:requirementId/full-chain', 'delivery', 'hidden_page', '', 32, '["requirement.read"]'::jsonb, true, 'active'),
  ('delivery.versions', '迭代版本', '/delivery/versions', 'delivery', 'page', 'BranchesOutlined', 33, '["product.read"]'::jsonb, true, 'active'),
  ('delivery.bugs', 'Bug 管理', '/delivery/bugs', 'delivery', 'page', 'BugOutlined', 34, '["bug.read"]'::jsonb, true, 'active'),
  ('product.assets', '产品资产', '/assets', NULL, 'group', 'AppstoreOutlined', 40, '[]'::jsonb, true, 'active'),
  ('product.products', '产品管理', '/assets/products', 'product.assets', 'page', 'AppstoreOutlined', 41, '["product.read"]'::jsonb, true, 'active'),
  ('knowledge.center', '知识中心', '/assets/knowledge', 'product.assets', 'page', 'BookOutlined', 42, '["knowledge.read"]'::jsonb, true, 'active'),
  ('knowledge.search', '知识检索', '/assets/knowledge', 'product.assets', 'hidden_page', 'SearchOutlined', 43, '["knowledge.search"]'::jsonb, true, 'active'),
  ('governance', '运营治理', '/governance', NULL, 'group', 'ControlOutlined', 50, '[]'::jsonb, true, 'active'),
  ('devops.metrics', '日志监控', '/governance/devops', 'governance', 'page', 'BarChartOutlined', 51, '["devops.read"]'::jsonb, true, 'active'),
  ('insight.center', '用户洞察', '/governance/insights', 'governance', 'page', 'RobotOutlined', 52, '["insight.read"]'::jsonb, true, 'active'),
  ('audit.events', '审计与运行', '/governance/audit', 'governance', 'page', 'SafetyCertificateOutlined', 53, '["audit.read"]'::jsonb, true, 'active'),
  ('system', '系统管理', '/system', NULL, 'group', 'SettingOutlined', 60, '[]'::jsonb, true, 'active'),
  ('system.users', '用户管理', '/system/users', 'system', 'page', 'TeamOutlined', 61, '["system.users.manage"]'::jsonb, true, 'active'),
  ('system.roles', '角色管理', '/system/roles', 'system', 'page', 'SafetyCertificateOutlined', 62, '["system.roles.manage"]'::jsonb, true, 'active'),
  ('system.menus', '菜单管理', '/system/menus', 'system', 'page', 'MenuOutlined', 63, '["system.menus.manage"]'::jsonb, true, 'active'),
  ('system.model_gateway', '模型网关', '/system/model-gateway', 'system', 'page', 'ApiOutlined', 64, '["system.model_gateway.manage"]'::jsonb, true, 'active'),
  ('org.departments', '部门管理', '/system/departments', 'system', 'hidden_page', 'ApartmentOutlined', 66, '["org.department.manage"]'::jsonb, true, 'active')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  path = EXCLUDED.path,
  parent_code = EXCLUDED.parent_code,
  menu_type = EXCLUDED.menu_type,
  icon = EXCLUDED.icon,
  sort_order = EXCLUDED.sort_order,
  required_permissions = EXCLUDED.required_permissions,
  is_system = EXCLUDED.is_system,
  status = EXCLUDED.status,
  updated_at = now();

WITH role_seed (code, name, description, category, is_system, is_assignable, sort_order, status) AS (
  VALUES
    ('admin', '系统管理员', '负责用户、角色、模型网关、审计与系统级配置管理。', 'system', true, true, 10, 'active'),
    ('product_owner', '产品负责人', '负责产品配置、版本模块、需求审批、任务生成和产品侧交付闭环。', 'delivery', true, true, 20, 'active'),
    ('rd_owner', '研发负责人', '负责研发任务执行、技术方案确认、Bug 处理和研发知识沉淀。', 'delivery', true, true, 30, 'active'),
    ('reviewer', '评审负责人', '负责高影响 AI 输出、需求分析、设计方案和代码评审的人工确认。', 'review', true, true, 40, 'active'),
    ('knowledge_owner', '知识负责人', '负责知识文档导入、知识空间维护、检索治理和沉淀审核。', 'knowledge', true, true, 50, 'active'),
    ('viewer', '查看者', '只能查看有权限访问的工作台数据、任务结果、知识和看板摘要。', 'readonly', true, true, 60, 'active'),
    ('developer', '开发工程师', '负责授权产品范围内的研发执行、Bug 处理和研发知识沉淀。', 'delivery', true, true, 70, 'active'),
    ('test_owner', '测试负责人', '负责测试计划、测试执行、自动化测试结果确认和 Bug 验证闭环。', 'testing', true, true, 80, 'active'),
    ('tester', '测试人员', '负责执行测试、提交验证结果并跟进授权范围内的 Bug。', 'testing', true, true, 90, 'active'),
    ('release_owner', '发布负责人', '负责发布准备度、发布确认和上线后分析闭环。', 'release', true, true, 100, 'active')
)
INSERT INTO roles (id, code, name, description, category, is_system, is_assignable, sort_order, status)
SELECT 'role_' || code, code, name, description, category, is_system, is_assignable, sort_order, status
FROM role_seed
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  category = EXCLUDED.category,
  is_system = EXCLUDED.is_system,
  is_assignable = EXCLUDED.is_assignable,
  sort_order = EXCLUDED.sort_order,
  status = EXCLUDED.status,
  updated_at = now();

WITH role_permission_seed(role_code, permission_code) AS (
  VALUES
    ('admin', 'system.roles.read'),
    ('admin', 'system.roles.manage'),
    ('admin', 'system.menus.read'),
    ('admin', 'system.menus.manage'),
    ('admin', 'system.users.read'),
    ('admin', 'system.users.manage'),
    ('admin', 'system.model_gateway.manage'),
    ('admin', 'org.read'),
    ('admin', 'org.department.manage'),
    ('admin', 'org.member.manage'),
    ('admin', 'product.read'),
    ('admin', 'product.manage'),
    ('admin', 'product.scope.manage'),
    ('admin', 'product.member.read'),
    ('admin', 'product.member.manage'),
    ('admin', 'requirement.read'),
    ('admin', 'task.read'),
    ('admin', 'review.read'),
    ('admin', 'bug.read'),
    ('admin', 'knowledge.read'),
    ('admin', 'knowledge.search'),
    ('admin', 'knowledge_space.manage'),
    ('admin', 'devops.read'),
    ('admin', 'insight.read'),
    ('admin', 'audit.read'),
    ('admin', 'assistant.chat'),
    ('admin', 'workspace.read'),
    ('admin', 'workspace.write'),
    ('product_owner', 'product.read'),
    ('product_owner', 'product.manage'),
    ('product_owner', 'product.member.read'),
    ('product_owner', 'product.member.manage'),
    ('product_owner', 'requirement.read'),
    ('product_owner', 'requirement.create'),
    ('product_owner', 'requirement.approve'),
    ('product_owner', 'requirement.task_generate'),
    ('product_owner', 'task.read'),
    ('product_owner', 'task.create'),
    ('product_owner', 'review.read'),
    ('product_owner', 'review.decide'),
    ('product_owner', 'bug.read'),
    ('product_owner', 'bug.manage'),
    ('product_owner', 'knowledge.read'),
    ('product_owner', 'knowledge.search'),
    ('product_owner', 'insight.read'),
    ('product_owner', 'planning.decide'),
    ('product_owner', 'assistant.chat'),
    ('product_owner', 'workspace.read'),
    ('product_owner', 'workspace.write'),
    ('rd_owner', 'product.read'),
    ('rd_owner', 'requirement.read'),
    ('rd_owner', 'task.read'),
    ('rd_owner', 'task.create'),
    ('rd_owner', 'task.execute'),
    ('rd_owner', 'task.cancel'),
    ('rd_owner', 'task.retry'),
    ('rd_owner', 'review.read'),
    ('rd_owner', 'review.decide'),
    ('rd_owner', 'bug.read'),
    ('rd_owner', 'bug.manage'),
    ('rd_owner', 'knowledge.read'),
    ('rd_owner', 'knowledge.search'),
    ('rd_owner', 'knowledge.manage'),
    ('rd_owner', 'knowledge.deposit.decide'),
    ('rd_owner', 'devops.read'),
    ('rd_owner', 'gitlab.read'),
    ('rd_owner', 'assistant.chat'),
    ('rd_owner', 'workspace.read'),
    ('rd_owner', 'workspace.write'),
    ('reviewer', 'task.read'),
    ('reviewer', 'review.read'),
    ('reviewer', 'review.decide'),
    ('reviewer', 'gitlab.review'),
    ('reviewer', 'audit.read'),
    ('reviewer', 'workspace.read'),
    ('knowledge_owner', 'knowledge.read'),
    ('knowledge_owner', 'knowledge.search'),
    ('knowledge_owner', 'knowledge.manage'),
    ('knowledge_owner', 'knowledge.deposit.decide'),
    ('knowledge_owner', 'knowledge_space.manage'),
    ('knowledge_owner', 'audit.read'),
    ('knowledge_owner', 'assistant.chat'),
    ('knowledge_owner', 'workspace.read'),
    ('viewer', 'workspace.read'),
    ('viewer', 'product.read'),
    ('viewer', 'requirement.read'),
    ('viewer', 'task.read'),
    ('viewer', 'bug.read'),
    ('viewer', 'knowledge.read'),
    ('viewer', 'knowledge.search'),
    ('viewer', 'devops.read'),
    ('viewer', 'insight.read'),
    ('viewer', 'assistant.chat'),
    ('developer', 'task.read'),
    ('developer', 'task.create'),
    ('developer', 'task.execute'),
    ('developer', 'bug.read'),
    ('developer', 'knowledge.search'),
    ('developer', 'assistant.chat'),
    ('developer', 'workspace.read'),
    ('test_owner', 'task.read'),
    ('test_owner', 'task.create'),
  ('test_owner', 'review.decide'),
  ('test_owner', 'bug.read'),
  ('test_owner', 'test.case.manage'),
  ('test_owner', 'test.execution.manage'),
  ('test_owner', 'test.bug.verify'),
    ('test_owner', 'assistant.chat'),
    ('test_owner', 'workspace.read'),
  ('tester', 'task.read'),
  ('tester', 'bug.read'),
  ('tester', 'test.read'),
  ('tester', 'test.execution.manage'),
  ('tester', 'test.bug.verify'),
    ('tester', 'assistant.chat'),
    ('tester', 'workspace.read'),
    ('release_owner', 'task.read'),
    ('release_owner', 'bug.read'),
    ('release_owner', 'release.readiness.manage'),
    ('release_owner', 'release.decide'),
    ('release_owner', 'devops.read'),
    ('release_owner', 'assistant.chat'),
    ('release_owner', 'workspace.read')
)
INSERT INTO role_permissions (role_id, permission_code)
SELECT r.id, role_permission_seed.permission_code
FROM role_permission_seed
JOIN roles r ON r.code = role_permission_seed.role_code
JOIN permissions p ON p.code = role_permission_seed.permission_code
ON CONFLICT (role_id, permission_code) DO UPDATE SET
  updated_at = now();

WITH role_menu_seed(role_code, menu_code) AS (
  VALUES
    ('admin', 'workspace.dashboard'),
    ('admin', 'assistant.chat'),
    ('admin', 'task'),
    ('admin', 'task.center'),
    ('admin', 'delivery'),
    ('admin', 'delivery.requirements'),
    ('admin', 'delivery.requirement_full_chain'),
    ('admin', 'delivery.versions'),
    ('admin', 'delivery.bugs'),
    ('admin', 'product.assets'),
    ('admin', 'product.products'),
    ('admin', 'knowledge.center'),
    ('admin', 'knowledge.search'),
    ('admin', 'governance'),
    ('admin', 'devops.metrics'),
    ('admin', 'insight.center'),
    ('admin', 'audit.events'),
    ('admin', 'system'),
    ('admin', 'system.users'),
    ('admin', 'system.roles'),
    ('admin', 'system.menus'),
    ('admin', 'system.model_gateway'),
    ('admin', 'org.departments'),
    ('product_owner', 'workspace.dashboard'),
    ('product_owner', 'assistant.chat'),
    ('product_owner', 'task'),
    ('product_owner', 'task.center'),
    ('product_owner', 'delivery'),
    ('product_owner', 'delivery.requirements'),
    ('product_owner', 'delivery.requirement_full_chain'),
    ('product_owner', 'delivery.versions'),
    ('product_owner', 'delivery.bugs'),
    ('product_owner', 'product.assets'),
    ('product_owner', 'product.products'),
    ('product_owner', 'knowledge.center'),
    ('product_owner', 'governance'),
    ('product_owner', 'insight.center'),
    ('rd_owner', 'workspace.dashboard'),
    ('rd_owner', 'assistant.chat'),
    ('rd_owner', 'task'),
    ('rd_owner', 'task.center'),
    ('rd_owner', 'delivery'),
    ('rd_owner', 'delivery.requirements'),
    ('rd_owner', 'delivery.bugs'),
    ('rd_owner', 'product.assets'),
    ('rd_owner', 'knowledge.center'),
    ('rd_owner', 'knowledge.search'),
    ('rd_owner', 'governance'),
    ('rd_owner', 'devops.metrics'),
    ('reviewer', 'task'),
    ('reviewer', 'task.center'),
    ('reviewer', 'governance'),
    ('reviewer', 'audit.events'),
    ('knowledge_owner', 'workspace.dashboard'),
    ('knowledge_owner', 'assistant.chat'),
    ('knowledge_owner', 'product.assets'),
    ('knowledge_owner', 'knowledge.center'),
    ('knowledge_owner', 'knowledge.search'),
    ('knowledge_owner', 'governance'),
    ('knowledge_owner', 'audit.events'),
    ('viewer', 'workspace.dashboard'),
    ('viewer', 'assistant.chat'),
    ('viewer', 'task'),
    ('viewer', 'task.center'),
    ('viewer', 'delivery'),
    ('viewer', 'delivery.requirements'),
    ('viewer', 'delivery.bugs'),
    ('viewer', 'product.assets'),
    ('viewer', 'knowledge.center'),
    ('viewer', 'knowledge.search'),
    ('developer', 'workspace.dashboard'),
    ('developer', 'assistant.chat'),
    ('developer', 'task'),
    ('developer', 'task.center'),
    ('developer', 'delivery'),
    ('developer', 'delivery.bugs'),
    ('developer', 'product.assets'),
    ('developer', 'knowledge.search'),
    ('test_owner', 'workspace.dashboard'),
    ('test_owner', 'assistant.chat'),
    ('test_owner', 'task'),
    ('test_owner', 'task.center'),
    ('test_owner', 'delivery'),
    ('test_owner', 'delivery.bugs'),
    ('tester', 'workspace.dashboard'),
    ('tester', 'assistant.chat'),
    ('tester', 'task'),
    ('tester', 'task.center'),
    ('tester', 'delivery'),
    ('tester', 'delivery.bugs'),
    ('release_owner', 'workspace.dashboard'),
    ('release_owner', 'assistant.chat'),
    ('release_owner', 'task'),
    ('release_owner', 'task.center'),
    ('release_owner', 'delivery'),
    ('release_owner', 'delivery.bugs'),
    ('release_owner', 'governance'),
    ('release_owner', 'devops.metrics')
)
INSERT INTO role_menu_grants (role_id, menu_code)
SELECT r.id, role_menu_seed.menu_code
FROM role_menu_seed
JOIN roles r ON r.code = role_menu_seed.role_code
JOIN menu_resources m ON m.code = role_menu_seed.menu_code
ON CONFLICT (role_id, menu_code) DO UPDATE SET
  updated_at = now();

WITH role_scope_seed(role_code, scope_type, scope_id, access_level) AS (
  VALUES
    ('admin', 'global', '*', 'admin'),
    ('reviewer', 'review_assignment', 'self', 'write'),
    ('test_owner', 'review_assignment', 'self', 'write'),
    ('knowledge_owner', 'knowledge_space', '*', 'admin'),
    ('viewer', 'self', '*', 'read')
)
INSERT INTO role_scope_grants (role_id, scope_type, scope_id, access_level)
SELECT r.id, role_scope_seed.scope_type, role_scope_seed.scope_id, role_scope_seed.access_level
FROM role_scope_seed
JOIN roles r ON r.code = role_scope_seed.role_code
ON CONFLICT (role_id, scope_type, scope_id, access_level) DO UPDATE SET
  updated_at = now();

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
    'developer',
    '开发工程师',
    '负责授权产品范围内的研发执行、Bug 处理和研发知识沉淀。',
    'delivery',
    '["开发工程师"]'::jsonb,
    '["执行研发任务并维护技术实现结果。", "处理授权范围内的 Bug。", "沉淀研发知识和上下文。"]'::jsonb,
    '授权产品、版本或模块下的任务、Bug、研发知识和 DevOps 只读数据。',
    '研发执行和 Bug 处理；不替代产品或发布决策。',
    '["任务管理", "Bug 管理", "知识检索", "首页 IT 团队看板"]'::jsonb,
    '["不能维护系统用户、角色或模型网关密钥。", "不能审批需求或确认发布决策。"]'::jsonb,
    '["task.read", "task.create", "task.execute", "bug.read", "knowledge.search", "assistant.chat", "workspace.read"]'::jsonb,
    true,
    70,
    'active'
  ),
  (
    'test_owner',
    '测试负责人',
    '负责测试计划、测试执行、自动化测试结果确认和 Bug 验证闭环。',
    'testing',
    '["测试负责人"]'::jsonb,
    '["维护测试计划和测试用例。", "确认自动化测试输出和 Bug 建议。", "推动 Bug 验证闭环。"]'::jsonb,
    '授权产品、版本或模块下的测试任务、Bug、测试证据和相关知识。',
    '测试策略、测试执行结论和 Bug 验证决策。',
    '["任务管理", "Bug 管理", "首页 IT 团队看板"]'::jsonb,
    '["不能维护系统用户、角色或模型网关密钥。", "不能替代发布负责人做发布确认。"]'::jsonb,
    '["task.read", "task.create", "review.decide", "bug.read", "test.case.manage", "test.execution.manage", "test.bug.verify", "assistant.chat", "workspace.read"]'::jsonb,
    true,
    80,
    'active'
  ),
  (
    'tester',
    '测试人员',
    '负责执行测试、提交验证结果并跟进授权范围内的 Bug。',
    'testing',
    '["测试人员"]'::jsonb,
    '["查看测试任务和 Bug。", "记录测试执行结果。", "验证 Bug 修复结果。"]'::jsonb,
    '授权产品、版本或模块下的测试任务、Bug 和只读知识。',
    '测试执行记录和 Bug 验证结果。',
    '["任务管理", "Bug 管理", "首页 IT 团队看板"]'::jsonb,
    '["不能审批需求、发布或系统配置。", "只能在授权范围内验证 Bug。"]'::jsonb,
    '["task.read", "bug.read", "test.read", "test.execution.manage", "test.bug.verify", "assistant.chat", "workspace.read"]'::jsonb,
    true,
    90,
    'active'
  ),
  (
    'release_owner',
    '发布负责人',
    '负责发布准备度、发布确认和上线后分析闭环。',
    'release',
    '["发布负责人"]'::jsonb,
    '["维护发布准备检查。", "确认发布决策和上线后分析。", "跟踪发布相关风险和证据。"]'::jsonb,
    '授权产品、版本下的发布准备度、Bug、任务结果和 DevOps 指标。',
    '发布准备确认、发布决策和上线后分析确认。',
    '["任务管理", "Bug 管理", "日志监控", "首页 IT 团队看板"]'::jsonb,
    '["不能维护系统用户、角色或模型网关密钥。", "不能替代产品负责人审批需求。"]'::jsonb,
    '["task.read", "bug.read", "release.readiness.manage", "release.decide", "devops.read", "assistant.chat", "workspace.read"]'::jsonb,
    true,
    100,
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

UPDATE role_definitions
SET
  permissions = (
    SELECT jsonb_agg(permission_code ORDER BY permission_code)
    FROM (
      SELECT DISTINCT permission_code
      FROM jsonb_array_elements_text(
        role_definitions.permissions
        || '["system.roles.read", "system.roles.manage", "system.menus.read", "system.menus.manage"]'::jsonb
      ) AS permission_values(permission_code)
    ) AS merged_permissions
  ),
  updated_at = now()
WHERE code = 'admin';

WITH legacy_roles AS (
  SELECT u.id AS user_id, role_values.role_code
  FROM users u
  CROSS JOIN LATERAL jsonb_array_elements_text(
    CASE
      WHEN jsonb_typeof(to_jsonb(u.roles)::jsonb) = 'array' THEN to_jsonb(u.roles)::jsonb
      ELSE '[]'::jsonb
    END
  ) AS role_values(role_code)
)
INSERT INTO user_roles (
  user_id,
  role_id,
  grant_reason,
  effective_from,
  status
)
SELECT
  legacy_roles.user_id,
  r.id,
  'compatibility backfill from users.roles',
  now(),
  'active'
FROM legacy_roles
JOIN roles r ON r.code = legacy_roles.role_code
ON CONFLICT (user_id, role_id, status) DO UPDATE SET
  grant_reason = EXCLUDED.grant_reason,
  updated_at = now();
