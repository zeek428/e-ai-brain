ALTER TABLE requirements
  ADD COLUMN IF NOT EXISTS brain_app_id text DEFAULT 'rd_brain';

UPDATE requirements
SET brain_app_id = 'rd_brain'
WHERE brain_app_id IS NULL;

ALTER TABLE requirements
  ALTER COLUMN brain_app_id SET DEFAULT 'rd_brain',
  ALTER COLUMN brain_app_id SET NOT NULL;

ALTER TABLE ai_tasks
  ADD COLUMN IF NOT EXISTS brain_app_id text DEFAULT 'rd_brain';

UPDATE ai_tasks
SET brain_app_id = COALESCE(
  (
    SELECT requirements.brain_app_id
    FROM requirements
    WHERE requirements.id = ai_tasks.requirement_id
  ),
  'rd_brain'
)
WHERE brain_app_id IS NULL;

ALTER TABLE ai_tasks
  ALTER COLUMN brain_app_id SET DEFAULT 'rd_brain',
  ALTER COLUMN brain_app_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_ai_tasks_brain_app
  ON ai_tasks (brain_app_id);

UPDATE brain_apps
SET config = '{"default_task_types":["product_detail_design","technical_solution","development_planning","automated_testing","release_readiness","post_release_analysis","code_review","bug_fix"]}'::jsonb,
    updated_at = now()
WHERE id = 'rd_brain';
