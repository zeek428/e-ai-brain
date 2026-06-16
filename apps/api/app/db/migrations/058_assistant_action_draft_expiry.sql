ALTER TABLE IF EXISTS assistant_action_drafts
  ADD COLUMN IF NOT EXISTS expires_at timestamptz;

ALTER TABLE IF EXISTS assistant_action_drafts
  DROP CONSTRAINT IF EXISTS ck_assistant_action_drafts_status;

ALTER TABLE IF EXISTS assistant_action_drafts
  ADD CONSTRAINT ck_assistant_action_drafts_status CHECK (
    status IN ('pending', 'confirmed', 'cancelled', 'expired', 'failed')
  );

CREATE INDEX IF NOT EXISTS idx_assistant_action_drafts_expires_at
  ON assistant_action_drafts(expires_at)
  WHERE status = 'pending';
