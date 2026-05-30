CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

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
  '{"default_task_types":["product_detail_design","technical_solution","code_review"]}'::jsonb
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
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  description text,
  owner_team text,
  status text NOT NULL DEFAULT 'active',
  display_order integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

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
  brain_app_id text DEFAULT 'rd_brain',
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
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ai_task_id text,
  subject_type text,
  subject_id text,
  event_type text NOT NULL,
  actor_id text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

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
