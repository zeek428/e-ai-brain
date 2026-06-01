CREATE TABLE IF NOT EXISTS iteration_plan_suggestions (
  id text PRIMARY KEY,
  product_id text NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  planning_cycle text NOT NULL,
  version_id text REFERENCES product_versions(id) ON DELETE SET NULL,
  module_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
  title text NOT NULL,
  status text NOT NULL DEFAULT 'suggested',
  priority text NOT NULL DEFAULT 'P2',
  priority_score integer NOT NULL DEFAULT 0,
  confidence_level text NOT NULL DEFAULT 'low',
  recommendation_reason text NOT NULL,
  business_value text NOT NULL,
  risk_signals jsonb NOT NULL DEFAULT '[]'::jsonb,
  dependencies jsonb NOT NULL DEFAULT '[]'::jsonb,
  estimated_effort text NOT NULL DEFAULT 'medium',
  evidence jsonb NOT NULL DEFAULT '[]'::jsonb,
  evidence_insufficient boolean NOT NULL DEFAULT false,
  created_by text NOT NULL REFERENCES users(id),
  converted_requirement_id text REFERENCES requirements(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_iteration_suggestion_status
    CHECK (status IN ('draft', 'suggested', 'accepted', 'edited_accepted', 'rejected', 'converted_to_requirement')),
  CONSTRAINT ck_iteration_suggestion_priority
    CHECK (priority IN ('P0', 'P1', 'P2', 'P3')),
  CONSTRAINT ck_iteration_suggestion_priority_score
    CHECK (priority_score BETWEEN 0 AND 100),
  CONSTRAINT ck_iteration_suggestion_confidence
    CHECK (confidence_level IN ('low', 'medium', 'high')),
  CONSTRAINT ck_iteration_suggestion_effort
    CHECK (estimated_effort IN ('low', 'medium', 'high'))
);

CREATE TABLE IF NOT EXISTS iteration_plan_decisions (
  id text PRIMARY KEY,
  suggestion_id text NOT NULL REFERENCES iteration_plan_suggestions(id) ON DELETE CASCADE,
  decision text NOT NULL,
  comment text,
  edited_title text,
  edited_scope text,
  convert_to_requirement boolean NOT NULL DEFAULT false,
  created_requirement_id text REFERENCES requirements(id) ON DELETE SET NULL,
  decided_by text NOT NULL REFERENCES users(id),
  decided_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_iteration_decision
    CHECK (decision IN ('accepted', 'edited_accepted', 'rejected'))
);

CREATE INDEX IF NOT EXISTS idx_iteration_plan_product_cycle
  ON iteration_plan_suggestions (product_id, planning_cycle, priority_score DESC);

CREATE INDEX IF NOT EXISTS idx_iteration_plan_status
  ON iteration_plan_suggestions (status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_iteration_plan_decision_suggestion
  ON iteration_plan_decisions (suggestion_id, decided_at DESC);
