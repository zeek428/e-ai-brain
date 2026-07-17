-- Durable Task 6 orchestration state.  Assessment commands are append-only
-- idempotency records; request/response snapshots are never process-local.

ALTER TABLE requirements
  ADD COLUMN IF NOT EXISTS assessment_revision bigint NOT NULL DEFAULT 1;

ALTER TABLE requirement_assessments
  ADD COLUMN IF NOT EXISTS version bigint NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS opinion_round integer NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS product_id text REFERENCES products(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS decision_action text,
  ADD COLUMN IF NOT EXISTS decision_comment text,
  ADD COLUMN IF NOT EXISTS proposed_policy_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS proposed_risk_level text,
  ADD COLUMN IF NOT EXISTS assessment_outcome text,
  ADD COLUMN IF NOT EXISTS assessment_evidence jsonb NOT NULL DEFAULT '[]'::jsonb;

UPDATE requirement_assessments assessment
SET product_id = requirement.product_id
FROM requirements requirement
WHERE assessment.requirement_id = requirement.id
  AND assessment.product_id IS NULL;

ALTER TABLE requirement_assessments
  ALTER COLUMN product_id SET NOT NULL;

ALTER TABLE requirement_assessments
  DROP CONSTRAINT IF EXISTS ck_requirement_assessments_decision_action,
  ADD CONSTRAINT ck_requirement_assessments_decision_action
  CHECK (decision_action IS NULL OR decision_action IN (
    'accept', 'reject', 'request_more_info', 'request_rework', 'defer'
  ));

ALTER TABLE requirement_assessment_opinions
  ADD COLUMN IF NOT EXISTS actor_id text,
  ADD COLUMN IF NOT EXISTS candidate_human_user_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS assigned_subject_type text,
  ADD COLUMN IF NOT EXISTS assigned_user_id text REFERENCES users(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS assigned_ai_employee_id text REFERENCES rd_ai_employees(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS execution_id text,
  ADD COLUMN IF NOT EXISTS policy_proposal_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS outcome_code text,
  ADD COLUMN IF NOT EXISTS risk_level text;

ALTER TABLE requirement_assessment_opinions
  DROP CONSTRAINT IF EXISTS ck_requirement_assessment_opinion_subject,
  ADD CONSTRAINT ck_requirement_assessment_opinion_subject
  CHECK (
    (assigned_subject_type = 'human_user' AND assigned_user_id IS NOT NULL AND assigned_ai_employee_id IS NULL)
    OR (assigned_subject_type = 'ai_employee' AND assigned_ai_employee_id IS NOT NULL AND assigned_user_id IS NULL)
    OR (assigned_subject_type IS NULL AND assigned_user_id IS NULL AND assigned_ai_employee_id IS NULL)
  );

CREATE TABLE IF NOT EXISTS requirement_assessment_executions (
  id text PRIMARY KEY,
  assessment_id text NOT NULL REFERENCES requirement_assessments(id) ON DELETE RESTRICT,
  opinion_id text NOT NULL REFERENCES requirement_assessment_opinions(id) ON DELETE RESTRICT,
  role_code text NOT NULL,
  actor_type text NOT NULL CHECK (actor_type IN ('human_user', 'ai_employee')),
  human_user_id text REFERENCES users(id) ON DELETE RESTRICT,
  ai_employee_id text REFERENCES rd_ai_employees(id) ON DELETE RESTRICT,
  executor_profile_id text REFERENCES rd_executor_profiles(id) ON DELETE RESTRICT,
  input_revision bigint NOT NULL,
  strategy_snapshot_id text NOT NULL REFERENCES rd_task_executor_policy_snapshots(id) ON DELETE RESTRICT,
  execution_kind text NOT NULL DEFAULT 'assessment_only' CHECK (execution_kind = 'assessment_only'),
  side_effect_policy text NOT NULL DEFAULT 'no_code_git_deploy_runner_work_item'
    CHECK (side_effect_policy = 'no_code_git_deploy_runner_work_item'),
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'cancelled')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (
    (actor_type = 'human_user' AND human_user_id IS NOT NULL AND ai_employee_id IS NULL)
    OR (actor_type = 'ai_employee' AND ai_employee_id IS NOT NULL AND human_user_id IS NULL)
  ),
  UNIQUE (opinion_id)
);

ALTER TABLE requirement_assessment_opinions
  DROP CONSTRAINT IF EXISTS fk_requirement_assessment_opinion_execution,
  ADD CONSTRAINT fk_requirement_assessment_opinion_execution
  FOREIGN KEY (execution_id) REFERENCES requirement_assessment_executions(id) ON DELETE RESTRICT;

CREATE TABLE IF NOT EXISTS requirement_assessment_answer_revisions (
  id text PRIMARY KEY,
  assessment_id text NOT NULL REFERENCES requirement_assessments(id) ON DELETE RESTRICT,
  requirement_id text NOT NULL REFERENCES requirements(id) ON DELETE RESTRICT,
  requirement_revision bigint NOT NULL,
  opinion_round integer NOT NULL,
  answers_json jsonb NOT NULL,
  actor_id text NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (assessment_id, requirement_revision)
);

CREATE TABLE IF NOT EXISTS requirement_assessment_commands (
  id text PRIMARY KEY,
  assessment_id text NOT NULL REFERENCES requirement_assessments(id) ON DELETE RESTRICT,
  operation text NOT NULL,
  idempotency_key text NOT NULL,
  request_hash text NOT NULL,
  response_snapshot jsonb NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed')),
  created_by text NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (assessment_id, operation, idempotency_key)
);

ALTER TABLE requirement_assessment_commands
  ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'pending';

ALTER TABLE requirement_assessment_commands
  DROP CONSTRAINT IF EXISTS ck_requirement_assessment_command_operation,
  ADD CONSTRAINT ck_requirement_assessment_command_operation
  CHECK (operation IN ('start', 'opinion', 'answers', 'decision', 'finalize'));

CREATE INDEX IF NOT EXISTS idx_requirement_assessment_commands_lookup
  ON requirement_assessment_commands (assessment_id, operation, created_at DESC);
