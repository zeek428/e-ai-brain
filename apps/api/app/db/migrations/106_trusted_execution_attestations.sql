ALTER TABLE ai_executor_runners
  ADD COLUMN IF NOT EXISTS trust_domain text NOT NULL DEFAULT 'coding';

ALTER TABLE ai_executor_runners
  ADD COLUMN IF NOT EXISTS trust_boundary_id text;

ALTER TABLE ai_executor_runners
  ADD COLUMN IF NOT EXISTS attestation_public_key text;

ALTER TABLE ai_executor_runners
  ADD COLUMN IF NOT EXISTS attestation_key_fingerprint text;

ALTER TABLE ai_executor_runners
  ADD COLUMN IF NOT EXISTS attestation_status text NOT NULL DEFAULT 'pending';

ALTER TABLE ai_executor_runners
  DROP CONSTRAINT IF EXISTS ck_ai_executor_runners_trust_domain;

ALTER TABLE ai_executor_runners
  ADD CONSTRAINT ck_ai_executor_runners_trust_domain CHECK (
    trust_domain IN ('coding', 'verification', 'deployment')
  );

ALTER TABLE ai_executor_runners
  DROP CONSTRAINT IF EXISTS ck_ai_executor_runners_attestation_status;

ALTER TABLE ai_executor_runners
  ADD CONSTRAINT ck_ai_executor_runners_attestation_status CHECK (
    attestation_status IN ('pending', 'active', 'revoked')
  );

CREATE TABLE IF NOT EXISTS execution_attestations (
  id text PRIMARY KEY,
  subject_type text NOT NULL,
  subject_id text NOT NULL,
  runner_task_id text NOT NULL UNIQUE,
  runner_id text NOT NULL,
  trust_domain text NOT NULL,
  trust_boundary_id text,
  payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  payload_sha256 text NOT NULL,
  signature text,
  public_key_fingerprint text,
  verification_status text NOT NULL,
  verification_error_code text,
  verified_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_execution_attestations_status CHECK (
    verification_status IN ('verified', 'blocked', 'invalid')
  )
);

CREATE INDEX IF NOT EXISTS idx_execution_attestations_subject
  ON execution_attestations (subject_type, subject_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_execution_attestations_runner
  ON execution_attestations (runner_id, verification_status, created_at DESC);
