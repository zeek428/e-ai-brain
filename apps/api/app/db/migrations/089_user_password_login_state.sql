ALTER TABLE users
  ADD COLUMN IF NOT EXISTS password_login_enabled boolean NOT NULL DEFAULT true;
