ALTER TABLE IF EXISTS ai_executor_runners
  ADD COLUMN IF NOT EXISTS token_rotated_at timestamptz,
  ADD COLUMN IF NOT EXISTS token_version integer NOT NULL DEFAULT 1;
