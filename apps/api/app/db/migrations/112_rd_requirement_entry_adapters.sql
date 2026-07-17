-- Persist the legacy R&D source that created a formal requirement so retries
-- cannot create duplicate open requirements or bypass the v2 assessment flow.
ALTER TABLE requirements
  ADD COLUMN IF NOT EXISTS source_object_type text,
  ADD COLUMN IF NOT EXISTS source_object_id text,
  ADD COLUMN IF NOT EXISTS source_adapter_key text,
  ADD COLUMN IF NOT EXISTS source_evidence jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS uk_requirements_open_source_adapter
  ON requirements (source_adapter_key)
  WHERE source_adapter_key IS NOT NULL
    AND status NOT IN ('closed', 'cancelled', 'rejected', 'deferred', 'accepted', 'released');

CREATE INDEX IF NOT EXISTS idx_requirements_source_object
  ON requirements (source_object_type, source_object_id)
  WHERE source_object_type IS NOT NULL AND source_object_id IS NOT NULL;

ALTER TABLE code_inspection_reports
  ADD COLUMN IF NOT EXISTS created_requirement_ids jsonb NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE code_inspection_findings
  ADD COLUMN IF NOT EXISTS created_requirement_id text
    REFERENCES requirements(id) ON DELETE SET NULL;
