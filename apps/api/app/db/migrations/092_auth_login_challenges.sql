CREATE TABLE IF NOT EXISTS auth_login_challenges (
  id text PRIMARY KEY,
  question text NOT NULL,
  answer_hash text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_auth_login_challenges_expires_at
  ON auth_login_challenges (expires_at);
