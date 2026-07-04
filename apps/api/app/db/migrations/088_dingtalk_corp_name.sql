ALTER TABLE user_external_identities
  ADD COLUMN IF NOT EXISTS corp_name text;
