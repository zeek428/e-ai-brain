CREATE TABLE IF NOT EXISTS user_feedback (
  id text PRIMARY KEY,
  product_id text NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  module_code text,
  feature_code text,
  source_channel text NOT NULL DEFAULT 'in_app',
  feedback_type text NOT NULL,
  sentiment text,
  satisfaction_score integer,
  content text NOT NULL,
  tags jsonb NOT NULL DEFAULT '[]'::jsonb,
  related_requirement_id text REFERENCES requirements(id) ON DELETE SET NULL,
  status text NOT NULL DEFAULT 'open',
  triage_note text,
  created_by text NOT NULL REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_user_feedback_status
    CHECK (status IN ('open', 'triaged', 'linked', 'resolved', 'archived')),
  CONSTRAINT ck_user_feedback_type
    CHECK (feedback_type IN ('improvement', 'bug', 'question', 'complaint', 'praise')),
  CONSTRAINT ck_user_feedback_sentiment
    CHECK (sentiment IS NULL OR sentiment IN ('positive', 'neutral', 'negative')),
  CONSTRAINT ck_user_feedback_satisfaction_score
    CHECK (satisfaction_score IS NULL OR satisfaction_score BETWEEN 1 AND 5)
);

ALTER TABLE user_feedback ADD COLUMN IF NOT EXISTS module_code text;
ALTER TABLE user_feedback ADD COLUMN IF NOT EXISTS feature_code text;
ALTER TABLE user_feedback ADD COLUMN IF NOT EXISTS source_channel text NOT NULL DEFAULT 'in_app';
ALTER TABLE user_feedback ADD COLUMN IF NOT EXISTS feedback_type text NOT NULL DEFAULT 'improvement';
ALTER TABLE user_feedback ADD COLUMN IF NOT EXISTS sentiment text;
ALTER TABLE user_feedback ADD COLUMN IF NOT EXISTS satisfaction_score integer;
ALTER TABLE user_feedback ADD COLUMN IF NOT EXISTS tags jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE user_feedback ADD COLUMN IF NOT EXISTS related_requirement_id text REFERENCES requirements(id) ON DELETE SET NULL;
ALTER TABLE user_feedback ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'open';
ALTER TABLE user_feedback ADD COLUMN IF NOT EXISTS triage_note text;
ALTER TABLE user_feedback ADD COLUMN IF NOT EXISTS created_by text REFERENCES users(id);
ALTER TABLE user_feedback ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE user_feedback ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_user_feedback_product_status
  ON user_feedback (product_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_feedback_module_feature
  ON user_feedback (product_id, module_code, feature_code);

CREATE INDEX IF NOT EXISTS idx_user_feedback_created_by
  ON user_feedback (created_by, created_at DESC);
