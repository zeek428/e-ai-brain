ALTER TABLE IF EXISTS ai_agents
  ADD COLUMN IF NOT EXISTS source_type text NOT NULL DEFAULT 'inline',
  ADD COLUMN IF NOT EXISTS package_uri text,
  ADD COLUMN IF NOT EXISTS package_checksum text,
  ADD COLUMN IF NOT EXISTS package_entry text,
  ADD COLUMN IF NOT EXISTS package_files jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS package_size_bytes integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS manifest jsonb NOT NULL DEFAULT '{}'::jsonb;

