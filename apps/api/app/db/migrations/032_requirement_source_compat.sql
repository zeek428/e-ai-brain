ALTER TABLE requirements
  ADD COLUMN IF NOT EXISTS source text DEFAULT 'business_department';

UPDATE requirements
SET source = 'business_department'
WHERE source IS NULL;

ALTER TABLE requirements
  ALTER COLUMN source SET DEFAULT 'business_department',
  ALTER COLUMN source SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_requirements_source_created
  ON requirements (source, created_at DESC);
