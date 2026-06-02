CREATE TABLE IF NOT EXISTS pending_attribution_items (
  id text PRIMARY KEY,
  source_type text NOT NULL,
  source_system text NOT NULL,
  collector_run_id text REFERENCES collector_runs(id) ON DELETE SET NULL,
  raw_subject_id text,
  summary text NOT NULL,
  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  suggested_product_id text REFERENCES products(id) ON DELETE SET NULL,
  suggested_module_code text,
  confidence numeric(5,4),
  status text NOT NULL DEFAULT 'pending',
  resolution_action text,
  resolution_note text,
  resolved_product_id text REFERENCES products(id) ON DELETE SET NULL,
  resolved_module_code text,
  resolved_requirement_id text REFERENCES requirements(id) ON DELETE SET NULL,
  resolved_subject_type text,
  resolved_subject_id text,
  resolved_by text REFERENCES users(id) ON DELETE SET NULL,
  resolved_at timestamptz,
  created_by text REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_pending_attribution_source_type
    CHECK (
      source_type IN (
        'gitlab_daily_code_metric',
        'jenkins_release',
        'online_log_metric',
        'user_usage_metric',
        'user_feedback',
        'iteration_plan_suggestion'
      )
    ),
  CONSTRAINT ck_pending_attribution_status
    CHECK (status IN ('pending', 'resolved', 'ignored')),
  CONSTRAINT ck_pending_attribution_resolution_action
    CHECK (
      resolution_action IS NULL
      OR resolution_action IN ('link_existing_context', 'ignore_as_noise')
    ),
  CONSTRAINT ck_pending_attribution_source_system
    CHECK (length(trim(source_system)) > 0),
  CONSTRAINT ck_pending_attribution_summary
    CHECK (length(trim(summary)) > 0),
  CONSTRAINT ck_pending_attribution_confidence
    CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
  CONSTRAINT ck_pending_attribution_terminal_resolution
    CHECK (
      (status = 'pending' AND resolved_at IS NULL AND resolved_by IS NULL)
      OR (status IN ('resolved', 'ignored') AND resolved_at IS NOT NULL AND resolved_by IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_pending_attribution_status_created
  ON pending_attribution_items (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pending_attribution_source_created
  ON pending_attribution_items (source_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pending_attribution_resolved_product
  ON pending_attribution_items (resolved_product_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_pending_attribution_collector_run
  ON pending_attribution_items (collector_run_id);
