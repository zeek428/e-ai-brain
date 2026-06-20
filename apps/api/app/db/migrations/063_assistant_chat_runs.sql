CREATE TABLE IF NOT EXISTS assistant_chat_runs (
  id text PRIMARY KEY,
  user_id text NOT NULL,
  conversation_id text,
  user_message_id text,
  assistant_message_id text,
  client_request_id text,
  status text NOT NULL DEFAULT 'running',
  cancel_reason text,
  cancelled_by text,
  cancelled_at timestamptz,
  error_code text,
  error_message text,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_assistant_chat_runs_status CHECK (
    status IN ('running', 'succeeded', 'cancelled', 'failed')
  )
);

ALTER TABLE IF EXISTS assistant_chat_runs
  ADD COLUMN IF NOT EXISTS conversation_id text,
  ADD COLUMN IF NOT EXISTS user_message_id text,
  ADD COLUMN IF NOT EXISTS assistant_message_id text,
  ADD COLUMN IF NOT EXISTS client_request_id text,
  ADD COLUMN IF NOT EXISTS cancel_reason text,
  ADD COLUMN IF NOT EXISTS cancelled_by text,
  ADD COLUMN IF NOT EXISTS cancelled_at timestamptz,
  ADD COLUMN IF NOT EXISTS error_code text,
  ADD COLUMN IF NOT EXISTS error_message text,
  ADD COLUMN IF NOT EXISTS metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS started_at timestamptz,
  ADD COLUMN IF NOT EXISTS finished_at timestamptz;

ALTER TABLE IF EXISTS assistant_messages
  ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'completed',
  ADD COLUMN IF NOT EXISTS client_request_id text,
  ADD COLUMN IF NOT EXISTS run_id text,
  ADD COLUMN IF NOT EXISTS cancelled_at timestamptz,
  ADD COLUMN IF NOT EXISTS completed_at timestamptz,
  ADD COLUMN IF NOT EXISTS failed_at timestamptz,
  ADD COLUMN IF NOT EXISTS error_code text;

ALTER TABLE IF EXISTS assistant_messages
  DROP CONSTRAINT IF EXISTS ck_assistant_messages_status;

ALTER TABLE IF EXISTS assistant_messages
  ADD CONSTRAINT ck_assistant_messages_status CHECK (
    status IN ('pending', 'completed', 'cancelled', 'failed')
  );

CREATE INDEX IF NOT EXISTS idx_assistant_chat_runs_user_status
  ON assistant_chat_runs(user_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_assistant_chat_runs_client_request
  ON assistant_chat_runs(user_id, client_request_id);

CREATE INDEX IF NOT EXISTS idx_assistant_messages_run
  ON assistant_messages(run_id);
