ALTER TABLE IF EXISTS code_inspection_findings
  ADD COLUMN IF NOT EXISTS suppression_status text NOT NULL DEFAULT 'none',
  ADD COLUMN IF NOT EXISTS suppression_reason text,
  ADD COLUMN IF NOT EXISTS suppression_note text,
  ADD COLUMN IF NOT EXISTS suppression_requested_by text,
  ADD COLUMN IF NOT EXISTS suppression_requested_at timestamptz,
  ADD COLUMN IF NOT EXISTS suppression_reviewed_by text,
  ADD COLUMN IF NOT EXISTS suppression_reviewed_at timestamptz;

ALTER TABLE IF EXISTS code_inspection_findings
  DROP CONSTRAINT IF EXISTS ck_code_inspection_findings_suppression_status;

ALTER TABLE IF EXISTS code_inspection_findings
  ADD CONSTRAINT ck_code_inspection_findings_suppression_status CHECK (
    suppression_status IN ('none', 'pending', 'approved', 'rejected')
  );

CREATE INDEX IF NOT EXISTS idx_code_inspection_findings_suppression_status
  ON code_inspection_findings(suppression_status, updated_at DESC);
