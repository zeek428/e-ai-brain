-- Requirement-driven R&D collaboration v2 additive schema.
-- This migration intentionally leaves legacy policy, task, and scheduled-job paths intact.

ALTER TABLE IF EXISTS rd_task_executor_policies
  ADD COLUMN IF NOT EXISTS policy_version bigint NOT NULL DEFAULT 1;

ALTER TABLE IF EXISTS rd_task_executor_policies
  DROP CONSTRAINT IF EXISTS ck_rd_task_executor_policies_policy_version;

ALTER TABLE IF EXISTS rd_task_executor_policies
  ADD CONSTRAINT ck_rd_task_executor_policies_policy_version CHECK (policy_version > 0);

CREATE UNIQUE INDEX IF NOT EXISTS uk_rd_task_executor_policies_version
  ON rd_task_executor_policies (id, policy_version);

CREATE OR REPLACE FUNCTION protect_rd_task_executor_policy_version_monotonic()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.policy_version < OLD.policy_version THEN
    RAISE EXCEPTION 'policy_version cannot decrease';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_rd_task_executor_policy_version_monotonic
  ON rd_task_executor_policies;

CREATE TRIGGER trg_rd_task_executor_policy_version_monotonic
BEFORE UPDATE OF policy_version ON rd_task_executor_policies
FOR EACH ROW EXECUTE FUNCTION protect_rd_task_executor_policy_version_monotonic();

DROP INDEX IF EXISTS uk_rd_task_executor_policies_active_product;
DROP INDEX IF EXISTS uk_rd_task_executor_policies_active_default;

-- Task 2 keeps legacy task-type policy selection writable. These indexes are
-- advisory lookup aids only; unified one-active-policy enforcement is a Task 14 cutover step.
CREATE INDEX IF NOT EXISTS idx_rd_task_executor_policies_active_product_advisory
  ON rd_task_executor_policies (brain_app_id, product_id)
  WHERE status = 'active' AND product_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_rd_task_executor_policies_active_default_advisory
  ON rd_task_executor_policies (brain_app_id)
  WHERE status = 'active' AND product_id IS NULL;

ALTER TABLE IF EXISTS product_versions
  ADD COLUMN IF NOT EXISTS scope_version bigint NOT NULL DEFAULT 1;

ALTER TABLE IF EXISTS product_version_branch_configs
  ADD COLUMN IF NOT EXISTS branch_config_version bigint NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS base_commit_sha text;

ALTER TABLE IF EXISTS product_version_branch_configs
  DROP CONSTRAINT IF EXISTS ck_product_version_branch_configs_version;

ALTER TABLE IF EXISTS product_version_branch_configs
  ADD CONSTRAINT ck_product_version_branch_configs_version CHECK (branch_config_version > 0);

ALTER TABLE IF EXISTS product_versions
  DROP CONSTRAINT IF EXISTS ck_product_versions_status;

ALTER TABLE IF EXISTS product_versions
  ADD CONSTRAINT ck_product_versions_status CHECK (
    status IN (
      'planning', 'active', 'testing', 'ready_for_release',
      'deploying', 'released', 'archived'
    )
  );

CREATE TABLE IF NOT EXISTS rd_role_definitions (
  id text PRIMARY KEY,
  brain_app_id text NOT NULL DEFAULT 'rd_brain' REFERENCES brain_apps(id) ON DELETE RESTRICT,
  code text NOT NULL,
  name text NOT NULL,
  capabilities jsonb NOT NULL DEFAULT '[]'::jsonb,
  responsibilities jsonb NOT NULL DEFAULT '[]'::jsonb,
  maximum_risk_level text NOT NULL DEFAULT 'medium',
  assignable_subject_types jsonb NOT NULL DEFAULT '["human_user", "ai_employee"]'::jsonb,
  status text NOT NULL DEFAULT 'active',
  created_by text REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (brain_app_id, code),
  CONSTRAINT ck_rd_role_definitions_status CHECK (status IN ('active', 'disabled')),
  CONSTRAINT ck_rd_role_definitions_risk CHECK (
    maximum_risk_level IN ('low', 'medium', 'high', 'critical')
  )
);

CREATE TABLE IF NOT EXISTS rd_ai_employees (
  id text PRIMARY KEY,
  brain_app_id text NOT NULL DEFAULT 'rd_brain' REFERENCES brain_apps(id) ON DELETE RESTRICT,
  code text NOT NULL,
  name text NOT NULL,
  capability_tags jsonb NOT NULL DEFAULT '[]'::jsonb,
  persona_version bigint NOT NULL DEFAULT 1,
  persona_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  work_style_version bigint NOT NULL DEFAULT 1,
  work_style_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'active',
  created_by text REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (brain_app_id, code),
  CONSTRAINT ck_rd_ai_employees_status CHECK (status IN ('active', 'disabled', 'retired')),
  CONSTRAINT ck_rd_ai_employees_versions CHECK (
    persona_version > 0 AND work_style_version > 0
  )
);

CREATE TABLE IF NOT EXISTS rd_executor_profiles (
  id text PRIMARY KEY,
  brain_app_id text NOT NULL DEFAULT 'rd_brain' REFERENCES brain_apps(id) ON DELETE RESTRICT,
  code text NOT NULL,
  name text NOT NULL,
  executor_type text NOT NULL,
  runner_id text REFERENCES ai_executor_runners(id) ON DELETE RESTRICT,
  model_gateway_config_id text REFERENCES model_gateway_configs(id) ON DELETE RESTRICT,
  credential_ref text,
  workspace_capabilities jsonb NOT NULL DEFAULT '{}'::jsonb,
  max_concurrency integer NOT NULL DEFAULT 1,
  supported_role_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
  health_status text NOT NULL DEFAULT 'unknown',
  status text NOT NULL DEFAULT 'active',
  created_by text REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (brain_app_id, code),
  CONSTRAINT ck_rd_executor_profiles_executor_type CHECK (
    executor_type IN ('model_gateway', 'codex', 'claude', 'hermes', 'openclaw', 'human')
  ),
  CONSTRAINT ck_rd_executor_profiles_concurrency CHECK (max_concurrency > 0),
  CONSTRAINT ck_rd_executor_profiles_health CHECK (
    health_status IN ('unknown', 'healthy', 'degraded', 'unavailable')
  ),
  CONSTRAINT ck_rd_executor_profiles_status CHECK (status IN ('active', 'disabled', 'retired'))
);

CREATE TABLE IF NOT EXISTS rd_task_executor_policy_role_bindings (
  id text PRIMARY KEY,
  policy_id text NOT NULL REFERENCES rd_task_executor_policies(id) ON DELETE RESTRICT,
  role_code text NOT NULL,
  actor_mode text NOT NULL,
  candidate_human_user_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  candidate_ai_employee_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  primary_executor_profile_id text REFERENCES rd_executor_profiles(id) ON DELETE RESTRICT,
  fallback_executor_profile_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  repository_trust_domains jsonb NOT NULL DEFAULT '[]'::jsonb,
  tool_trust_domains jsonb NOT NULL DEFAULT '[]'::jsonb,
  context_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  tool_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  budget_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  reviewer_role_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
  required_permissions jsonb NOT NULL DEFAULT '[]'::jsonb,
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (policy_id, role_code),
  CONSTRAINT ck_rd_policy_role_binding_actor_mode CHECK (
    actor_mode IN ('human', 'ai', 'hybrid')
  ),
  CONSTRAINT ck_rd_policy_role_binding_status CHECK (status IN ('active', 'disabled'))
);

CREATE TABLE IF NOT EXISTS rd_task_executor_policy_snapshots (
  id text PRIMARY KEY,
  policy_id text NOT NULL,
  policy_version bigint NOT NULL,
  parent_snapshot_id text REFERENCES rd_task_executor_policy_snapshots(id) ON DELETE RESTRICT,
  snapshot_kind text NOT NULL,
  resolution_context_key text NOT NULL,
  resolution_revision integer NOT NULL,
  schema_version bigint NOT NULL,
  content_hash text NOT NULL,
  payload_json jsonb NOT NULL,
  created_by text NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (policy_id, policy_version, snapshot_kind, resolution_context_key, resolution_revision),
  CONSTRAINT ck_rd_policy_snapshot_kind CHECK (
    snapshot_kind IN ('base', 'assessment_resolved', 'version_resolved')
  ),
  CONSTRAINT ck_rd_policy_snapshot_identity CHECK (
    (
      snapshot_kind = 'base'
      AND parent_snapshot_id IS NULL
      AND resolution_context_key = 'policy:' || policy_id || ':version:' || policy_version::text
      AND resolution_revision = 0
    ) OR (
      snapshot_kind = 'assessment_resolved'
      AND parent_snapshot_id IS NOT NULL
      AND resolution_context_key ~ '^assessment:[^:]+$'
      AND resolution_revision BETWEEN 1 AND 2
    ) OR (
      snapshot_kind = 'version_resolved'
      AND parent_snapshot_id IS NOT NULL
      AND resolution_context_key ~ '^version:[^:]+:scope:[0-9]+$'
      AND resolution_revision = 1
    )
  ),
  CONSTRAINT ck_rd_policy_snapshot_versions CHECK (
    policy_version > 0 AND schema_version > 0
  )
);

-- Snapshots preserve the version value that produced their payload, while the identity
-- FK deliberately follows only the stable policy row. The insert trigger below checks
-- that a newly frozen snapshot uses the policy's then-current version.
ALTER TABLE rd_task_executor_policy_snapshots
  DROP CONSTRAINT IF EXISTS fk_rd_policy_snapshot_policy_version;

ALTER TABLE rd_task_executor_policy_snapshots
  DROP CONSTRAINT IF EXISTS fk_rd_policy_snapshot_policy;

ALTER TABLE rd_task_executor_policy_snapshots
  ADD CONSTRAINT fk_rd_policy_snapshot_policy
  FOREIGN KEY (policy_id) REFERENCES rd_task_executor_policies(id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_rd_policy_snapshot_content_hash
  ON rd_task_executor_policy_snapshots (content_hash);

CREATE TABLE IF NOT EXISTS requirement_assessments (
  id text PRIMARY KEY,
  requirement_id text NOT NULL REFERENCES requirements(id) ON DELETE RESTRICT,
  requirement_revision bigint NOT NULL,
  initial_strategy_snapshot_id text NOT NULL REFERENCES rd_task_executor_policy_snapshots(id) ON DELETE RESTRICT,
  final_strategy_snapshot_id text NOT NULL REFERENCES rd_task_executor_policy_snapshots(id) ON DELETE RESTRICT,
  strategy_snapshot_id text NOT NULL REFERENCES rd_task_executor_policy_snapshots(id) ON DELETE RESTRICT,
  structured_assessment jsonb NOT NULL DEFAULT '{}'::jsonb,
  completeness_score numeric(7, 4),
  risk_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  dependency_summary jsonb NOT NULL DEFAULT '[]'::jsonb,
  effort_estimate jsonb NOT NULL DEFAULT '{}'::jsonb,
  candidate_version_id text REFERENCES product_versions(id) ON DELETE RESTRICT,
  assignment_reason text,
  status text NOT NULL DEFAULT 'draft',
  llm_suggestion jsonb NOT NULL DEFAULT '{}'::jsonb,
  deterministic_validation jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by text NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  decided_by text REFERENCES users(id) ON DELETE RESTRICT,
  decided_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_requirement_assessments_revision CHECK (requirement_revision > 0),
  CONSTRAINT ck_requirement_assessments_status CHECK (
    status IN (
      'draft', 'evaluating', 'waiting_human', 'needs_info', 'rework_required',
      'accepted', 'deferred', 'rejected', 'failed', 'cancelled'
    )
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS uk_requirement_assessment_active_revision_initial_snapshot
  ON requirement_assessments (requirement_id, requirement_revision, initial_strategy_snapshot_id)
  WHERE status IN ('draft', 'evaluating', 'waiting_human', 'needs_info', 'rework_required', 'accepted');

CREATE TABLE IF NOT EXISTS requirement_assessment_opinions (
  id text PRIMARY KEY,
  assessment_id text NOT NULL REFERENCES requirement_assessments(id) ON DELETE RESTRICT,
  role_code text NOT NULL,
  ai_employee_id text REFERENCES rd_ai_employees(id) ON DELETE RESTRICT,
  executor_profile_id text REFERENCES rd_executor_profiles(id) ON DELETE RESTRICT,
  input_revision bigint NOT NULL,
  strategy_snapshot_id text NOT NULL REFERENCES rd_task_executor_policy_snapshots(id) ON DELETE RESTRICT,
  opinion_round integer NOT NULL DEFAULT 1,
  conclusion_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  confidence numeric(7, 4),
  risk_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  cost_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (assessment_id, role_code, opinion_round),
  CONSTRAINT ck_requirement_assessment_opinion_round CHECK (opinion_round > 0)
);

CREATE TABLE IF NOT EXISTS decision_requests (
  id text PRIMARY KEY,
  brain_app_id text NOT NULL DEFAULT 'rd_brain' REFERENCES brain_apps(id) ON DELETE RESTRICT,
  product_id text NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
  subject_type text NOT NULL,
  subject_id text NOT NULL,
  decision_type text NOT NULL,
  plan_version bigint NOT NULL DEFAULT 0,
  options_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  options_hash text NOT NULL,
  evidence_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  recommendation_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  decision_actor_selector jsonb NOT NULL DEFAULT '{}'::jsonb,
  answer_actor_selector jsonb NOT NULL DEFAULT '{}'::jsonb,
  answer_schema jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'pending',
  selected_option_code text,
  answer_json jsonb,
  decided_by text REFERENCES users(id) ON DELETE RESTRICT,
  decided_at timestamptz,
  expires_at timestamptz NOT NULL,
  timeout_policy text NOT NULL DEFAULT 'escalate_keep_paused',
  escalation_target_selector jsonb NOT NULL DEFAULT '{}'::jsonb,
  escalation_level integer NOT NULL DEFAULT 0,
  expired_at timestamptz,
  expiry_event_id text,
  supersedes_decision_request_id text REFERENCES decision_requests(id) ON DELETE RESTRICT,
  version bigint NOT NULL DEFAULT 1,
  created_by text NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_decision_requests_status CHECK (
    status IN ('pending', 'waiting_more_info', 'approved', 'rejected', 'expired', 'cancelled')
  ),
  CONSTRAINT ck_decision_requests_timeout_policy CHECK (
    timeout_policy IN ('escalate_keep_paused')
  ),
  CONSTRAINT ck_decision_requests_versions CHECK (
    plan_version >= 0 AND escalation_level >= 0 AND version > 0
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS uk_decision_requests_active_subject_plan
  ON decision_requests (subject_type, subject_id, decision_type, plan_version)
  WHERE status IN ('pending', 'waiting_more_info');

CREATE INDEX IF NOT EXISTS idx_decision_requests_expiry_due
  ON decision_requests (expires_at, id)
  WHERE status IN ('pending', 'waiting_more_info');

CREATE UNIQUE INDEX IF NOT EXISTS uk_decision_requests_expiry_event
  ON decision_requests (expiry_event_id)
  WHERE expiry_event_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uk_decision_requests_supersedes
  ON decision_requests (supersedes_decision_request_id)
  WHERE supersedes_decision_request_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS rd_collaboration_runs (
  id text PRIMARY KEY,
  brain_app_id text NOT NULL DEFAULT 'rd_brain' REFERENCES brain_apps(id) ON DELETE RESTRICT,
  product_id text NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
  product_version_id text NOT NULL REFERENCES product_versions(id) ON DELETE RESTRICT,
  strategy_snapshot_id text NOT NULL REFERENCES rd_task_executor_policy_snapshots(id) ON DELETE RESTRICT,
  run_generation bigint NOT NULL DEFAULT 1,
  supersedes_run_id text REFERENCES rd_collaboration_runs(id) ON DELETE RESTRICT,
  scope_version bigint NOT NULL,
  plan_version bigint NOT NULL DEFAULT 0,
  status text NOT NULL DEFAULT 'draft',
  delivery_target text NOT NULL DEFAULT 'ready_for_release',
  budget_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  graph_definition text NOT NULL DEFAULT 'rd_collaboration',
  graph_version text NOT NULL,
  resume_state text,
  suspended_decision_request_id text REFERENCES decision_requests(id) ON DELETE RESTRICT,
  suspended_at timestamptz,
  completion_reason text,
  started_at timestamptz,
  completed_at timestamptz,
  version bigint NOT NULL DEFAULT 1,
  created_by text NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (product_version_id, run_generation),
  CONSTRAINT ck_rd_collaboration_runs_status CHECK (
    status IN (
      'draft', 'planning', 'running', 'waiting_human', 'integrating',
      'verifying', 'completed', 'failed', 'cancelled'
    )
  ),
  CONSTRAINT ck_rd_collaboration_run_versions CHECK (
    run_generation > 0 AND scope_version > 0 AND plan_version >= 0 AND version > 0
  ),
  CONSTRAINT ck_rd_collaboration_run_pause CHECK (
    (
      status = 'waiting_human'
      AND resume_state IN ('running', 'integrating', 'verifying')
      AND suspended_decision_request_id IS NOT NULL
      AND suspended_at IS NOT NULL
    ) OR (
      status <> 'waiting_human'
      AND resume_state IS NULL
      AND suspended_decision_request_id IS NULL
      AND suspended_at IS NULL
    )
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS uk_rd_collaboration_runs_active_version
  ON rd_collaboration_runs (product_version_id)
  WHERE status NOT IN ('completed', 'failed', 'cancelled');

CREATE UNIQUE INDEX IF NOT EXISTS uk_rd_collaboration_runs_supersedes
  ON rd_collaboration_runs (supersedes_run_id)
  WHERE supersedes_run_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_rd_collaboration_runs_suspended_decision
  ON rd_collaboration_runs (suspended_decision_request_id)
  WHERE status = 'waiting_human';

CREATE TABLE IF NOT EXISTS rd_task_executor_policy_snapshot_sources (
  id text PRIMARY KEY,
  snapshot_id text NOT NULL REFERENCES rd_task_executor_policy_snapshots(id) ON DELETE RESTRICT,
  source_snapshot_id text NOT NULL REFERENCES rd_task_executor_policy_snapshots(id) ON DELETE RESTRICT,
  requirement_id text NOT NULL REFERENCES requirements(id) ON DELETE RESTRICT,
  assessment_id text NOT NULL REFERENCES requirement_assessments(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (snapshot_id, requirement_id)
);

CREATE TABLE IF NOT EXISTS rd_collaboration_run_requirements (
  id text PRIMARY KEY,
  collaboration_run_id text NOT NULL REFERENCES rd_collaboration_runs(id) ON DELETE RESTRICT,
  requirement_id text NOT NULL REFERENCES requirements(id) ON DELETE RESTRICT,
  requirement_revision bigint NOT NULL,
  assessment_id text NOT NULL REFERENCES requirement_assessments(id) ON DELETE RESTRICT,
  final_strategy_snapshot_id text NOT NULL REFERENCES rd_task_executor_policy_snapshots(id) ON DELETE RESTRICT,
  acceptance_criteria_hash text NOT NULL,
  repository_scope_hash text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (collaboration_run_id, requirement_id),
  CONSTRAINT ck_rd_collaboration_run_requirement_revision CHECK (requirement_revision > 0)
);

CREATE TABLE IF NOT EXISTS rd_scope_change_requests (
  id text PRIMARY KEY,
  product_version_id text NOT NULL REFERENCES product_versions(id) ON DELETE RESTRICT,
  request_id text NOT NULL,
  source_run_id text NOT NULL REFERENCES rd_collaboration_runs(id) ON DELETE RESTRICT,
  source_run_state text NOT NULL,
  expected_scope_version bigint NOT NULL,
  expected_run_generation bigint NOT NULL,
  operations_json jsonb NOT NULL,
  operations_hash text NOT NULL,
  reason text NOT NULL,
  status text NOT NULL DEFAULT 'pending_decision',
  decision_request_id text NOT NULL REFERENCES decision_requests(id) ON DELETE RESTRICT,
  applied_scope_version bigint,
  requested_by text NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  applied_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (product_version_id, request_id),
  CONSTRAINT ck_rd_scope_change_request_status CHECK (
    status IN ('pending_decision', 'applied', 'rejected')
  ),
  CONSTRAINT ck_rd_scope_change_request_source_state CHECK (
    source_run_state IN (
      'draft', 'planning', 'running', 'waiting_human', 'integrating',
      'verifying', 'failed', 'cancelled'
    )
  ),
  CONSTRAINT ck_rd_scope_change_request_versions CHECK (
    expected_scope_version > 0 AND expected_run_generation > 0
  ),
  CONSTRAINT ck_rd_scope_change_request_state_fields CHECK (
    (
      status = 'pending_decision' AND decision_request_id IS NOT NULL
      AND applied_scope_version IS NULL AND applied_at IS NULL
    ) OR (
      status = 'applied' AND decision_request_id IS NOT NULL
      AND applied_scope_version IS NOT NULL AND applied_at IS NOT NULL
    ) OR (
      status = 'rejected' AND decision_request_id IS NOT NULL
      AND applied_scope_version IS NULL AND applied_at IS NULL
    )
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS uk_rd_scope_change_request_pending_version
  ON rd_scope_change_requests (product_version_id)
  WHERE status = 'pending_decision';

CREATE TABLE IF NOT EXISTS rd_scope_change_request_operations (
  id text PRIMARY KEY,
  scope_change_request_id text NOT NULL REFERENCES rd_scope_change_requests(id) ON DELETE RESTRICT,
  position integer NOT NULL,
  op text NOT NULL,
  requirement_id text REFERENCES requirements(id) ON DELETE RESTRICT,
  requirement_revision bigint,
  assessment_id text REFERENCES requirement_assessments(id) ON DELETE RESTRICT,
  final_strategy_snapshot_id text REFERENCES rd_task_executor_policy_snapshots(id) ON DELETE RESTRICT,
  repository_id text REFERENCES product_git_repositories(id) ON DELETE RESTRICT,
  branch_config_version bigint,
  base_commit_sha text,
  destination text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (scope_change_request_id, position),
  CONSTRAINT ck_rd_scope_change_operation_position CHECK (position >= 0),
  CONSTRAINT ck_rd_scope_change_operation_kind CHECK (
    op IN ('add_requirement', 'remove_requirement', 'replace_requirement_snapshot', 'update_repository_baseline')
  ),
  CONSTRAINT ck_rd_scope_change_operation_fields CHECK (
    (
      op = 'add_requirement'
      AND requirement_id IS NOT NULL AND requirement_revision IS NOT NULL
      AND assessment_id IS NOT NULL AND final_strategy_snapshot_id IS NOT NULL
      AND repository_id IS NULL AND branch_config_version IS NULL
      AND base_commit_sha IS NULL AND destination IS NULL
    ) OR (
      op = 'remove_requirement'
      AND requirement_id IS NOT NULL AND requirement_revision IS NULL
      AND assessment_id IS NULL AND final_strategy_snapshot_id IS NULL
      AND repository_id IS NULL AND branch_config_version IS NULL
      AND base_commit_sha IS NULL AND destination IS NOT NULL
      AND length(trim(destination)) > 0 AND destination = 'approved_pool'
    ) OR (
      op = 'replace_requirement_snapshot'
      AND requirement_id IS NOT NULL AND requirement_revision IS NOT NULL
      AND assessment_id IS NOT NULL AND final_strategy_snapshot_id IS NOT NULL
      AND repository_id IS NULL AND branch_config_version IS NULL
      AND base_commit_sha IS NULL AND destination IS NULL
    ) OR (
      op = 'update_repository_baseline'
      AND requirement_id IS NULL AND requirement_revision IS NULL
      AND assessment_id IS NULL AND final_strategy_snapshot_id IS NULL
      AND repository_id IS NOT NULL AND branch_config_version IS NOT NULL
      AND base_commit_sha IS NOT NULL AND destination IS NULL
    )
  )
);

ALTER TABLE IF EXISTS rd_scope_change_request_operations
  DROP CONSTRAINT IF EXISTS ck_rd_scope_change_operation_fields;

DROP TRIGGER IF EXISTS trg_rd_scope_change_request_operations_immutable
  ON rd_scope_change_request_operations;

UPDATE rd_scope_change_request_operations
SET destination = 'approved_pool'
WHERE op = 'remove_requirement'
  AND (destination IS NULL OR length(trim(destination)) = 0);

UPDATE rd_scope_change_request_operations
SET destination = NULL
WHERE op = 'update_repository_baseline'
  AND destination IS NOT NULL;

ALTER TABLE IF EXISTS rd_scope_change_request_operations
  ADD CONSTRAINT ck_rd_scope_change_operation_fields CHECK (
    (
      op = 'add_requirement'
      AND requirement_id IS NOT NULL AND requirement_revision IS NOT NULL
      AND assessment_id IS NOT NULL AND final_strategy_snapshot_id IS NOT NULL
      AND repository_id IS NULL AND branch_config_version IS NULL
      AND base_commit_sha IS NULL AND destination IS NULL
    ) OR (
      op = 'remove_requirement'
      AND requirement_id IS NOT NULL AND requirement_revision IS NULL
      AND assessment_id IS NULL AND final_strategy_snapshot_id IS NULL
      AND repository_id IS NULL AND branch_config_version IS NULL
      AND base_commit_sha IS NULL AND destination IS NOT NULL
      AND length(trim(destination)) > 0 AND destination = 'approved_pool'
    ) OR (
      op = 'replace_requirement_snapshot'
      AND requirement_id IS NOT NULL AND requirement_revision IS NOT NULL
      AND assessment_id IS NOT NULL AND final_strategy_snapshot_id IS NOT NULL
      AND repository_id IS NULL AND branch_config_version IS NULL
      AND base_commit_sha IS NULL AND destination IS NULL
    ) OR (
      op = 'update_repository_baseline'
      AND requirement_id IS NULL AND requirement_revision IS NULL
      AND assessment_id IS NULL AND final_strategy_snapshot_id IS NULL
      AND repository_id IS NOT NULL AND branch_config_version IS NOT NULL
      AND base_commit_sha IS NOT NULL AND destination IS NULL
    )
  );

ALTER TABLE IF EXISTS requirements
  ADD COLUMN IF NOT EXISTS supersedes_requirement_id text REFERENCES requirements(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS source_collaboration_run_id text REFERENCES rd_collaboration_runs(id) ON DELETE RESTRICT;

ALTER TABLE IF EXISTS requirements
  DROP CONSTRAINT IF EXISTS ck_requirements_supersedes_source_run;

ALTER TABLE IF EXISTS requirements
  ADD CONSTRAINT ck_requirements_supersedes_source_run CHECK (
    supersedes_requirement_id IS NULL OR source_collaboration_run_id IS NOT NULL
  );

CREATE INDEX IF NOT EXISTS idx_requirements_collaboration_lineage
  ON requirements (supersedes_requirement_id, source_collaboration_run_id);

CREATE TABLE IF NOT EXISTS rd_run_seats (
  id text PRIMARY KEY,
  collaboration_run_id text NOT NULL REFERENCES rd_collaboration_runs(id) ON DELETE RESTRICT,
  role_code text NOT NULL,
  subject_type text NOT NULL,
  human_user_id text REFERENCES users(id) ON DELETE RESTRICT,
  ai_employee_id text REFERENCES rd_ai_employees(id) ON DELETE RESTRICT,
  executor_profile_id text REFERENCES rd_executor_profiles(id) ON DELETE RESTRICT,
  responsibility_scope jsonb NOT NULL DEFAULT '{}'::jsonb,
  capacity integer NOT NULL DEFAULT 1,
  status text NOT NULL DEFAULT 'active',
  replaces_seat_id text REFERENCES rd_run_seats(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (collaboration_run_id, role_code),
  UNIQUE (collaboration_run_id, id),
  CONSTRAINT ck_rd_run_seat_subject_type CHECK (subject_type IN ('human_user', 'ai_employee')),
  CONSTRAINT ck_rd_run_seat_subject CHECK (
    (subject_type = 'human_user' AND human_user_id IS NOT NULL AND ai_employee_id IS NULL)
    OR (subject_type = 'ai_employee' AND ai_employee_id IS NOT NULL AND human_user_id IS NULL AND executor_profile_id IS NOT NULL)
  ),
  CONSTRAINT ck_rd_run_seat_capacity CHECK (capacity > 0),
  CONSTRAINT ck_rd_run_seat_status CHECK (status IN ('active', 'suspended', 'replaced', 'released'))
);

CREATE TABLE IF NOT EXISTS rd_role_sessions (
  id text PRIMARY KEY,
  collaboration_run_id text NOT NULL REFERENCES rd_collaboration_runs(id) ON DELETE RESTRICT,
  seat_id text NOT NULL REFERENCES rd_run_seats(id) ON DELETE RESTRICT,
  session_no integer NOT NULL,
  handoff_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  context_cursor jsonb NOT NULL DEFAULT '{}'::jsonb,
  resume_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'active',
  started_at timestamptz NOT NULL DEFAULT now(),
  ended_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (seat_id, session_no),
  CONSTRAINT ck_rd_role_session_no CHECK (session_no > 0),
  CONSTRAINT ck_rd_role_session_status CHECK (status IN ('active', 'handed_off', 'closed'))
);

CREATE TABLE IF NOT EXISTS rd_work_items (
  id text PRIMARY KEY,
  collaboration_run_id text NOT NULL REFERENCES rd_collaboration_runs(id) ON DELETE RESTRICT,
  plan_version bigint NOT NULL,
  work_item_type text NOT NULL,
  title text NOT NULL,
  objective text NOT NULL,
  owner_seat_id text REFERENCES rd_run_seats(id) ON DELETE RESTRICT,
  input_contract jsonb NOT NULL DEFAULT '{}'::jsonb,
  output_contract jsonb NOT NULL DEFAULT '{}'::jsonb,
  acceptance_criteria jsonb NOT NULL DEFAULT '[]'::jsonb,
  status text NOT NULL DEFAULT 'draft',
  resume_state text,
  suspended_attempt_id text,
  suspended_decision_request_id text REFERENCES decision_requests(id) ON DELETE RESTRICT,
  suspended_at timestamptz,
  release_conditions jsonb NOT NULL DEFAULT '[]'::jsonb,
  risk_level text NOT NULL DEFAULT 'medium',
  priority integer NOT NULL DEFAULT 100,
  ai_task_id text REFERENCES ai_tasks(id) ON DELETE RESTRICT,
  reviewer_seat_id text REFERENCES rd_run_seats(id) ON DELETE RESTRICT,
  lease_owner text,
  lease_expires_at timestamptz,
  idempotency_key text NOT NULL,
  version bigint NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (collaboration_run_id, idempotency_key),
  CONSTRAINT ck_rd_work_item_status CHECK (
    status IN (
      'draft', 'ready', 'claimed', 'running', 'waiting_human', 'blocked',
      'reviewing', 'completed', 'failed', 'cancelled'
    )
  ),
  CONSTRAINT ck_rd_work_item_pause CHECK (
    (
      status = 'waiting_human'
      AND resume_state IN ('ready', 'claimed', 'running', 'reviewing')
      AND suspended_decision_request_id IS NOT NULL AND suspended_at IS NOT NULL
    ) OR (
      status <> 'waiting_human'
      AND resume_state IS NULL AND suspended_decision_request_id IS NULL AND suspended_at IS NULL
    )
  ),
  CONSTRAINT ck_rd_work_items_version CHECK (version > 0)
);

ALTER TABLE IF EXISTS rd_work_items
  ADD COLUMN IF NOT EXISTS version bigint NOT NULL DEFAULT 1;

ALTER TABLE IF EXISTS rd_work_items
  DROP CONSTRAINT IF EXISTS ck_rd_work_items_version;

ALTER TABLE IF EXISTS rd_work_items
  ADD CONSTRAINT ck_rd_work_items_version CHECK (version > 0);

CREATE TABLE IF NOT EXISTS rd_work_item_dependencies (
  id text PRIMARY KEY,
  collaboration_run_id text NOT NULL REFERENCES rd_collaboration_runs(id) ON DELETE RESTRICT,
  plan_version bigint NOT NULL,
  predecessor_work_item_id text NOT NULL REFERENCES rd_work_items(id) ON DELETE RESTRICT,
  successor_work_item_id text NOT NULL REFERENCES rd_work_items(id) ON DELETE RESTRICT,
  dependency_type text NOT NULL DEFAULT 'finish_to_start',
  status text NOT NULL DEFAULT 'pending',
  satisfied_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (
    collaboration_run_id, plan_version, predecessor_work_item_id,
    successor_work_item_id, dependency_type
  ),
  CONSTRAINT ck_rd_work_item_dependency_self CHECK (
    predecessor_work_item_id <> successor_work_item_id
  ),
  CONSTRAINT ck_rd_work_item_dependency_status CHECK (status IN ('pending', 'satisfied', 'waived'))
);

CREATE TABLE IF NOT EXISTS rd_work_item_attempts (
  id text PRIMARY KEY,
  work_item_id text NOT NULL REFERENCES rd_work_items(id) ON DELETE RESTRICT,
  attempt_no integer NOT NULL,
  idempotency_key text NOT NULL,
  lease_id text,
  lease_token_hash text,
  status text NOT NULL DEFAULT 'claimed',
  executor_profile_id text REFERENCES rd_executor_profiles(id) ON DELETE RESTRICT,
  input_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  result_json jsonb,
  failure_json jsonb,
  rework_evidence jsonb NOT NULL DEFAULT '[]'::jsonb,
  claimed_at timestamptz NOT NULL DEFAULT now(),
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (work_item_id, attempt_no),
  UNIQUE (work_item_id, idempotency_key),
  CONSTRAINT ck_rd_work_item_attempt_no CHECK (attempt_no > 0),
  CONSTRAINT ck_rd_work_item_attempt_status CHECK (
    status IN ('claimed', 'running', 'waiting_human', 'completed', 'failed', 'cancelled', 'expired')
  )
);

ALTER TABLE IF EXISTS rd_work_items
  DROP CONSTRAINT IF EXISTS fk_rd_work_items_suspended_attempt;

ALTER TABLE IF EXISTS rd_work_items
  ADD CONSTRAINT fk_rd_work_items_suspended_attempt
  FOREIGN KEY (suspended_attempt_id) REFERENCES rd_work_item_attempts(id) ON DELETE RESTRICT;

CREATE TABLE IF NOT EXISTS rd_collaboration_events (
  id text PRIMARY KEY,
  collaboration_run_id text NOT NULL REFERENCES rd_collaboration_runs(id) ON DELETE RESTRICT,
  event_type text NOT NULL,
  event_key text NOT NULL,
  subject_type text NOT NULL,
  subject_id text NOT NULL,
  payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (collaboration_run_id, id),
  UNIQUE (collaboration_run_id, event_key)
);

ALTER TABLE IF EXISTS decision_requests
  DROP CONSTRAINT IF EXISTS fk_decision_requests_expiry_event;

ALTER TABLE IF EXISTS decision_requests
  ADD CONSTRAINT fk_decision_requests_expiry_event
  FOREIGN KEY (expiry_event_id) REFERENCES rd_collaboration_events(id) ON DELETE RESTRICT;

CREATE TABLE IF NOT EXISTS rd_command_idempotency_records (
  id text PRIMARY KEY,
  command_type text NOT NULL,
  aggregate_type text NOT NULL,
  aggregate_id text NOT NULL,
  idempotency_key text NOT NULL,
  request_hash text NOT NULL,
  result_type text NOT NULL,
  result_id text NOT NULL,
  http_status integer NOT NULL,
  response_hash text NOT NULL,
  response_json jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (command_type, aggregate_type, aggregate_id, idempotency_key),
  CONSTRAINT ck_rd_command_idempotency_http_status CHECK (http_status BETWEEN 100 AND 599)
);

CREATE TABLE IF NOT EXISTS rd_command_replay_secrets (
  id text PRIMARY KEY,
  command_record_id text NOT NULL REFERENCES rd_command_idempotency_records(id) ON DELETE RESTRICT,
  secret_ciphertext text,
  key_id text NOT NULL,
  expires_at timestamptz NOT NULL,
  scrubbed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (command_record_id),
  CONSTRAINT ck_rd_command_replay_secret_scrub CHECK (
    (secret_ciphertext IS NOT NULL AND scrubbed_at IS NULL)
    OR (secret_ciphertext IS NULL AND scrubbed_at IS NOT NULL)
  )
);

CREATE TABLE IF NOT EXISTS role_feedback_records (
  id text PRIMARY KEY,
  brain_app_id text NOT NULL DEFAULT 'rd_brain' REFERENCES brain_apps(id) ON DELETE RESTRICT,
  product_id text NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
  collaboration_run_id text NOT NULL REFERENCES rd_collaboration_runs(id) ON DELETE RESTRICT,
  feedback_kind text NOT NULL,
  source_event_id text NOT NULL,
  feedback_fingerprint text NOT NULL,
  role_code text NOT NULL,
  seat_id text REFERENCES rd_run_seats(id) ON DELETE RESTRICT,
  human_user_id text REFERENCES users(id) ON DELETE RESTRICT,
  ai_employee_id text REFERENCES rd_ai_employees(id) ON DELETE RESTRICT,
  executor_profile_id text REFERENCES rd_executor_profiles(id) ON DELETE RESTRICT,
  work_item_id text REFERENCES rd_work_items(id) ON DELETE RESTRICT,
  attempt_id text REFERENCES rd_work_item_attempts(id) ON DELETE RESTRICT,
  strategy_snapshot_id text NOT NULL REFERENCES rd_task_executor_policy_snapshots(id) ON DELETE RESTRICT,
  evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  producer_subject_type text NOT NULL,
  producer_subject_id text NOT NULL,
  producer_role_code text,
  producer_seat_id text REFERENCES rd_run_seats(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (collaboration_run_id, feedback_fingerprint),
  CONSTRAINT fk_role_feedback_source_event FOREIGN KEY (collaboration_run_id, source_event_id)
    REFERENCES rd_collaboration_events(collaboration_run_id, id) ON DELETE RESTRICT,
  CONSTRAINT ck_role_feedback_attributed_subject CHECK (
    (human_user_id IS NOT NULL AND ai_employee_id IS NULL)
    OR (human_user_id IS NULL AND ai_employee_id IS NOT NULL)
  ),
  CONSTRAINT ck_role_feedback_producer_type CHECK (
    producer_subject_type IN ('human_user', 'ai_employee', 'service')
  ),
  CONSTRAINT ck_role_feedback_producer_service CHECK (
    producer_subject_type <> 'service'
    OR producer_subject_id IN (
      'collaboration_orchestrator', 'quality_gate', 'delivery_reconciler', 'decision_expiry_worker'
    )
  ),
  CONSTRAINT ck_role_feedback_producer_role_seat CHECK (
    (producer_role_code IS NULL AND producer_seat_id IS NULL)
    OR (producer_role_code IS NOT NULL AND producer_seat_id IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_role_feedback_producer
  ON role_feedback_records (
    producer_subject_type, producer_subject_id, producer_role_code, producer_seat_id
  );

CREATE TABLE IF NOT EXISTS rd_role_experience_records (
  id text PRIMARY KEY,
  experience_key text NOT NULL,
  version bigint NOT NULL,
  brain_app_id text NOT NULL DEFAULT 'rd_brain' REFERENCES brain_apps(id) ON DELETE RESTRICT,
  product_scope jsonb NOT NULL DEFAULT '[]'::jsonb,
  role_code text NOT NULL,
  work_item_type text NOT NULL,
  scenario text NOT NULL,
  risk_scope jsonb NOT NULL DEFAULT '{}'::jsonb,
  repository_trust_domains jsonb NOT NULL DEFAULT '[]'::jsonb,
  tool_trust_domains jsonb NOT NULL DEFAULT '[]'::jsonb,
  content jsonb NOT NULL,
  evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  strategy_snapshot_id text NOT NULL REFERENCES rd_task_executor_policy_snapshots(id) ON DELETE RESTRICT,
  confidence numeric(7, 4) NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  review_version bigint NOT NULL DEFAULT 1,
  reviewed_by text REFERENCES users(id) ON DELETE RESTRICT,
  reviewed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (experience_key, version),
  CONSTRAINT ck_rd_role_experience_versions CHECK (version > 0 AND review_version > 0),
  CONSTRAINT ck_rd_role_experience_confidence CHECK (confidence BETWEEN 0 AND 1),
  CONSTRAINT ck_rd_role_experience_status CHECK (
    status IN ('pending', 'approved', 'rejected', 'retired')
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS uk_rd_role_experience_one_approved
  ON rd_role_experience_records (experience_key)
  WHERE status = 'approved';

CREATE TABLE IF NOT EXISTS rd_role_experience_sources (
  id text PRIMARY KEY,
  experience_id text NOT NULL REFERENCES rd_role_experience_records(id) ON DELETE RESTRICT,
  role_feedback_record_id text NOT NULL REFERENCES role_feedback_records(id) ON DELETE RESTRICT,
  strategy_snapshot_id text NOT NULL REFERENCES rd_task_executor_policy_snapshots(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (experience_id, role_feedback_record_id)
);

CREATE TABLE IF NOT EXISTS rd_collaboration_upgrade_state (
  id text PRIMARY KEY,
  fence_mode text NOT NULL DEFAULT 'disabled',
  version bigint NOT NULL DEFAULT 1,
  schema_version bigint NOT NULL DEFAULT 1,
  fence_reason text,
  advisory_preflight_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  locked_preflight_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  active_counts_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  backup_marker text,
  cutover_started_at timestamptz,
  cleanup_started_at timestamptz,
  cleanup_completed_at timestamptz,
  v2_api_version text,
  v2_worker_version text,
  v2_graph_version text,
  health_marker text,
  smoke_test_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  abort_reason text,
  abort_actor_id text REFERENCES users(id) ON DELETE RESTRICT,
  aborted_at timestamptz,
  fence_released_at timestamptz,
  fence_release_evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_rd_collaboration_upgrade_fence CHECK (
    fence_mode IN ('disabled', 'draining', 'cutover_locked')
  ),
  CONSTRAINT ck_rd_collaboration_upgrade_versions CHECK (version > 0 AND schema_version > 0)
);

INSERT INTO rd_collaboration_upgrade_state (id, fence_mode, version, schema_version)
VALUES ('rd_collaboration', 'disabled', 1, 1)
ON CONFLICT (id) DO NOTHING;

ALTER TABLE IF EXISTS ai_tasks
  ADD COLUMN IF NOT EXISTS collaboration_run_id text REFERENCES rd_collaboration_runs(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS work_item_id text REFERENCES rd_work_items(id) ON DELETE RESTRICT;

ALTER TABLE IF EXISTS graph_runs
  ALTER COLUMN ai_task_id DROP NOT NULL,
  ADD COLUMN IF NOT EXISTS subject_type text,
  ADD COLUMN IF NOT EXISTS subject_id text,
  ADD COLUMN IF NOT EXISTS thread_id text,
  ADD COLUMN IF NOT EXISTS graph_definition text,
  ADD COLUMN IF NOT EXISTS graph_version text;

UPDATE graph_runs
SET
  subject_type = COALESCE(subject_type, 'ai_task'),
  subject_id = COALESCE(subject_id, ai_task_id),
  thread_id = COALESCE(thread_id, 'ai_task:' || ai_task_id),
  graph_definition = COALESCE(graph_definition, 'ai_task'),
  graph_version = COALESCE(graph_version, 'v1')
WHERE ai_task_id IS NOT NULL;

ALTER TABLE IF EXISTS graph_checkpoints
  ALTER COLUMN ai_task_id DROP NOT NULL,
  ADD COLUMN IF NOT EXISTS subject_type text,
  ADD COLUMN IF NOT EXISTS subject_id text,
  ADD COLUMN IF NOT EXISTS thread_id text,
  ADD COLUMN IF NOT EXISTS graph_definition text,
  ADD COLUMN IF NOT EXISTS graph_version text;

UPDATE graph_checkpoints checkpoint
SET
  subject_type = COALESCE(checkpoint.subject_type, run.subject_type, 'ai_task'),
  subject_id = COALESCE(checkpoint.subject_id, run.subject_id, checkpoint.ai_task_id),
  thread_id = COALESCE(checkpoint.thread_id, run.thread_id, 'ai_task:' || checkpoint.ai_task_id),
  graph_definition = COALESCE(checkpoint.graph_definition, run.graph_definition, 'ai_task'),
  graph_version = COALESCE(checkpoint.graph_version, run.graph_version, 'v1')
FROM graph_runs run
WHERE run.id = checkpoint.graph_run_id;

CREATE UNIQUE INDEX IF NOT EXISTS uk_graph_runs_thread_id
  ON graph_runs (thread_id) WHERE thread_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_graph_checkpoints_subject
  ON graph_checkpoints (subject_type, subject_id, created_at DESC);

CREATE OR REPLACE FUNCTION reject_immutable_rd_collaboration_fact_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'immutable collaboration fact rows cannot be updated or deleted';
END;
$$;

DROP TRIGGER IF EXISTS trg_rd_task_executor_policy_snapshots_immutable
  ON rd_task_executor_policy_snapshots;

CREATE TRIGGER trg_rd_task_executor_policy_snapshots_immutable
BEFORE UPDATE OR DELETE ON rd_task_executor_policy_snapshots
FOR EACH ROW EXECUTE FUNCTION reject_immutable_rd_collaboration_fact_mutation();

DROP TRIGGER IF EXISTS trg_rd_task_executor_policy_snapshot_sources_immutable
  ON rd_task_executor_policy_snapshot_sources;

CREATE TRIGGER trg_rd_task_executor_policy_snapshot_sources_immutable
BEFORE UPDATE OR DELETE ON rd_task_executor_policy_snapshot_sources
FOR EACH ROW EXECUTE FUNCTION reject_immutable_rd_collaboration_fact_mutation();

DROP TRIGGER IF EXISTS trg_rd_collaboration_run_requirements_immutable
  ON rd_collaboration_run_requirements;

CREATE TRIGGER trg_rd_collaboration_run_requirements_immutable
BEFORE UPDATE OR DELETE ON rd_collaboration_run_requirements
FOR EACH ROW EXECUTE FUNCTION reject_immutable_rd_collaboration_fact_mutation();

DROP TRIGGER IF EXISTS trg_rd_scope_change_request_operations_immutable
  ON rd_scope_change_request_operations;

CREATE TRIGGER trg_rd_scope_change_request_operations_immutable
BEFORE UPDATE OR DELETE ON rd_scope_change_request_operations
FOR EACH ROW EXECUTE FUNCTION reject_immutable_rd_collaboration_fact_mutation();

DROP TRIGGER IF EXISTS trg_rd_command_idempotency_records_immutable
  ON rd_command_idempotency_records;

CREATE TRIGGER trg_rd_command_idempotency_records_immutable
BEFORE UPDATE OR DELETE ON rd_command_idempotency_records
FOR EACH ROW EXECUTE FUNCTION reject_immutable_rd_collaboration_fact_mutation();

DROP TRIGGER IF EXISTS trg_role_feedback_records_immutable
  ON role_feedback_records;

CREATE TRIGGER trg_role_feedback_records_immutable
BEFORE UPDATE OR DELETE ON role_feedback_records
FOR EACH ROW EXECUTE FUNCTION reject_immutable_rd_collaboration_fact_mutation();

CREATE OR REPLACE FUNCTION validate_rd_policy_snapshot_parent_integrity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  parent_row rd_task_executor_policy_snapshots%ROWTYPE;
BEGIN
  IF NEW.snapshot_kind = 'base' THEN
    RETURN NEW;
  END IF;
  SELECT * INTO parent_row
  FROM rd_task_executor_policy_snapshots
  WHERE id = NEW.parent_snapshot_id;
  IF NOT FOUND
     OR parent_row.policy_id <> NEW.policy_id
     OR parent_row.policy_version <> NEW.policy_version THEN
    RAISE EXCEPTION 'policy snapshot parent must use the same policy id and version';
  END IF;
  IF NEW.snapshot_kind = 'version_resolved' AND parent_row.snapshot_kind <> 'base' THEN
    RAISE EXCEPTION 'version_resolved snapshot parent must be base';
  END IF;
  IF NEW.snapshot_kind = 'assessment_resolved'
     AND parent_row.snapshot_kind NOT IN ('base', 'assessment_resolved') THEN
    RAISE EXCEPTION 'assessment_resolved snapshot parent is invalid';
  END IF;
  IF NEW.snapshot_kind = 'version_resolved' THEN
    IF NOT EXISTS (
      SELECT 1
      FROM product_versions version
      JOIN rd_task_executor_policies policy ON policy.id = NEW.policy_id
      WHERE NEW.resolution_context_key =
        'version:' || version.id || ':scope:' || version.scope_version::text
        AND (policy.product_id IS NULL OR policy.product_id = version.product_id)
    ) THEN
      RAISE EXCEPTION 'version_resolved snapshot must match current version scope and policy ownership';
    END IF;
    IF NOT EXISTS (
      SELECT 1
      FROM rd_task_executor_policy_snapshot_sources source
      WHERE source.snapshot_id = NEW.id
    ) THEN
      RAISE EXCEPTION 'version_resolved snapshot must have immutable source coverage';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION validate_rd_policy_snapshot_current_policy_version()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  current_policy_version bigint;
BEGIN
  SELECT policy_version INTO current_policy_version
  FROM rd_task_executor_policies
  WHERE id = NEW.policy_id;
  IF NOT FOUND OR current_policy_version IS DISTINCT FROM NEW.policy_version THEN
    RAISE EXCEPTION 'policy snapshot version must equal the current policy version';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_rd_policy_snapshot_current_policy_version
  ON rd_task_executor_policy_snapshots;

CREATE TRIGGER trg_rd_policy_snapshot_current_policy_version
BEFORE INSERT ON rd_task_executor_policy_snapshots
FOR EACH ROW EXECUTE FUNCTION validate_rd_policy_snapshot_current_policy_version();

DROP TRIGGER IF EXISTS trg_rd_policy_snapshot_parent_integrity
  ON rd_task_executor_policy_snapshots;

CREATE CONSTRAINT TRIGGER trg_rd_policy_snapshot_parent_integrity
AFTER INSERT ON rd_task_executor_policy_snapshots
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION validate_rd_policy_snapshot_parent_integrity();

CREATE OR REPLACE FUNCTION validate_requirement_assessment_snapshot_integrity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  initial_snapshot rd_task_executor_policy_snapshots%ROWTYPE;
  final_snapshot rd_task_executor_policy_snapshots%ROWTYPE;
  prior_revision_snapshot rd_task_executor_policy_snapshots%ROWTYPE;
BEGIN
  SELECT * INTO initial_snapshot
  FROM rd_task_executor_policy_snapshots WHERE id = NEW.initial_strategy_snapshot_id;
  SELECT * INTO final_snapshot
  FROM rd_task_executor_policy_snapshots WHERE id = NEW.final_strategy_snapshot_id;
  IF initial_snapshot.snapshot_kind <> 'base'
     OR final_snapshot.snapshot_kind NOT IN ('base', 'assessment_resolved') THEN
    RAISE EXCEPTION 'requirement assessment strategy snapshot kinds are invalid';
  END IF;
  IF NEW.strategy_snapshot_id <> NEW.final_strategy_snapshot_id THEN
    RAISE EXCEPTION 'strategy_snapshot_id must equal final_strategy_snapshot_id';
  END IF;
  IF final_snapshot.snapshot_kind = 'base' THEN
    IF final_snapshot.id <> initial_snapshot.id THEN
      RAISE EXCEPTION 'assessment snapshot base must equal its initial snapshot root';
    END IF;
    RETURN NEW;
  END IF;
  IF final_snapshot.policy_id <> initial_snapshot.policy_id
     OR final_snapshot.policy_version <> initial_snapshot.policy_version
     OR final_snapshot.resolution_context_key <> 'assessment:' || NEW.id THEN
    RAISE EXCEPTION 'assessment snapshot must match assessment context and initial root policy';
  END IF;
  IF final_snapshot.resolution_revision = 1 THEN
    IF final_snapshot.parent_snapshot_id <> initial_snapshot.id THEN
      RAISE EXCEPTION 'assessment snapshot revision 1 must descend from its initial root';
    END IF;
  ELSIF final_snapshot.resolution_revision = 2 THEN
    SELECT * INTO prior_revision_snapshot
    FROM rd_task_executor_policy_snapshots
    WHERE id = final_snapshot.parent_snapshot_id;
    IF NOT FOUND
       OR prior_revision_snapshot.snapshot_kind <> 'assessment_resolved'
       OR prior_revision_snapshot.policy_id <> initial_snapshot.policy_id
       OR prior_revision_snapshot.policy_version <> initial_snapshot.policy_version
       OR prior_revision_snapshot.resolution_context_key <> 'assessment:' || NEW.id
       OR prior_revision_snapshot.resolution_revision <> 1
       OR prior_revision_snapshot.parent_snapshot_id <> initial_snapshot.id THEN
      RAISE EXCEPTION 'assessment snapshot revision 2 must follow revision 1 from its initial root';
    END IF;
  ELSE
    RAISE EXCEPTION 'assessment snapshot revision is invalid';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_requirement_assessment_snapshot_integrity
  ON requirement_assessments;

CREATE CONSTRAINT TRIGGER trg_requirement_assessment_snapshot_integrity
AFTER INSERT OR UPDATE OF id, initial_strategy_snapshot_id, final_strategy_snapshot_id, strategy_snapshot_id
ON requirement_assessments
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION validate_requirement_assessment_snapshot_integrity();

CREATE OR REPLACE FUNCTION protect_referenced_requirement_assessment_provenance()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF ROW(
    NEW.requirement_id, NEW.requirement_revision,
    NEW.initial_strategy_snapshot_id, NEW.final_strategy_snapshot_id,
    NEW.strategy_snapshot_id, NEW.status
  ) IS DISTINCT FROM ROW(
    OLD.requirement_id, OLD.requirement_revision,
    OLD.initial_strategy_snapshot_id, OLD.final_strategy_snapshot_id,
    OLD.strategy_snapshot_id, OLD.status
  ) THEN
    IF OLD.status = 'accepted' THEN
      RAISE EXCEPTION 'accepted assessment provenance is immutable; create a new assessment';
    END IF;
    IF EXISTS (
      SELECT 1 FROM rd_task_executor_policy_snapshot_sources
      WHERE assessment_id = OLD.id
    ) OR EXISTS (
      SELECT 1 FROM rd_collaboration_run_requirements
      WHERE assessment_id = OLD.id
    ) THEN
      RAISE EXCEPTION 'referenced assessment provenance is immutable';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_requirement_assessment_provenance_immutable
  ON requirement_assessments;

CREATE TRIGGER trg_requirement_assessment_provenance_immutable
BEFORE UPDATE ON requirement_assessments
FOR EACH ROW EXECUTE FUNCTION protect_referenced_requirement_assessment_provenance();

CREATE OR REPLACE FUNCTION validate_rd_collaboration_run_integrity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  previous_run rd_collaboration_runs%ROWTYPE;
BEGIN
  IF TG_OP = 'INSERT' THEN
    IF NOT EXISTS (
      SELECT 1
      FROM rd_task_executor_policy_snapshots snapshot
      JOIN rd_task_executor_policies policy ON policy.id = snapshot.policy_id
      JOIN product_versions version ON version.id = NEW.product_version_id
      WHERE snapshot.id = NEW.strategy_snapshot_id
        AND snapshot.snapshot_kind = 'version_resolved'
        AND snapshot.resolution_context_key =
          'version:' || NEW.product_version_id || ':scope:' || NEW.scope_version::text
        AND version.product_id = NEW.product_id
        AND version.scope_version = NEW.scope_version
        AND policy.brain_app_id = NEW.brain_app_id
        AND (policy.product_id IS NULL OR policy.product_id = NEW.product_id)
    ) THEN
      RAISE EXCEPTION 'collaboration run snapshot must match version, scope, and current ownership';
    END IF;
  ELSIF NOT EXISTS (
    SELECT 1
    FROM rd_task_executor_policy_snapshots snapshot
    WHERE snapshot.id = NEW.strategy_snapshot_id
      AND snapshot.snapshot_kind = 'version_resolved'
      AND snapshot.resolution_context_key =
        'version:' || NEW.product_version_id || ':scope:' || NEW.scope_version::text
  ) THEN
    RAISE EXCEPTION 'collaboration run snapshot must match frozen version and scope';
  END IF;
  IF NEW.supersedes_run_id IS NOT NULL THEN
    SELECT * INTO previous_run FROM rd_collaboration_runs WHERE id = NEW.supersedes_run_id;
    IF NOT FOUND
       OR previous_run.product_version_id <> NEW.product_version_id
       OR previous_run.status NOT IN ('failed', 'cancelled')
       OR previous_run.run_generation + 1 <> NEW.run_generation THEN
      RAISE EXCEPTION 'superseded run must be the previous failed or cancelled generation';
    END IF;
  ELSIF NEW.run_generation <> 1 THEN
    RAISE EXCEPTION 'non-initial generation must supersede the previous generation';
  END IF;
  IF TG_OP = 'UPDATE'
     AND OLD.status IN ('completed', 'failed', 'cancelled')
     AND NEW.status NOT IN ('completed', 'failed', 'cancelled') THEN
    RAISE EXCEPTION 'terminal collaboration runs cannot be reopened';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_rd_collaboration_run_integrity
  ON rd_collaboration_runs;

CREATE CONSTRAINT TRIGGER trg_rd_collaboration_run_integrity
AFTER INSERT OR UPDATE ON rd_collaboration_runs
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION validate_rd_collaboration_run_integrity();

CREATE OR REPLACE FUNCTION protect_rd_collaboration_run_scope_identity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF OLD.status IN ('failed', 'cancelled') THEN
    RAISE EXCEPTION 'failed or cancelled terminal collaboration runs are immutable';
  END IF;
  IF ROW(
    NEW.brain_app_id, NEW.product_id, NEW.product_version_id,
    NEW.strategy_snapshot_id, NEW.run_generation, NEW.supersedes_run_id,
    NEW.scope_version
  ) IS DISTINCT FROM ROW(
    OLD.brain_app_id, OLD.product_id, OLD.product_version_id,
    OLD.strategy_snapshot_id, OLD.run_generation, OLD.supersedes_run_id,
    OLD.scope_version
  ) THEN
    RAISE EXCEPTION 'collaboration run scope and generation identity are immutable';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_rd_collaboration_run_scope_identity_immutable
  ON rd_collaboration_runs;

CREATE TRIGGER trg_rd_collaboration_run_scope_identity_immutable
BEFORE UPDATE ON rd_collaboration_runs
FOR EACH ROW EXECUTE FUNCTION protect_rd_collaboration_run_scope_identity();

CREATE OR REPLACE FUNCTION validate_rd_collaboration_scope_integrity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  run_row rd_collaboration_runs%ROWTYPE;
  source_count bigint;
  scope_count bigint;
  mismatch_count bigint;
BEGIN
  IF TG_TABLE_NAME = 'rd_task_executor_policy_snapshot_sources' THEN
    IF NOT EXISTS (
      SELECT 1
      FROM rd_task_executor_policy_snapshots target_snapshot
      JOIN rd_task_executor_policy_snapshots source_snapshot
        ON source_snapshot.id = NEW.source_snapshot_id
      JOIN requirement_assessments assessment
        ON assessment.id = NEW.assessment_id
      WHERE target_snapshot.id = NEW.snapshot_id
        AND target_snapshot.snapshot_kind = 'version_resolved'
        AND source_snapshot.snapshot_kind IN ('base', 'assessment_resolved')
        AND target_snapshot.policy_id = source_snapshot.policy_id
        AND target_snapshot.policy_version = source_snapshot.policy_version
        AND assessment.requirement_id = NEW.requirement_id
        AND assessment.status = 'accepted'
        AND assessment.final_strategy_snapshot_id = NEW.source_snapshot_id
    ) THEN
      RAISE EXCEPTION 'snapshot source must use accepted assessment final snapshot with same policy id and version';
    END IF;
  END IF;

  IF TG_TABLE_NAME = 'rd_collaboration_runs' THEN
    run_row := NEW;
  ELSIF TG_TABLE_NAME = 'rd_collaboration_run_requirements' THEN
    SELECT * INTO run_row FROM rd_collaboration_runs WHERE id = NEW.collaboration_run_id;
  ELSE
    SELECT run.* INTO run_row
    FROM rd_collaboration_runs run
    WHERE run.strategy_snapshot_id = NEW.snapshot_id
    ORDER BY run.created_at DESC
    LIMIT 1;
    IF NOT FOUND THEN
      RETURN NEW;
    END IF;
  END IF;

  SELECT count(*) INTO scope_count
  FROM rd_collaboration_run_requirements scope_row
  WHERE scope_row.collaboration_run_id = run_row.id;
  IF scope_count < 1 THEN
    RAISE EXCEPTION 'collaboration run exact run requirement scope must contain at least one row';
  END IF;

  SELECT count(*) INTO source_count
  FROM rd_task_executor_policy_snapshot_sources source_row
  WHERE source_row.snapshot_id = run_row.strategy_snapshot_id;
  IF source_count <> scope_count THEN
    RAISE EXCEPTION 'snapshot source_count must equal run scope_count';
  END IF;

  SELECT count(*) INTO mismatch_count
  FROM rd_collaboration_run_requirements scope_row
  FULL JOIN (
    SELECT *
    FROM rd_task_executor_policy_snapshot_sources
    WHERE snapshot_id = run_row.strategy_snapshot_id
  ) source_row
    ON source_row.requirement_id = scope_row.requirement_id
  LEFT JOIN requirement_assessments assessment
    ON assessment.id = COALESCE(scope_row.assessment_id, source_row.assessment_id)
  LEFT JOIN rd_task_executor_policy_snapshots target_snapshot
    ON target_snapshot.id = run_row.strategy_snapshot_id
  LEFT JOIN rd_task_executor_policy_snapshots source_snapshot
    ON source_snapshot.id = source_row.source_snapshot_id
  WHERE (scope_row.collaboration_run_id = run_row.id OR scope_row.collaboration_run_id IS NULL)
    AND (
      scope_row.requirement_id IS NULL OR source_row.requirement_id IS NULL
      OR scope_row.assessment_id <> source_row.assessment_id
      OR scope_row.final_strategy_snapshot_id <> source_row.source_snapshot_id
      OR assessment.status <> 'accepted'
      OR assessment.requirement_revision <> scope_row.requirement_revision
      OR assessment.final_strategy_snapshot_id <> scope_row.final_strategy_snapshot_id
      OR target_snapshot.policy_id <> source_snapshot.policy_id
      OR target_snapshot.policy_version <> source_snapshot.policy_version
    );
  IF mismatch_count <> 0 THEN
    RAISE EXCEPTION 'snapshot sources must provide exact run requirement scope with same policy id and version';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_rd_policy_snapshot_source_integrity
  ON rd_task_executor_policy_snapshot_sources;

CREATE CONSTRAINT TRIGGER trg_rd_policy_snapshot_source_integrity
AFTER INSERT ON rd_task_executor_policy_snapshot_sources
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION validate_rd_collaboration_scope_integrity();

DROP TRIGGER IF EXISTS trg_rd_collaboration_run_scope_integrity
  ON rd_collaboration_run_requirements;

CREATE CONSTRAINT TRIGGER trg_rd_collaboration_run_scope_integrity
AFTER INSERT ON rd_collaboration_run_requirements
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION validate_rd_collaboration_scope_integrity();

DROP TRIGGER IF EXISTS trg_rd_collaboration_run_requires_scope
  ON rd_collaboration_runs;

CREATE CONSTRAINT TRIGGER trg_rd_collaboration_run_requires_scope
AFTER INSERT ON rd_collaboration_runs
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION validate_rd_collaboration_scope_integrity();

CREATE OR REPLACE FUNCTION protect_rd_scope_change_request_proposal()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF ROW(
    NEW.product_version_id, NEW.request_id, NEW.source_run_id, NEW.source_run_state,
    NEW.expected_scope_version, NEW.expected_run_generation, NEW.operations_json,
    NEW.operations_hash, NEW.reason, NEW.requested_by
  ) IS DISTINCT FROM ROW(
    OLD.product_version_id, OLD.request_id, OLD.source_run_id, OLD.source_run_state,
    OLD.expected_scope_version, OLD.expected_run_generation, OLD.operations_json,
    OLD.operations_hash, OLD.reason, OLD.requested_by
  ) THEN
    RAISE EXCEPTION 'scope change proposal fields are immutable';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_rd_scope_change_request_proposal_immutable
  ON rd_scope_change_requests;

CREATE TRIGGER trg_rd_scope_change_request_proposal_immutable
BEFORE UPDATE ON rd_scope_change_requests
FOR EACH ROW EXECUTE FUNCTION protect_rd_scope_change_request_proposal();

CREATE OR REPLACE FUNCTION validate_requirement_lineage_integrity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  previous_product_id text;
  source_product_id text;
  source_version_status text;
BEGIN
  IF NEW.source_collaboration_run_id IS NULL THEN
    RETURN NEW;
  END IF;
  SELECT run.product_id, version.status
  INTO source_product_id, source_version_status
  FROM rd_collaboration_runs run
  JOIN product_versions version ON version.id = run.product_version_id
  WHERE run.id = NEW.source_collaboration_run_id;
  IF source_product_id IS DISTINCT FROM NEW.product_id
     OR source_version_status NOT IN ('ready_for_release', 'deploying', 'released') THEN
    RAISE EXCEPTION 'requirement lineage source run must be same product and ready for release';
  END IF;
  IF NEW.supersedes_requirement_id IS NOT NULL THEN
    SELECT product_id INTO previous_product_id
    FROM requirements WHERE id = NEW.supersedes_requirement_id;
    IF previous_product_id IS DISTINCT FROM NEW.product_id THEN
      RAISE EXCEPTION 'superseded requirement must belong to the same product';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_requirement_lineage_integrity
  ON requirements;

CREATE CONSTRAINT TRIGGER trg_requirement_lineage_integrity
AFTER INSERT OR UPDATE OF supersedes_requirement_id, source_collaboration_run_id, product_id
ON requirements
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION validate_requirement_lineage_integrity();

CREATE OR REPLACE FUNCTION protect_decision_expiry_definition()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF ROW(
    NEW.expires_at, NEW.timeout_policy, NEW.escalation_target_selector,
    NEW.escalation_level, NEW.supersedes_decision_request_id
  ) IS DISTINCT FROM ROW(
    OLD.expires_at, OLD.timeout_policy, OLD.escalation_target_selector,
    OLD.escalation_level, OLD.supersedes_decision_request_id
  ) THEN
    RAISE EXCEPTION 'decision expiry and escalation definition is frozen';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_decision_request_expiry_definition_immutable
  ON decision_requests;

CREATE TRIGGER trg_decision_request_expiry_definition_immutable
BEFORE UPDATE ON decision_requests
FOR EACH ROW EXECUTE FUNCTION protect_decision_expiry_definition();

CREATE OR REPLACE FUNCTION validate_role_feedback_producer_subject()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  locked_subject_id text;
BEGIN
  IF NEW.producer_subject_type = 'human_user' THEN
    SELECT id INTO locked_subject_id
    FROM users
    WHERE id = NEW.producer_subject_id
    FOR KEY SHARE;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'feedback producer human user does not exist';
    END IF;
  ELSIF NEW.producer_subject_type = 'ai_employee' THEN
    SELECT id INTO locked_subject_id
    FROM rd_ai_employees
    WHERE id = NEW.producer_subject_id
    FOR KEY SHARE;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'feedback producer ai employee does not exist';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_role_feedback_producer_subject
  ON role_feedback_records;

CREATE CONSTRAINT TRIGGER trg_role_feedback_producer_subject
AFTER INSERT ON role_feedback_records
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION validate_role_feedback_producer_subject();

CREATE OR REPLACE FUNCTION validate_role_feedback_producer_seat_role()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  seat_role text;
  seat_run_id text;
  seat_subject_type text;
  seat_subject_id text;
BEGIN
  IF NEW.producer_seat_id IS NULL THEN
    RETURN NEW;
  END IF;
  SELECT
    role_code,
    collaboration_run_id,
    subject_type,
    CASE
      WHEN subject_type = 'human_user' THEN human_user_id
      WHEN subject_type = 'ai_employee' THEN ai_employee_id
    END
  INTO seat_role, seat_run_id, seat_subject_type, seat_subject_id
  FROM rd_run_seats
  WHERE id = NEW.producer_seat_id
  FOR KEY SHARE;
  IF seat_role IS DISTINCT FROM NEW.producer_role_code
     OR seat_run_id IS DISTINCT FROM NEW.collaboration_run_id THEN
    RAISE EXCEPTION 'feedback producer frozen role and run must match producer seat';
  END IF;
  IF NEW.producer_subject_type = 'service'
     OR seat_subject_type IS DISTINCT FROM NEW.producer_subject_type
     OR seat_subject_id IS DISTINCT FROM NEW.producer_subject_id THEN
    RAISE EXCEPTION 'feedback producer seat subject must match producer subject type and id';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_role_feedback_producer_seat_role
  ON role_feedback_records;

CREATE CONSTRAINT TRIGGER trg_role_feedback_producer_seat_role
AFTER INSERT ON role_feedback_records
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION validate_role_feedback_producer_seat_role();

CREATE OR REPLACE FUNCTION protect_feedback_referenced_rd_run_seat_identity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF ROW(
    NEW.collaboration_run_id, NEW.role_code, NEW.subject_type,
    NEW.human_user_id, NEW.ai_employee_id
  ) IS DISTINCT FROM ROW(
    OLD.collaboration_run_id, OLD.role_code, OLD.subject_type,
    OLD.human_user_id, OLD.ai_employee_id
  ) THEN
    RAISE EXCEPTION 'feedback-referenced seat identity is immutable from creation';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_rd_run_seat_feedback_identity_immutable
  ON rd_run_seats;

CREATE TRIGGER trg_rd_run_seat_feedback_identity_immutable
BEFORE UPDATE ON rd_run_seats
FOR EACH ROW EXECUTE FUNCTION protect_feedback_referenced_rd_run_seat_identity();

CREATE OR REPLACE FUNCTION protect_role_feedback_polymorphic_producer_identity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  feedback_subject_type text;
BEGIN
  IF TG_OP = 'UPDATE' AND NEW.id IS NOT DISTINCT FROM OLD.id THEN
    RETURN NEW;
  END IF;
  feedback_subject_type := CASE
    WHEN TG_TABLE_NAME = 'users' THEN 'human_user'
    WHEN TG_TABLE_NAME = 'rd_ai_employees' THEN 'ai_employee'
  END;
  IF EXISTS (
    SELECT 1
    FROM role_feedback_records feedback
    WHERE feedback.producer_subject_type = feedback_subject_type
      AND feedback.producer_subject_id = OLD.id
  ) THEN
    RAISE EXCEPTION 'feedback producer identity cannot be changed or deleted';
  END IF;
  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_users_feedback_producer_identity
  ON users;

CREATE TRIGGER trg_users_feedback_producer_identity
BEFORE UPDATE OR DELETE ON users
FOR EACH ROW EXECUTE FUNCTION protect_role_feedback_polymorphic_producer_identity();

DROP TRIGGER IF EXISTS trg_rd_ai_employees_feedback_producer_identity
  ON rd_ai_employees;

CREATE TRIGGER trg_rd_ai_employees_feedback_producer_identity
BEFORE UPDATE OR DELETE ON rd_ai_employees
FOR EACH ROW EXECUTE FUNCTION protect_role_feedback_polymorphic_producer_identity();

CREATE OR REPLACE FUNCTION scrub_expired_rd_command_replay_secrets()
RETURNS bigint
LANGUAGE plpgsql
AS $$
DECLARE
  scrubbed_count bigint;
BEGIN
  UPDATE rd_command_replay_secrets
  SET secret_ciphertext = NULL, scrubbed_at = now(), updated_at = now()
  WHERE expires_at <= now() AND secret_ciphertext IS NOT NULL;
  GET DIAGNOSTICS scrubbed_count = ROW_COUNT;
  RETURN scrubbed_count;
END;
$$;

COMMENT ON FUNCTION scrub_expired_rd_command_replay_secrets()
  IS 'Idempotently scrubs expired claim secrets; replay returns RD_CLAIM_LEASE_EXPIRED.';

INSERT INTO permissions (code, name, category, description, risk_level, is_system, status)
VALUES
  ('delivery.rd_roles.manage', '管理研发岗位', 'delivery', '维护研发协作岗位定义。', 'high', true, 'active'),
  ('delivery.rd_ai_employees.manage', '管理 AI 数字员工', 'delivery', '维护稳定 AI 数字员工身份。', 'high', true, 'active'),
  ('delivery.rd_executor_profiles.manage', '管理研发执行器档案', 'delivery', '维护研发执行器能力档案。', 'high', true, 'active'),
  ('delivery.requirement_assessments.read', '查看需求评估', 'delivery', '查看正式需求评估。', 'normal', true, 'active'),
  ('delivery.requirement_assessments.decide', '决策需求评估', 'delivery', '确认正式需求评估。', 'high', true, 'active'),
  ('delivery.rd_collaboration.read', '查看研发协作', 'delivery', '查看版本研发协作。', 'normal', true, 'active'),
  ('delivery.rd_collaboration.plan', '规划研发协作', 'delivery', '规划版本研发协作。', 'high', true, 'active'),
  ('delivery.rd_collaboration.work', '执行研发协作', 'delivery', '执行席位内研发工作。', 'high', true, 'active'),
  ('delivery.decision_requests.decide', '处理研发决策', 'delivery', '处理研发协作高风险决策。', 'critical', true, 'active'),
  ('delivery.decision_requests.answer', '补充研发决策信息', 'delivery', '按冻结选择器补充决策信息。', 'high', true, 'active'),
  ('delivery.rd_role_experiences.read', '查看岗位经验', 'delivery', '查看岗位经验候选和批准版本。', 'normal', true, 'active'),
  ('delivery.rd_role_experiences.decide', '审核岗位经验', 'delivery', '审核和退役岗位经验版本。', 'high', true, 'active')
ON CONFLICT (code) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_code, granted_by)
SELECT role.id, permission.code, 'user_admin'
FROM roles role
CROSS JOIN permissions permission
WHERE role.code = 'admin'
  AND permission.code IN (
    'delivery.rd_roles.manage', 'delivery.rd_ai_employees.manage',
    'delivery.rd_executor_profiles.manage', 'delivery.requirement_assessments.read',
    'delivery.requirement_assessments.decide', 'delivery.rd_collaboration.read',
    'delivery.rd_collaboration.plan', 'delivery.rd_collaboration.work',
    'delivery.decision_requests.decide', 'delivery.decision_requests.answer',
    'delivery.rd_role_experiences.read', 'delivery.rd_role_experiences.decide'
  )
ON CONFLICT (role_id, permission_code) DO UPDATE SET
  granted_by = EXCLUDED.granted_by,
  updated_at = now();

-- immutable runtime grants
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ai_brain_app_runtime') THEN
    EXECUTE 'GRANT SELECT, INSERT ON rd_task_executor_policy_snapshots TO ai_brain_app_runtime';
    EXECUTE 'GRANT SELECT, INSERT ON rd_task_executor_policy_snapshot_sources TO ai_brain_app_runtime';
    EXECUTE 'GRANT SELECT, INSERT ON rd_collaboration_run_requirements TO ai_brain_app_runtime';
    EXECUTE 'GRANT SELECT, INSERT ON rd_scope_change_request_operations TO ai_brain_app_runtime';
    EXECUTE 'GRANT SELECT, INSERT ON rd_command_idempotency_records TO ai_brain_app_runtime';
    EXECUTE 'GRANT SELECT, INSERT ON role_feedback_records TO ai_brain_app_runtime';
  END IF;
END;
$$;
