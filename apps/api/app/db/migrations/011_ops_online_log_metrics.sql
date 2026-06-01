CREATE TABLE IF NOT EXISTS online_log_metrics (
  id text PRIMARY KEY,
  product_id text NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  module_code text,
  environment text NOT NULL DEFAULT 'prod',
  window_start timestamptz NOT NULL,
  window_end timestamptz NOT NULL,
  request_count integer NOT NULL DEFAULT 0,
  error_count integer NOT NULL DEFAULT 0,
  error_rate numeric NOT NULL DEFAULT 0,
  p95_latency_ms numeric,
  p99_latency_ms numeric,
  core_event_count integer NOT NULL DEFAULT 0,
  top_errors jsonb NOT NULL DEFAULT '[]'::jsonb,
  anomaly_summary text,
  status text NOT NULL DEFAULT 'collected',
  source_channel text,
  created_by text NOT NULL REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_online_log_metric_window
    CHECK (window_end > window_start),
  CONSTRAINT ck_online_log_metric_counts
    CHECK (
      request_count >= 0
      AND error_count >= 0
      AND error_count <= request_count
      AND core_event_count >= 0
    ),
  CONSTRAINT ck_online_log_metric_latency
    CHECK (
      (p95_latency_ms IS NULL OR p95_latency_ms >= 0)
      AND (p99_latency_ms IS NULL OR p99_latency_ms >= 0)
    ),
  CONSTRAINT ck_online_log_metric_rate
    CHECK (error_rate BETWEEN 0 AND 1),
  CONSTRAINT ck_online_log_metric_status
    CHECK (status IN ('collected', 'partial', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_online_log_product_window
  ON online_log_metrics (product_id, environment, window_start DESC);

CREATE INDEX IF NOT EXISTS idx_online_log_module_window
  ON online_log_metrics (product_id, module_code, environment, window_start DESC);

CREATE INDEX IF NOT EXISTS idx_online_log_status
  ON online_log_metrics (product_id, status, window_start DESC);
