CREATE TABLE IF NOT EXISTS assistant_action_drafts (
  id text PRIMARY KEY,
  user_id text NOT NULL,
  source_message_id text,
  client_draft_id text,
  title text NOT NULL,
  action text NOT NULL,
  risk_level text NOT NULL DEFAULT 'medium',
  status text NOT NULL DEFAULT 'pending',
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  result_run_id text,
  cancel_reason text,
  cancelled_by text,
  cancelled_at timestamptz,
  confirmed_by text,
  confirmed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_assistant_action_drafts_status CHECK (
    status IN ('pending', 'confirmed', 'cancelled', 'failed')
  ),
  CONSTRAINT ck_assistant_action_drafts_action CHECK (
    action IN (
      'create_ai_agent',
      'create_ai_skill',
      'create_analysis_draft',
      'create_plugin_action',
      'create_plugin_connection',
      'create_rd_task',
      'create_scheduled_job'
    )
  )
);

ALTER TABLE IF EXISTS assistant_action_drafts
  ADD COLUMN IF NOT EXISTS source_message_id text,
  ADD COLUMN IF NOT EXISTS client_draft_id text,
  ADD COLUMN IF NOT EXISTS metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS result_run_id text,
  ADD COLUMN IF NOT EXISTS cancel_reason text,
  ADD COLUMN IF NOT EXISTS cancelled_by text,
  ADD COLUMN IF NOT EXISTS cancelled_at timestamptz,
  ADD COLUMN IF NOT EXISTS confirmed_by text,
  ADD COLUMN IF NOT EXISTS confirmed_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_assistant_action_drafts_user_status
  ON assistant_action_drafts(user_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_assistant_action_drafts_source_message
  ON assistant_action_drafts(source_message_id);

CREATE TABLE IF NOT EXISTS assistant_action_runs (
  id text PRIMARY KEY,
  draft_id text NOT NULL REFERENCES assistant_action_drafts(id) ON DELETE CASCADE,
  action text NOT NULL,
  status text NOT NULL,
  executed_by text NOT NULL,
  result_type text,
  result_id text,
  result jsonb NOT NULL DEFAULT '{}'::jsonb,
  error_code text,
  error_message text,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_assistant_action_runs_status CHECK (status IN ('succeeded', 'failed'))
);

ALTER TABLE IF EXISTS assistant_action_runs
  ADD COLUMN IF NOT EXISTS result jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS error_code text,
  ADD COLUMN IF NOT EXISTS error_message text,
  ADD COLUMN IF NOT EXISTS started_at timestamptz,
  ADD COLUMN IF NOT EXISTS finished_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_assistant_action_runs_draft
  ON assistant_action_runs(draft_id, created_at DESC);
