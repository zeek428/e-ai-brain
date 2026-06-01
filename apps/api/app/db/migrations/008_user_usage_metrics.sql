CREATE TABLE IF NOT EXISTS user_usage_metrics (
  id text PRIMARY KEY,
  product_id text NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  module_code text,
  feature_code text NOT NULL,
  user_segment text NOT NULL DEFAULT 'all',
  window_start timestamptz NOT NULL,
  window_end timestamptz NOT NULL,
  active_users integer NOT NULL DEFAULT 0,
  event_count integer NOT NULL DEFAULT 0,
  conversion_count integer NOT NULL DEFAULT 0,
  conversion_rate numeric,
  avg_duration_seconds numeric,
  bounce_rate numeric,
  error_count integer NOT NULL DEFAULT 0,
  source_channel text,
  created_by text NOT NULL REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_user_usage_metric_window
    CHECK (window_end > window_start),
  CONSTRAINT ck_user_usage_metric_counts
    CHECK (active_users >= 0 AND event_count >= 0 AND conversion_count >= 0 AND error_count >= 0),
  CONSTRAINT ck_user_usage_metric_rates
    CHECK (
      (conversion_rate IS NULL OR conversion_rate BETWEEN 0 AND 1)
      AND (bounce_rate IS NULL OR bounce_rate BETWEEN 0 AND 1)
    ),
  CONSTRAINT ck_user_usage_metric_duration
    CHECK (avg_duration_seconds IS NULL OR avg_duration_seconds >= 0)
);

CREATE INDEX IF NOT EXISTS idx_user_usage_product_window
  ON user_usage_metrics (product_id, module_code, feature_code, window_start DESC);

CREATE INDEX IF NOT EXISTS idx_user_usage_segment_window
  ON user_usage_metrics (product_id, user_segment, window_start DESC);
