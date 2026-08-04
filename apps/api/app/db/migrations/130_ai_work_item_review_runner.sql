-- An AI employee occupying the frozen reviewer seat executes a dedicated,
-- read-only Runner task after the independent quality gate passes.

ALTER TABLE IF EXISTS ai_executor_tasks
  DROP CONSTRAINT IF EXISTS ck_ai_executor_tasks_task_kind;

ALTER TABLE IF EXISTS ai_executor_tasks
  ADD CONSTRAINT ck_ai_executor_tasks_task_kind CHECK (
    task_kind IN (
      'coding', 'quality_gate', 'deployment', 'integration', 'assessment',
      'git_push', 'work_item_review'
    )
  );
