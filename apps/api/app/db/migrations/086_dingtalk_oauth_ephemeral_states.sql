CREATE TABLE IF NOT EXISTS dingtalk_oauth_ephemeral_states (
  id text PRIMARY KEY,
  state_type text NOT NULL,
  purpose text NOT NULL,
  redirect_path text NOT NULL DEFAULT '/welcome',
  user_id text,
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_dingtalk_oauth_ephemeral_state_type
    CHECK (state_type IN ('oauth_state', 'login_ticket'))
);

CREATE INDEX IF NOT EXISTS idx_dingtalk_oauth_ephemeral_expiry
  ON dingtalk_oauth_ephemeral_states (expires_at);

CREATE INDEX IF NOT EXISTS idx_dingtalk_oauth_ephemeral_user
  ON dingtalk_oauth_ephemeral_states (user_id)
  WHERE user_id IS NOT NULL;
