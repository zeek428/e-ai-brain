ALTER TABLE requirements
  ALTER COLUMN version_id DROP NOT NULL;

ALTER TABLE ai_tasks
  ALTER COLUMN version_id DROP NOT NULL;

UPDATE requirements
SET status = 'submitted'
WHERE status = 'pending_approval';

UPDATE requirements
SET status = 'designing'
WHERE status = 'task_created';
