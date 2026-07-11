CREATE TABLE IF NOT EXISTS execution_context_manifests (
  id text PRIMARY KEY,
  subject_type text NOT NULL,
  subject_id text NOT NULL,
  product_id text REFERENCES products(id) ON DELETE CASCADE,
  version integer NOT NULL DEFAULT 1,
  content_hash text NOT NULL,
  requirement_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  bug_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  repository_ref jsonb NOT NULL DEFAULT '{}'::jsonb,
  branch text,
  knowledge_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  acceptance_criteria jsonb NOT NULL DEFAULT '[]'::jsonb,
  permission_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  retrieval_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  truncation_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  iteration_context jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by text REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (subject_type, subject_id, version),
  CONSTRAINT ck_execution_context_manifest_version CHECK (version > 0)
);

CREATE INDEX IF NOT EXISTS idx_execution_context_manifests_subject
  ON execution_context_manifests (subject_type, subject_id, version DESC);

CREATE INDEX IF NOT EXISTS idx_execution_context_manifests_product
  ON execution_context_manifests (product_id, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_execution_context_manifests_content
  ON execution_context_manifests (subject_type, subject_id, content_hash);

ALTER TABLE execution_context_manifests
  ADD COLUMN IF NOT EXISTS iteration_context jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE TABLE IF NOT EXISTS quality_gate_policies (
  id text PRIMARY KEY,
  name text NOT NULL,
  product_id text REFERENCES products(id) ON DELETE CASCADE,
  task_type text,
  phase text NOT NULL,
  risk_levels jsonb NOT NULL DEFAULT '["low", "medium", "high", "critical"]'::jsonb,
  required_checks jsonb NOT NULL DEFAULT '[]'::jsonb,
  protected_paths jsonb NOT NULL DEFAULT '[]'::jsonb,
  max_changed_files integer,
  max_changed_lines integer,
  required_ci_contexts jsonb NOT NULL DEFAULT '[]'::jsonb,
  minimum_independent_evidence integer NOT NULL DEFAULT 1,
  manual_review_on_migration boolean NOT NULL DEFAULT true,
  status text NOT NULL DEFAULT 'active',
  version integer NOT NULL DEFAULT 1,
  created_by text REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_quality_gate_policy_phase CHECK (
    phase IN ('pre_merge', 'pre_deploy', 'post_deploy')
  ),
  CONSTRAINT ck_quality_gate_policy_status CHECK (status IN ('active', 'disabled')),
  CONSTRAINT ck_quality_gate_policy_version CHECK (version > 0),
  CONSTRAINT ck_quality_gate_policy_evidence CHECK (minimum_independent_evidence >= 1),
  CONSTRAINT ck_quality_gate_policy_changed_files CHECK (
    max_changed_files IS NULL OR max_changed_files > 0
  ),
  CONSTRAINT ck_quality_gate_policy_changed_lines CHECK (
    max_changed_lines IS NULL OR max_changed_lines > 0
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_quality_gate_policy_scope
  ON quality_gate_policies (
    COALESCE(product_id, ''),
    COALESCE(task_type, ''),
    phase,
    version
  );

CREATE INDEX IF NOT EXISTS idx_quality_gate_policy_match
  ON quality_gate_policies (phase, product_id, task_type, status, updated_at DESC);

CREATE TABLE IF NOT EXISTS quality_gate_runs (
  id text PRIMARY KEY,
  policy_id text REFERENCES quality_gate_policies(id) ON DELETE SET NULL,
  policy_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  phase text NOT NULL,
  subject_type text NOT NULL,
  subject_id text NOT NULL,
  product_id text REFERENCES products(id) ON DELETE CASCADE,
  context_manifest_id text REFERENCES execution_context_manifests(id) ON DELETE SET NULL,
  status text NOT NULL DEFAULT 'pending',
  risk_level text NOT NULL DEFAULT 'medium',
  independent_evidence_count integer NOT NULL DEFAULT 0,
  summary text,
  blocked_reasons jsonb NOT NULL DEFAULT '[]'::jsonb,
  started_at timestamptz,
  finished_at timestamptz,
  created_by text REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_quality_gate_run_phase CHECK (
    phase IN ('pre_merge', 'pre_deploy', 'post_deploy')
  ),
  CONSTRAINT ck_quality_gate_run_status CHECK (
    status IN ('pending', 'running', 'passed', 'failed', 'blocked', 'cancelled')
  ),
  CONSTRAINT ck_quality_gate_run_risk CHECK (
    risk_level IN ('low', 'medium', 'high', 'critical')
  ),
  CONSTRAINT ck_quality_gate_run_evidence CHECK (independent_evidence_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_quality_gate_runs_subject
  ON quality_gate_runs (subject_type, subject_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_quality_gate_runs_product_status
  ON quality_gate_runs (product_id, status, updated_at DESC);

CREATE TABLE IF NOT EXISTS quality_gate_checks (
  id text PRIMARY KEY,
  quality_gate_run_id text NOT NULL REFERENCES quality_gate_runs(id) ON DELETE CASCADE,
  check_type text NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  source text NOT NULL,
  required boolean NOT NULL DEFAULT true,
  independent boolean NOT NULL DEFAULT false,
  evidence_ref text,
  command_catalog_code text,
  exit_code integer,
  duration_ms integer,
  summary text,
  details_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_quality_gate_check_status CHECK (
    status IN ('pending', 'running', 'passed', 'failed', 'blocked', 'skipped', 'cancelled')
  ),
  CONSTRAINT ck_quality_gate_check_source CHECK (
    source IN ('runner_coding', 'platform_verifier', 'ci_webhook', 'platform_scan', 'human_approval')
  ),
  CONSTRAINT ck_quality_gate_check_duration CHECK (duration_ms IS NULL OR duration_ms >= 0)
);

CREATE INDEX IF NOT EXISTS idx_quality_gate_checks_run
  ON quality_gate_checks (quality_gate_run_id, status, check_type);

CREATE UNIQUE INDEX IF NOT EXISTS idx_quality_gate_checks_evidence
  ON quality_gate_checks (
    quality_gate_run_id,
    check_type,
    source,
    COALESCE(evidence_ref, '')
  );

CREATE TABLE IF NOT EXISTS agent_loop_runs (
  id text PRIMARY KEY,
  ai_task_id text NOT NULL REFERENCES ai_tasks(id) ON DELETE CASCADE,
  product_id text REFERENCES products(id) ON DELETE CASCADE,
  objective_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'planning',
  current_iteration integer NOT NULL DEFAULT 0,
  max_iterations integer NOT NULL DEFAULT 3,
  max_duration_seconds integer NOT NULL DEFAULT 3600,
  token_budget bigint,
  cost_budget numeric(14, 4),
  token_used bigint NOT NULL DEFAULT 0,
  cost_used numeric(14, 4) NOT NULL DEFAULT 0,
  context_manifest_id text REFERENCES execution_context_manifests(id) ON DELETE SET NULL,
  context_version integer NOT NULL DEFAULT 1,
  quality_gate_policy_id text REFERENCES quality_gate_policies(id) ON DELETE SET NULL,
  stop_reason text,
  started_at timestamptz,
  finished_at timestamptz,
  version integer NOT NULL DEFAULT 1,
  created_by text REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_agent_loop_status CHECK (
    status IN (
      'planning',
      'executing',
      'verifying',
      'reflecting',
      'waiting_review',
      'succeeded',
      'failed',
      'stopped',
      'safety_blocked'
    )
  ),
  CONSTRAINT ck_agent_loop_iterations CHECK (
    current_iteration >= 0 AND max_iterations BETWEEN 1 AND 20
  ),
  CONSTRAINT ck_agent_loop_duration CHECK (max_duration_seconds BETWEEN 60 AND 86400),
  CONSTRAINT ck_agent_loop_tokens CHECK (
    token_used >= 0 AND (token_budget IS NULL OR token_budget > 0)
  ),
  CONSTRAINT ck_agent_loop_cost CHECK (
    cost_used >= 0 AND (cost_budget IS NULL OR cost_budget > 0)
  ),
  CONSTRAINT ck_agent_loop_version CHECK (version > 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_loop_active_task
  ON agent_loop_runs (ai_task_id)
  WHERE status IN ('planning', 'executing', 'verifying', 'reflecting', 'waiting_review');

CREATE INDEX IF NOT EXISTS idx_agent_loop_product_status
  ON agent_loop_runs (product_id, status, updated_at DESC);

CREATE TABLE IF NOT EXISTS agent_loop_iterations (
  id text PRIMARY KEY,
  loop_run_id text NOT NULL REFERENCES agent_loop_runs(id) ON DELETE CASCADE,
  iteration_number integer NOT NULL,
  coding_runner_task_id text,
  verifier_runner_task_id text,
  quality_gate_run_id text REFERENCES quality_gate_runs(id) ON DELETE SET NULL,
  status text NOT NULL DEFAULT 'planning',
  plan_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  change_summary text,
  test_evidence jsonb NOT NULL DEFAULT '[]'::jsonb,
  failure_analysis jsonb NOT NULL DEFAULT '{}'::jsonb,
  verification_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  context_version integer NOT NULL DEFAULT 1,
  token_usage bigint NOT NULL DEFAULT 0,
  cost_amount numeric(14, 4) NOT NULL DEFAULT 0,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (loop_run_id, iteration_number),
  CONSTRAINT ck_agent_loop_iteration_number CHECK (iteration_number > 0),
  CONSTRAINT ck_agent_loop_iteration_status CHECK (
    status IN ('planning', 'executing', 'verifying', 'reflecting', 'passed', 'failed', 'stopped')
  ),
  CONSTRAINT ck_agent_loop_iteration_usage CHECK (token_usage >= 0 AND cost_amount >= 0)
);

CREATE INDEX IF NOT EXISTS idx_agent_loop_iterations_run
  ON agent_loop_iterations (loop_run_id, iteration_number DESC);

CREATE TABLE IF NOT EXISTS execution_outbox_events (
  id text PRIMARY KEY,
  aggregate_type text NOT NULL,
  aggregate_id text NOT NULL,
  event_type text NOT NULL,
  idempotency_key text NOT NULL UNIQUE,
  payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'pending',
  attempt_count integer NOT NULL DEFAULT 0,
  available_at timestamptz NOT NULL DEFAULT now(),
  lease_owner text,
  lease_until timestamptz,
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz,
  CONSTRAINT ck_execution_outbox_status CHECK (
    status IN ('pending', 'processing', 'completed', 'failed', 'dead_letter', 'cancelled')
  ),
  CONSTRAINT ck_execution_outbox_attempts CHECK (attempt_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_execution_outbox_claim
  ON execution_outbox_events (status, available_at, lease_until, created_at)
  WHERE status IN ('pending', 'failed', 'processing');

CREATE INDEX IF NOT EXISTS idx_execution_outbox_aggregate
  ON execution_outbox_events (aggregate_type, aggregate_id, created_at DESC);

CREATE TABLE IF NOT EXISTS execution_resource_grants (
  id text PRIMARY KEY,
  product_id text NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  environment text NOT NULL,
  resource_type text NOT NULL,
  resource_id text NOT NULL,
  target_code text NOT NULL DEFAULT '',
  status text NOT NULL DEFAULT 'active',
  version integer NOT NULL DEFAULT 1,
  created_by text REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (product_id, environment, resource_type, resource_id, target_code),
  CONSTRAINT ck_execution_resource_type CHECK (
    resource_type IN ('runner_target', 'jenkins_connection')
  ),
  CONSTRAINT ck_execution_resource_status CHECK (status IN ('active', 'disabled')),
  CONSTRAINT ck_execution_resource_version CHECK (version > 0)
);

CREATE INDEX IF NOT EXISTS idx_execution_resource_grants_lookup
  ON execution_resource_grants (
    product_id,
    environment,
    resource_type,
    status,
    resource_id,
    target_code
  );

CREATE TABLE IF NOT EXISTS external_event_inbox (
  id text PRIMARY KEY,
  provider text NOT NULL,
  event_type text NOT NULL,
  delivery_id text NOT NULL,
  signature_status text NOT NULL,
  payload_hash text NOT NULL,
  payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'pending',
  attempt_count integer NOT NULL DEFAULT 0,
  lease_owner text,
  lease_until timestamptz,
  error_message text,
  received_at timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (provider, delivery_id),
  CONSTRAINT ck_external_event_provider CHECK (
    provider IN ('github', 'gitlab', 'jenkins', 'prometheus', 'opentelemetry', 'sentry', 'user_behavior')
  ),
  CONSTRAINT ck_external_event_signature CHECK (
    signature_status IN ('verified', 'not_applicable', 'failed')
  ),
  CONSTRAINT ck_external_event_status CHECK (
    status IN ('pending', 'processing', 'completed', 'failed', 'dead_letter', 'ignored')
  ),
  CONSTRAINT ck_external_event_attempts CHECK (attempt_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_external_event_inbox_claim
  ON external_event_inbox (status, lease_until, received_at)
  WHERE status IN ('pending', 'failed', 'processing');

CREATE TABLE IF NOT EXISTS deployment_run_steps (
  id text PRIMARY KEY,
  deployment_run_id text NOT NULL REFERENCES deployment_runs(id) ON DELETE CASCADE,
  step_type text NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  sequence integer NOT NULL,
  quality_gate_run_id text REFERENCES quality_gate_runs(id) ON DELETE SET NULL,
  summary text,
  evidence_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (deployment_run_id, sequence),
  CONSTRAINT ck_deployment_run_step_type CHECK (
    step_type IN ('preflight', 'deploy', 'health_check', 'smoke_test', 'traffic_switch', 'rollback')
  ),
  CONSTRAINT ck_deployment_run_step_status CHECK (
    status IN ('pending', 'running', 'passed', 'failed', 'blocked', 'skipped', 'cancelled')
  ),
  CONSTRAINT ck_deployment_run_step_sequence CHECK (sequence > 0)
);

CREATE INDEX IF NOT EXISTS idx_deployment_run_steps_run
  ON deployment_run_steps (deployment_run_id, sequence);

CREATE TABLE IF NOT EXISTS knowledge_processing_profiles (
  id text PRIMARY KEY,
  name text NOT NULL,
  product_id text REFERENCES products(id) ON DELETE CASCADE,
  provider_type text NOT NULL,
  provider_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  credential_ref text,
  capabilities jsonb NOT NULL DEFAULT '[]'::jsonb,
  status text NOT NULL DEFAULT 'active',
  version integer NOT NULL DEFAULT 1,
  created_by text REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_knowledge_profile_provider CHECK (
    provider_type IN ('builtin', 'http', 'mineru', 'paddleocr', 'gotenberg', 'multimodal_gateway')
  ),
  CONSTRAINT ck_knowledge_profile_status CHECK (status IN ('active', 'disabled')),
  CONSTRAINT ck_knowledge_profile_version CHECK (version > 0)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_processing_profiles_product
  ON knowledge_processing_profiles (product_id, status, name);

CREATE TABLE IF NOT EXISTS knowledge_document_versions (
  id text PRIMARY KEY,
  document_id text NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
  version integer NOT NULL,
  source_asset_id text,
  processing_profile_id text REFERENCES knowledge_processing_profiles(id) ON DELETE SET NULL,
  parser_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  content_hash text NOT NULL,
  status text NOT NULL DEFAULT 'processing',
  activated_at timestamptz,
  expires_at timestamptz,
  created_by text REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (document_id, version),
  CONSTRAINT ck_knowledge_document_version CHECK (version > 0),
  CONSTRAINT ck_knowledge_document_version_status CHECK (
    status IN ('processing', 'active', 'failed', 'superseded', 'expired')
  )
);

CREATE INDEX IF NOT EXISTS idx_knowledge_document_versions_document
  ON knowledge_document_versions (document_id, version DESC);

CREATE TABLE IF NOT EXISTS knowledge_citation_feedback (
  id text PRIMARY KEY,
  product_id text REFERENCES products(id) ON DELETE CASCADE,
  document_id text NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
  document_version_id text REFERENCES knowledge_document_versions(id) ON DELETE SET NULL,
  chunk_id text REFERENCES knowledge_chunks(id) ON DELETE SET NULL,
  subject_type text,
  subject_id text,
  feedback_value text NOT NULL,
  comment text,
  created_by text REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_knowledge_citation_feedback_value CHECK (
    feedback_value IN ('useful', 'not_useful', 'outdated', 'incorrect')
  )
);

CREATE INDEX IF NOT EXISTS idx_knowledge_citation_feedback_document
  ON knowledge_citation_feedback (document_id, document_version_id, created_at DESC);

ALTER TABLE execution_context_manifests
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE external_event_inbox
  ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(),
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE knowledge_citation_feedback
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE rd_task_executor_policies
  ADD COLUMN IF NOT EXISTS autonomy_mode text NOT NULL DEFAULT 'single_pass',
  ADD COLUMN IF NOT EXISTS max_iterations integer NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS max_duration_seconds integer NOT NULL DEFAULT 3600,
  ADD COLUMN IF NOT EXISTS token_budget bigint,
  ADD COLUMN IF NOT EXISTS cost_budget numeric(14, 4),
  ADD COLUMN IF NOT EXISTS quality_gate_policy_id text
    REFERENCES quality_gate_policies(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS auto_merge_risk_threshold text NOT NULL DEFAULT 'low';

ALTER TABLE rd_task_executor_policies
  DROP CONSTRAINT IF EXISTS ck_rd_task_executor_policies_autonomy_mode;

ALTER TABLE rd_task_executor_policies
  ADD CONSTRAINT ck_rd_task_executor_policies_autonomy_mode CHECK (
    autonomy_mode IN ('single_pass', 'autonomous_loop')
  );

ALTER TABLE rd_task_executor_policies
  DROP CONSTRAINT IF EXISTS ck_rd_task_executor_policies_loop_limits;

ALTER TABLE rd_task_executor_policies
  ADD CONSTRAINT ck_rd_task_executor_policies_loop_limits CHECK (
    max_iterations BETWEEN 1 AND 20
    AND max_duration_seconds BETWEEN 60 AND 86400
    AND (token_budget IS NULL OR token_budget > 0)
    AND (cost_budget IS NULL OR cost_budget > 0)
  );

ALTER TABLE rd_task_executor_policies
  DROP CONSTRAINT IF EXISTS ck_rd_task_executor_policies_auto_merge_risk;

ALTER TABLE rd_task_executor_policies
  ADD CONSTRAINT ck_rd_task_executor_policies_auto_merge_risk CHECK (
    auto_merge_risk_threshold IN ('none', 'low', 'medium')
  );

ALTER TABLE ai_executor_tasks
  ADD COLUMN IF NOT EXISTS context_manifest_id text
    REFERENCES execution_context_manifests(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS agent_loop_run_id text
    REFERENCES agent_loop_runs(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS agent_loop_iteration_id text
    REFERENCES agent_loop_iterations(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS quality_gate_run_id text
    REFERENCES quality_gate_runs(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS task_kind text NOT NULL DEFAULT 'coding';

ALTER TABLE ai_executor_tasks
  DROP CONSTRAINT IF EXISTS ck_ai_executor_tasks_task_kind;

ALTER TABLE ai_executor_tasks
  ADD CONSTRAINT ck_ai_executor_tasks_task_kind CHECK (
    task_kind IN ('coding', 'quality_gate', 'deployment', 'integration')
  );

ALTER TABLE ai_executor_tasks
  DROP CONSTRAINT IF EXISTS ck_ai_executor_tasks_executor_type;

ALTER TABLE ai_executor_tasks
  ADD CONSTRAINT ck_ai_executor_tasks_executor_type CHECK (
    executor_type IN ('codex', 'claude', 'hermes', 'openclaw', 'deployment', 'quality_gate')
  );

ALTER TABLE deployment_schemes
  ADD COLUMN IF NOT EXISTS rollout_strategy text NOT NULL DEFAULT 'all_at_once',
  ADD COLUMN IF NOT EXISTS wave_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS preflight_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS health_check_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS rollback_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS window_enforcement text NOT NULL DEFAULT 'warn';

ALTER TABLE deployment_schemes
  DROP CONSTRAINT IF EXISTS ck_deployment_schemes_rollout_strategy;

ALTER TABLE deployment_schemes
  ADD CONSTRAINT ck_deployment_schemes_rollout_strategy CHECK (
    rollout_strategy IN ('all_at_once', 'canary', 'batch', 'blue_green')
  );

ALTER TABLE deployment_schemes
  DROP CONSTRAINT IF EXISTS ck_deployment_schemes_window_enforcement;

ALTER TABLE deployment_schemes
  ADD CONSTRAINT ck_deployment_schemes_window_enforcement CHECK (
    window_enforcement IN ('strict', 'warn', 'disabled')
  );

ALTER TABLE deployment_requests
  ADD COLUMN IF NOT EXISTS window_enforcement text NOT NULL DEFAULT 'warn',
  ADD COLUMN IF NOT EXISTS current_wave integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS total_waves integer NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS quality_gate_run_id text
    REFERENCES quality_gate_runs(id) ON DELETE SET NULL;

ALTER TABLE deployment_requests
  DROP CONSTRAINT IF EXISTS ck_deployment_request_status;

ALTER TABLE deployment_requests
  ADD CONSTRAINT ck_deployment_request_status CHECK (
    status IN (
      'draft',
      'pending_ops',
      'approved',
      'preflight',
      'deploying',
      'verifying',
      'cancelling',
      'rolling_back',
      'waiting_takeover',
      'succeeded',
      'failed',
      'cancelled',
      'rolled_back'
    )
  );

ALTER TABLE deployment_requests
  DROP CONSTRAINT IF EXISTS ck_deployment_request_waves;

ALTER TABLE deployment_requests
  ADD CONSTRAINT ck_deployment_request_waves CHECK (
    current_wave >= 0 AND total_waves > 0 AND current_wave <= total_waves
  );

ALTER TABLE deployment_runs
  ADD COLUMN IF NOT EXISTS operation text NOT NULL DEFAULT 'deploy',
  ADD COLUMN IF NOT EXISTS wave_number integer NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS wave_total integer NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS health_status text,
  ADD COLUMN IF NOT EXISTS rollback_run_id text REFERENCES deployment_runs(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS quality_gate_run_id text
    REFERENCES quality_gate_runs(id) ON DELETE SET NULL;

ALTER TABLE deployment_runs
  DROP CONSTRAINT IF EXISTS ck_deployment_runs_operation;

ALTER TABLE deployment_runs
  ADD CONSTRAINT ck_deployment_runs_operation CHECK (
    operation IN ('deploy', 'verify', 'rollback')
  );

ALTER TABLE deployment_runs
  DROP CONSTRAINT IF EXISTS ck_deployment_runs_waves;

ALTER TABLE deployment_runs
  ADD CONSTRAINT ck_deployment_runs_waves CHECK (
    wave_number > 0 AND wave_total > 0 AND wave_number <= wave_total
  );

ALTER TABLE deployment_runs
  DROP CONSTRAINT IF EXISTS ck_deployment_runs_health;

ALTER TABLE deployment_runs
  ADD CONSTRAINT ck_deployment_runs_health CHECK (
    health_status IS NULL OR health_status IN ('pending', 'healthy', 'unhealthy', 'skipped')
  );

ALTER TABLE knowledge_assets
  ADD COLUMN IF NOT EXISTS document_version_id text
    REFERENCES knowledge_document_versions(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS page_number integer,
  ADD COLUMN IF NOT EXISTS bounding_boxes jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS provider_metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE knowledge_chunks
  ADD COLUMN IF NOT EXISTS document_version_id text
    REFERENCES knowledge_document_versions(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS modality text NOT NULL DEFAULT 'text',
  ADD COLUMN IF NOT EXISTS embedding_model text;

ALTER TABLE knowledge_chunks
  DROP CONSTRAINT IF EXISTS ck_knowledge_chunks_modality;

ALTER TABLE knowledge_chunks
  ADD CONSTRAINT ck_knowledge_chunks_modality CHECK (
    modality IN ('text', 'image', 'table', 'layout', 'multimodal')
  );

CREATE INDEX IF NOT EXISTS idx_knowledge_assets_document_version
  ON knowledge_assets (document_version_id, page_number, asset_type);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document_version
  ON knowledge_chunks (document_version_id, modality, chunk_index);

INSERT INTO quality_gate_policies (
  id,
  name,
  phase,
  risk_levels,
  required_checks,
  protected_paths,
  max_changed_files,
  max_changed_lines,
  minimum_independent_evidence,
  manual_review_on_migration,
  status,
  version
)
VALUES (
  'quality_gate_policy_system_pre_merge',
  '系统默认研发合并门禁',
  'pre_merge',
  '["low", "medium", "high", "critical"]'::jsonb,
  '[
    {"type":"unit_test","required":true,"independent":true,"catalog_code":"project.unit_test"},
    {"type":"type_check","required":true,"independent":true,"catalog_code":"project.type_check"},
    {"type":"secret_scan","required":true,"independent":true,"catalog_code":"platform.secret_scan"}
  ]'::jsonb,
  '[
    "**/migrations/**",
    "**/auth/**",
    "**/permissions/**",
    "**/*secret*",
    "docker-compose*.yml"
  ]'::jsonb,
  60,
  2000,
  1,
  true,
  'active',
  1
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO execution_resource_grants (
  id,
  product_id,
  environment,
  resource_type,
  resource_id,
  target_code,
  status,
  version,
  created_by
)
SELECT
  'execution_resource_grant_' || substr(
    md5(
      scheme.product_id || ':' || scheme.environment || ':runner_target:' ||
      scheme.runner_id || ':' || scheme.target_code
    ),
    1,
    20
  ),
  scheme.product_id,
  scheme.environment,
  'runner_target',
  scheme.runner_id,
  scheme.target_code,
  'active',
  1,
  scheme.created_by
FROM deployment_schemes scheme
WHERE scheme.runner_id IS NOT NULL
  AND NULLIF(scheme.target_code, '') IS NOT NULL
ON CONFLICT (product_id, environment, resource_type, resource_id, target_code)
DO NOTHING;

INSERT INTO execution_resource_grants (
  id,
  product_id,
  environment,
  resource_type,
  resource_id,
  target_code,
  status,
  version,
  created_by
)
SELECT
  'execution_resource_grant_' || substr(
    md5(
      scheme.product_id || ':' || scheme.environment || ':jenkins_connection:' ||
      scheme.jenkins_connection_id
    ),
    1,
    20
  ),
  scheme.product_id,
  scheme.environment,
  'jenkins_connection',
  scheme.jenkins_connection_id,
  '',
  'active',
  1,
  scheme.created_by
FROM deployment_schemes scheme
WHERE scheme.jenkins_connection_id IS NOT NULL
ON CONFLICT (product_id, environment, resource_type, resource_id, target_code)
DO NOTHING;
