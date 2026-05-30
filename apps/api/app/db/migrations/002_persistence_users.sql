CREATE TABLE IF NOT EXISTS users (
  id text PRIMARY KEY,
  email text NOT NULL UNIQUE,
  display_name text NOT NULL,
  roles jsonb NOT NULL DEFAULT '[]'::jsonb,
  password_hash text NOT NULL,
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO users (id, email, display_name, roles, password_hash, status)
VALUES
  (
    'user_admin',
    'admin@example.com',
    'AI Brain Admin',
    '["admin"]'::jsonb,
    'pbkdf2_sha256$210000$admin-local-salt$KntdecyMHyH2xHE5T1MpTcNqUSw77BzqFUHEEHh6IcI',
    'active'
  ),
  (
    'user_reviewer',
    'reviewer@example.com',
    'AI Brain Reviewer',
    '["reviewer"]'::jsonb,
    'pbkdf2_sha256$210000$reviewer-local-salt$2y8_7B-H676ivrW5jN7hGbvcmzq55VeL1RhrqRlZyXA',
    'active'
  )
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS app_state_snapshots (
  key text PRIMARY KEY,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);
