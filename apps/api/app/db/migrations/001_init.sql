CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

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

CREATE TABLE IF NOT EXISTS graph_runs (
  id text PRIMARY KEY,
  ai_task_id text NOT NULL,
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
  ai_task_id text NOT NULL,
  current_step text NOT NULL,
  state_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
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
CREATE INDEX IF NOT EXISTS idx_graph_runs_task ON graph_runs (ai_task_id);
CREATE INDEX IF NOT EXISTS idx_graph_checkpoints_run ON graph_checkpoints (graph_run_id);
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
