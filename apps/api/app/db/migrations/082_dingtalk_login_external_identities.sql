CREATE TABLE IF NOT EXISTS user_external_identities (
  id text PRIMARY KEY,
  user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider text NOT NULL,
  provider_subject text NOT NULL,
  union_id text,
  open_id text,
  corp_id text,
  corp_name text,
  display_name text,
  email text,
  avatar_url text,
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_external_identities_provider_subject
  ON user_external_identities (provider, provider_subject);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_external_identities_active_user_provider
  ON user_external_identities (user_id, provider)
  WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_user_external_identities_provider_corp
  ON user_external_identities (provider, corp_id);
