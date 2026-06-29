ALTER TABLE IF EXISTS code_inspection_findings
  ADD COLUMN IF NOT EXISTS suppression_owner text,
  ADD COLUMN IF NOT EXISTS suppression_expires_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_code_inspection_findings_suppression_expiry
  ON code_inspection_findings(suppression_reason, suppression_status, suppression_expires_at)
  WHERE suppression_reason = 'accepted_risk';
