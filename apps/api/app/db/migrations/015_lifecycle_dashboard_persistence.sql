ALTER TABLE lifecycle_context_edges
  ADD COLUMN IF NOT EXISTS summary text;

ALTER TABLE lifecycle_risk_signals
  ADD COLUMN IF NOT EXISTS version_id text,
  ADD COLUMN IF NOT EXISTS module_code text,
  ADD COLUMN IF NOT EXISTS requirement_id text,
  ADD COLUMN IF NOT EXISTS task_id text;

CREATE TABLE IF NOT EXISTS dashboard_metric_snapshots (
  id text PRIMARY KEY,
  product_id text,
  time_range text NOT NULL DEFAULT 'all',
  window_start timestamptz,
  window_end timestamptz,
  metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_dashboard_product_window
  ON dashboard_metric_snapshots (product_id, window_start, window_end);

CREATE INDEX IF NOT EXISTS idx_dashboard_updated_at
  ON dashboard_metric_snapshots (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_lifecycle_risk_requirement
  ON lifecycle_risk_signals (requirement_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_lifecycle_risk_task
  ON lifecycle_risk_signals (task_id, observed_at DESC);
