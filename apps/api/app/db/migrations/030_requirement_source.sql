ALTER TABLE requirements
  ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'business_department';

CREATE INDEX IF NOT EXISTS idx_requirements_source_created
  ON requirements (source, created_at DESC);
