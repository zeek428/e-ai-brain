CREATE INDEX IF NOT EXISTS idx_user_feedback_status_updated
  ON user_feedback (status, updated_at DESC, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_feedback_updated
  ON user_feedback (updated_at DESC, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_usage_updated
  ON user_usage_metrics (updated_at DESC, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_iteration_plan_updated
  ON iteration_plan_suggestions (updated_at DESC, created_at DESC);
