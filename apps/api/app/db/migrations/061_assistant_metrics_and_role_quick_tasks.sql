ALTER TABLE IF EXISTS scheduled_job_runs
  ADD COLUMN IF NOT EXISTS assistant_action_run_id text,
  ADD COLUMN IF NOT EXISTS assistant_action_draft_id text,
  ADD COLUMN IF NOT EXISTS assistant_source_message_id text,
  ADD COLUMN IF NOT EXISTS triggered_by_assistant boolean NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_scheduled_job_runs_assistant_action_run
  ON scheduled_job_runs(assistant_action_run_id)
  WHERE assistant_action_run_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_scheduled_job_runs_assistant_draft
  ON scheduled_job_runs(assistant_action_draft_id)
  WHERE assistant_action_draft_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_scheduled_job_runs_assistant_message
  ON scheduled_job_runs(assistant_source_message_id)
  WHERE assistant_source_message_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_scheduled_job_runs_triggered_by_assistant
  ON scheduled_job_runs(triggered_by_assistant, started_at DESC);

CREATE TABLE IF NOT EXISTS assistant_role_quick_tasks (
  id text PRIMARY KEY,
  enterprise_id text,
  group_key text NOT NULL,
  group_label text NOT NULL,
  group_roles jsonb NOT NULL DEFAULT '[]'::jsonb,
  group_enabled boolean NOT NULL DEFAULT true,
  group_sort_order integer NOT NULL DEFAULT 0,
  task_key text NOT NULL,
  title text NOT NULL,
  prompt text NOT NULL,
  permissions jsonb NOT NULL DEFAULT '[]'::jsonb,
  analytics_key text,
  target_draft_type text,
  enabled boolean NOT NULL DEFAULT true,
  sort_order integer NOT NULL DEFAULT 0,
  template_version text,
  rollout_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_by text,
  updated_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE IF EXISTS assistant_role_quick_tasks
  ADD COLUMN IF NOT EXISTS enterprise_id text,
  ADD COLUMN IF NOT EXISTS updated_by text;

ALTER TABLE IF EXISTS assistant_role_quick_tasks
  DROP CONSTRAINT IF EXISTS assistant_role_quick_tasks_group_key_task_key_key;

CREATE INDEX IF NOT EXISTS idx_assistant_role_quick_tasks_group
  ON assistant_role_quick_tasks(group_key, group_sort_order, sort_order);

CREATE INDEX IF NOT EXISTS idx_assistant_role_quick_tasks_enterprise
  ON assistant_role_quick_tasks(enterprise_id)
  WHERE enterprise_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_assistant_role_quick_tasks_scope_unique
  ON assistant_role_quick_tasks(
    COALESCE(enterprise_id, ''),
    group_key,
    task_key,
    COALESCE(template_version, '')
  );
