-- A v2 work item owns at most one non-terminal AI task.  Rework creates a
-- new task only after the previous task has reached a terminal state, so this
-- database fence is the final authority under concurrent dispatch requests.
CREATE UNIQUE INDEX IF NOT EXISTS uq_ai_tasks_active_work_item
  ON ai_tasks (work_item_id)
  WHERE work_item_id IS NOT NULL
    AND status IN ('draft', 'running', 'waiting_more_info', 'waiting_review', 'writing_back');
