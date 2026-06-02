CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

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

CREATE TABLE IF NOT EXISTS users (
  id text PRIMARY KEY,
  email text NOT NULL UNIQUE,
  display_name text NOT NULL,
  roles jsonb NOT NULL DEFAULT '[]'::jsonb,
  password_hash text NOT NULL,
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO users (id, email, display_name, roles, password_hash, status)
VALUES
  (
    'user_admin',
    'admin@example.com',
    'AI Brain Admin',
    '["admin"]'::jsonb,
    'pbkdf2_sha256$210000$admin-local-salt$KntdecyMHyH2xHE5T1MpTcNqUSw77BzqFUHEEHh6IcI',
    'active'
  ),
  (
    'user_reviewer',
    'reviewer@example.com',
    'AI Brain Reviewer',
    '["reviewer"]'::jsonb,
    'pbkdf2_sha256$210000$reviewer-local-salt$2y8_7B-H676ivrW5jN7hGbvcmzq55VeL1RhrqRlZyXA',
    'active'
  )
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS app_state_snapshots (
  key text PRIMARY KEY,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS brain_apps (
  id text PRIMARY KEY,
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  description text,
  status text NOT NULL DEFAULT 'active',
  config jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO brain_apps (id, code, name, description, status, config)
VALUES (
  'rd_brain',
  'rd_brain',
  '研发大脑',
  '把研发需求转成可确认、可回写、可沉淀的任务方案。',
  'active',
  '{"default_task_types":["product_detail_design","technical_solution","development_planning","automated_testing","release_readiness","post_release_analysis","code_review"]}'::jsonb
)
ON CONFLICT (id) DO UPDATE SET
  code = EXCLUDED.code,
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  status = EXCLUDED.status,
  config = EXCLUDED.config,
  updated_at = now();

CREATE TABLE IF NOT EXISTS products (
  id text PRIMARY KEY,
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  description text,
  owner_team text,
  status text NOT NULL DEFAULT 'active',
  display_order integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS product_versions (
  id text PRIMARY KEY,
  product_id text NOT NULL REFERENCES products(id),
  code text NOT NULL,
  name text NOT NULL,
  description text,
  status text NOT NULL DEFAULT 'planning',
  start_date date,
  release_date date,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (product_id, code)
);

CREATE TABLE IF NOT EXISTS product_modules (
  id text PRIMARY KEY,
  product_id text NOT NULL REFERENCES products(id),
  code text NOT NULL,
  name text NOT NULL,
  description text,
  owner_team text,
  status text NOT NULL DEFAULT 'active',
  display_order integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (product_id, code)
);

CREATE TABLE IF NOT EXISTS product_git_repositories (
  id text PRIMARY KEY,
  product_id text NOT NULL REFERENCES products(id),
  repo_type text NOT NULL DEFAULT 'code',
  name text NOT NULL,
  remote_url text,
  git_provider text NOT NULL DEFAULT 'gitlab',
  project_id text,
  project_path text,
  credential_ref text,
  default_branch text NOT NULL DEFAULT 'main',
  root_path text NOT NULL DEFAULT '/',
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS related_systems (
  id text PRIMARY KEY,
  product_id text REFERENCES products(id) ON DELETE SET NULL,
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  description text,
  owner_team text,
  status text NOT NULL DEFAULT 'active',
  display_order integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_related_systems_product_status
  ON related_systems (product_id, status);

CREATE TABLE IF NOT EXISTS model_gateway_configs (
  id text PRIMARY KEY,
  name text NOT NULL,
  provider text NOT NULL DEFAULT 'openai_compatible',
  base_url text NOT NULL,
  api_key_ref text,
  default_chat_model text NOT NULL,
  default_embedding_model text NOT NULL,
  timeout_seconds integer NOT NULL DEFAULT 60,
  max_retries integer NOT NULL DEFAULT 1,
  status text NOT NULL DEFAULT 'active',
  is_default boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS model_gateway_logs (
  id text PRIMARY KEY,
  ai_task_id text,
  provider text NOT NULL,
  model text NOT NULL,
  purpose text NOT NULL,
  tokens jsonb NOT NULL DEFAULT '{}'::jsonb,
  latency_ms integer NOT NULL DEFAULT 0,
  status text NOT NULL,
  error text,
  model_gateway_config_id text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS requirements (
  id text PRIMARY KEY,
  brain_app_id text NOT NULL DEFAULT 'rd_brain',
  title text NOT NULL,
  product_id text NOT NULL REFERENCES products(id),
  version_id text NOT NULL REFERENCES product_versions(id),
  module_code text,
  description text NOT NULL,
  priority text NOT NULL DEFAULT 'P1',
  status text NOT NULL DEFAULT 'pending_approval',
  created_by text NOT NULL,
  approval_comment text,
  rejection_reason text,
  task_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_tasks (
  id text PRIMARY KEY,
  brain_app_id text NOT NULL DEFAULT 'rd_brain',
  requirement_id text REFERENCES requirements(id),
  task_type text NOT NULL,
  title text NOT NULL,
  status text NOT NULL DEFAULT 'draft',
  product_id text NOT NULL REFERENCES products(id),
  version_id text NOT NULL REFERENCES product_versions(id),
  module_code text,
  requirement_snapshot jsonb,
  product_context jsonb NOT NULL DEFAULT '{}'::jsonb,
  input_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  output_json jsonb,
  current_step text,
  error_code text,
  error_message text,
  created_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS graph_runs (
  id text PRIMARY KEY,
  ai_task_id text NOT NULL REFERENCES ai_tasks(id),
  task_type text NOT NULL,
  status text NOT NULL,
  current_step text,
  checkpoint_id text,
  runtime text,
  node_path jsonb NOT NULL DEFAULT '[]'::jsonb,
  state_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);

CREATE TABLE IF NOT EXISTS graph_checkpoints (
  id text PRIMARY KEY,
  graph_run_id text NOT NULL REFERENCES graph_runs(id),
  ai_task_id text NOT NULL REFERENCES ai_tasks(id),
  current_step text NOT NULL,
  state_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS human_reviews (
  id text PRIMARY KEY,
  ai_task_id text NOT NULL REFERENCES ai_tasks(id),
  stage text NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  version integer NOT NULL DEFAULT 1,
  content jsonb NOT NULL DEFAULT '{}'::jsonb,
  edited_content jsonb,
  decision_reason text,
  decided_by text,
  questions jsonb NOT NULL DEFAULT '[]'::jsonb,
  decided_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS gitlab_mr_snapshots (
  id text PRIMARY KEY,
  repository_id text NOT NULL REFERENCES product_git_repositories(id),
  product_id text NOT NULL REFERENCES products(id),
  version_id text REFERENCES product_versions(id),
  project_id text,
  project_path text,
  mr_iid integer NOT NULL,
  title text NOT NULL,
  author jsonb,
  source_branch text NOT NULL,
  target_branch text NOT NULL,
  base_sha text,
  head_sha text NOT NULL,
  diff_refs jsonb,
  changed_files_summary jsonb NOT NULL DEFAULT '[]'::jsonb,
  diff_storage_ref text NOT NULL,
  diff_size_bytes integer NOT NULL DEFAULT 0,
  diff_limit_bytes integer NOT NULL DEFAULT 0,
  snapshot_hash text NOT NULL,
  requirement_id text NOT NULL REFERENCES requirements(id),
  technical_solution_task_id text NOT NULL REFERENCES ai_tasks(id),
  created_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  writeback_allowed boolean NOT NULL DEFAULT false,
  UNIQUE (repository_id, snapshot_hash)
);

CREATE TABLE IF NOT EXISTS code_review_reports (
  id text PRIMARY KEY,
  task_id text NOT NULL REFERENCES ai_tasks(id),
  gitlab_mr_snapshot_id text NOT NULL REFERENCES gitlab_mr_snapshots(id),
  executor jsonb NOT NULL DEFAULT '{}'::jsonb,
  summary text NOT NULL,
  risk_level text NOT NULL,
  findings jsonb NOT NULL DEFAULT '[]'::jsonb,
  status text NOT NULL DEFAULT 'draft',
  review_id text REFERENCES human_reviews(id),
  archived_at timestamptz,
  error_code text,
  gitlab_writeback_performed boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_documents (
  id text PRIMARY KEY,
  brain_app_id text DEFAULT 'rd_brain',
  product_id text REFERENCES products(id),
  version_id text REFERENCES product_versions(id),
  title text NOT NULL,
  content text NOT NULL,
  source_type text NOT NULL DEFAULT 'manual',
  doc_type text NOT NULL DEFAULT 'manual',
  permission_scope jsonb NOT NULL DEFAULT '{}'::jsonb,
  permission_roles jsonb NOT NULL DEFAULT '["admin"]'::jsonb,
  index_status text NOT NULL DEFAULT 'pending_index',
  index_error text,
  tags jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
  id text PRIMARY KEY,
  document_id text NOT NULL REFERENCES knowledge_documents(id),
  chunk_index integer NOT NULL,
  content text NOT NULL,
  embedding vector(1536),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  permission_scope jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS knowledge_deposits (
  id text PRIMARY KEY,
  ai_task_id text NOT NULL REFERENCES ai_tasks(id),
  deposit_type text NOT NULL DEFAULT 'task_output',
  title text NOT NULL,
  content text NOT NULL,
  content_hash text,
  status text NOT NULL DEFAULT 'pending',
  knowledge_document_id text REFERENCES knowledge_documents(id),
  rejection_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (ai_task_id, deposit_type, content_hash)
);

CREATE TABLE IF NOT EXISTS mock_issues (
  id text PRIMARY KEY,
  source_task_id text NOT NULL REFERENCES ai_tasks(id),
  title text NOT NULL,
  status text NOT NULL DEFAULT 'open',
  idempotency_key text NOT NULL UNIQUE,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bugs (
  id text PRIMARY KEY,
  product_id text NOT NULL REFERENCES products(id),
  version_id text REFERENCES product_versions(id),
  module_code text,
  source text NOT NULL,
  title text NOT NULL,
  severity text NOT NULL,
  description text NOT NULL,
  status text NOT NULL DEFAULT 'open',
  assignee text,
  related_task_id text REFERENCES ai_tasks(id),
  requirement_id text REFERENCES requirements(id),
  reproduce_steps jsonb NOT NULL DEFAULT '[]'::jsonb,
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  duplicate_of_bug_id text REFERENCES bugs(id),
  created_by text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lifecycle_context_edges (
  id text PRIMARY KEY,
  source_subject_type text NOT NULL,
  source_subject_id text NOT NULL,
  target_subject_type text NOT NULL,
  target_subject_id text NOT NULL,
  relation_type text NOT NULL,
  product_id text,
  version_id text,
  module_code text,
  confidence numeric NOT NULL DEFAULT 1.0,
  source_module text NOT NULL,
  observed_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS lifecycle_risk_signals (
  id text PRIMARY KEY,
  product_id text,
  risk_type text NOT NULL,
  severity text NOT NULL,
  source_subject_type text NOT NULL,
  source_subject_id text NOT NULL,
  impact_summary text NOT NULL,
  recommendation text NOT NULL,
  observed_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_events (
  id text PRIMARY KEY,
  ai_task_id text,
  subject_type text,
  subject_id text,
  event_type text NOT NULL,
  actor_id text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  sequence integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE audit_events ALTER COLUMN id DROP DEFAULT;
ALTER TABLE audit_events ALTER COLUMN id TYPE text USING id::text;
ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS sequence integer NOT NULL DEFAULT 0;

CREATE UNIQUE INDEX IF NOT EXISTS idx_model_gateway_default_active
  ON model_gateway_configs (is_default)
  WHERE is_default = true AND status = 'active';

CREATE INDEX IF NOT EXISTS idx_model_gateway_logs_task ON model_gateway_logs (ai_task_id);
CREATE INDEX IF NOT EXISTS idx_model_gateway_logs_created_at
  ON model_gateway_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_products_status ON products (status);
CREATE INDEX IF NOT EXISTS idx_product_versions_product_status
  ON product_versions (product_id, status);
CREATE INDEX IF NOT EXISTS idx_product_modules_product_status
  ON product_modules (product_id, status);
CREATE INDEX IF NOT EXISTS idx_product_git_repositories_product_status
  ON product_git_repositories (product_id, status);
CREATE INDEX IF NOT EXISTS idx_requirements_status ON requirements (status);
CREATE INDEX IF NOT EXISTS idx_requirements_product_id ON requirements (product_id);
CREATE INDEX IF NOT EXISTS idx_requirements_created_at ON requirements (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_tasks_status ON ai_tasks (status);
CREATE INDEX IF NOT EXISTS idx_ai_tasks_requirement ON ai_tasks (requirement_id);
CREATE INDEX IF NOT EXISTS idx_ai_tasks_product_status ON ai_tasks (product_id, status);
CREATE INDEX IF NOT EXISTS idx_ai_tasks_brain_app ON ai_tasks (brain_app_id);
CREATE INDEX IF NOT EXISTS idx_graph_runs_task ON graph_runs (ai_task_id);
CREATE INDEX IF NOT EXISTS idx_graph_checkpoints_run ON graph_checkpoints (graph_run_id);
CREATE INDEX IF NOT EXISTS idx_human_reviews_task ON human_reviews (ai_task_id);
CREATE INDEX IF NOT EXISTS idx_human_reviews_status ON human_reviews (status);
CREATE INDEX IF NOT EXISTS idx_gitlab_mr_snapshots_requirement
  ON gitlab_mr_snapshots (requirement_id);
CREATE INDEX IF NOT EXISTS idx_code_review_reports_task ON code_review_reports (task_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_index_status
  ON knowledge_documents (index_status);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document ON knowledge_chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_deposits_task_status
  ON knowledge_deposits (ai_task_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS uk_mock_issues_idempotency
  ON mock_issues (idempotency_key);
CREATE INDEX IF NOT EXISTS idx_bugs_product_status ON bugs (product_id, status);
CREATE INDEX IF NOT EXISTS idx_bugs_product_severity ON bugs (product_id, severity);
CREATE INDEX IF NOT EXISTS idx_bugs_source ON bugs (source);
CREATE INDEX IF NOT EXISTS idx_bugs_related_task ON bugs (related_task_id);
CREATE INDEX IF NOT EXISTS idx_lifecycle_edges_source
  ON lifecycle_context_edges (source_subject_type, source_subject_id);
CREATE INDEX IF NOT EXISTS idx_lifecycle_edges_target
  ON lifecycle_context_edges (target_subject_type, target_subject_id);
CREATE INDEX IF NOT EXISTS idx_lifecycle_risk_product
  ON lifecycle_risk_signals (product_id, severity, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_ai_task_id ON audit_events (ai_task_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_subject ON audit_events (subject_type, subject_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_event_type ON audit_events (event_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_created_at ON audit_events (created_at DESC);
