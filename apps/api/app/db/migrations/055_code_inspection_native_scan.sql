ALTER TABLE IF EXISTS code_inspection_reports
  ADD COLUMN IF NOT EXISTS scan_mode text,
  ADD COLUMN IF NOT EXISTS scanner_name text,
  ADD COLUMN IF NOT EXISTS is_full_scan boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS files_scanned integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS lines_scanned integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS rules_loaded jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS coverage_warning text;

CREATE INDEX IF NOT EXISTS idx_code_inspection_reports_scan_mode_created
  ON code_inspection_reports(scan_mode, created_at DESC);
