ALTER TABLE plugin_connections
  ADD COLUMN IF NOT EXISTS request_config jsonb NOT NULL DEFAULT '{}'::jsonb;
