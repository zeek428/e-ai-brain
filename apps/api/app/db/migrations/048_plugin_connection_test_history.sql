ALTER TABLE plugin_connections
  ADD COLUMN IF NOT EXISTS test_history jsonb NOT NULL DEFAULT '[]'::jsonb;
