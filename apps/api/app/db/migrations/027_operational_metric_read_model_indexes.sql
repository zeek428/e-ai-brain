CREATE INDEX IF NOT EXISTS idx_gitlab_daily_metrics_status_updated
  ON gitlab_daily_code_metrics (status, updated_at DESC, collected_at DESC, metric_date DESC);

CREATE INDEX IF NOT EXISTS idx_jenkins_release_status_updated
  ON jenkins_release_records (status, updated_at DESC, deployed_at DESC NULLS LAST, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_online_log_status_updated
  ON online_log_metrics (status, updated_at DESC, window_start DESC, created_at DESC);
