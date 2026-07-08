ALTER TABLE IF EXISTS rd_task_executor_policies
  ADD COLUMN IF NOT EXISTS code_change_review_mode text NOT NULL DEFAULT 'manual_review';

ALTER TABLE IF EXISTS rd_task_executor_policies
  DROP CONSTRAINT IF EXISTS ck_rd_task_executor_policies_code_change_review_mode;

ALTER TABLE IF EXISTS rd_task_executor_policies
  ADD CONSTRAINT ck_rd_task_executor_policies_code_change_review_mode
  CHECK (code_change_review_mode IN ('manual_review', 'auto_commit'));
