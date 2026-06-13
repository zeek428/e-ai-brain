ALTER TABLE plugin_connections
  ADD COLUMN IF NOT EXISTS last_test_summary jsonb NOT NULL DEFAULT '{}'::jsonb;
