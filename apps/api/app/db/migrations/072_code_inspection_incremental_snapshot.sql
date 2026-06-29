ALTER TABLE IF EXISTS code_inspection_reports
  ADD COLUMN IF NOT EXISTS incremental_from_commit text,
  ADD COLUMN IF NOT EXISTS incremental_file_count integer;

CREATE INDEX IF NOT EXISTS idx_code_inspection_reports_incremental_base
  ON code_inspection_reports(repository_id, branch, incremental_from_commit)
  WHERE incremental_from_commit IS NOT NULL;
