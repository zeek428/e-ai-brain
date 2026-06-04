CREATE INDEX IF NOT EXISTS idx_ai_tasks_task_type
  ON ai_tasks (task_type);

CREATE INDEX IF NOT EXISTS idx_ai_tasks_created_at_coalesced
  ON ai_tasks ((COALESCE(created_at, updated_at)) DESC);

CREATE INDEX IF NOT EXISTS idx_ai_tasks_created_by
  ON ai_tasks (created_by);

CREATE INDEX IF NOT EXISTS idx_human_reviews_status_task_created
  ON human_reviews (status, ai_task_id, created_at DESC);
