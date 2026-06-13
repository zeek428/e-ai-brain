ALTER TABLE IF EXISTS code_inspection_reports
  ADD COLUMN IF NOT EXISTS created_task_ids jsonb NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE IF EXISTS code_inspection_findings
  ADD COLUMN IF NOT EXISTS created_task_id text REFERENCES ai_tasks(id) ON DELETE SET NULL;
