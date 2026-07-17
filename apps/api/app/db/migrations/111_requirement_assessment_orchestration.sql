-- Durable Task 6 orchestration state.  Assessment commands are append-only
-- idempotency records; request/response snapshots are never process-local.

ALTER TABLE requirements
  ADD COLUMN IF NOT EXISTS assessment_revision bigint NOT NULL DEFAULT 1;

ALTER TABLE requirement_assessments
  ADD COLUMN IF NOT EXISTS version bigint NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS opinion_round integer NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS product_id text REFERENCES products(id) ON DELETE RESTRICT;

ALTER TABLE requirement_assessment_opinions
  ADD COLUMN IF NOT EXISTS actor_id text,
  ADD COLUMN IF NOT EXISTS candidate_human_user_ids jsonb NOT NULL DEFAULT '[]'::jsonb;

CREATE TABLE IF NOT EXISTS requirement_assessment_commands (
  id text PRIMARY KEY,
  assessment_id text NOT NULL REFERENCES requirement_assessments(id) ON DELETE RESTRICT,
  operation text NOT NULL,
  idempotency_key text NOT NULL,
  request_hash text NOT NULL,
  response_snapshot jsonb NOT NULL,
  created_by text NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (assessment_id, operation, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_requirement_assessment_commands_lookup
  ON requirement_assessment_commands (assessment_id, operation, created_at DESC);
