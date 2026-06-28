ALTER TABLE IF EXISTS ai_executor_tasks
  DROP CONSTRAINT IF EXISTS ck_ai_executor_tasks_status;

ALTER TABLE IF EXISTS ai_executor_tasks
  ADD CONSTRAINT ck_ai_executor_tasks_status CHECK (
    status IN (
      'queued',
      'claimed',
      'running',
      'succeeded',
      'failed',
      'cancelled',
      'timed_out',
      'dead_letter'
    )
  );
