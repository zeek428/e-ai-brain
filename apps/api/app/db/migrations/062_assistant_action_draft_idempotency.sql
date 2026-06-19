CREATE UNIQUE INDEX IF NOT EXISTS idx_assistant_action_runs_successful_draft_unique
  ON assistant_action_runs(draft_id)
  WHERE status = 'succeeded';
