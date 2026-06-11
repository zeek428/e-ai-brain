ALTER TABLE IF EXISTS code_inspection_reports
  ADD COLUMN IF NOT EXISTS committer_count integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS committer_summary jsonb NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE IF EXISTS code_inspection_findings
  ADD COLUMN IF NOT EXISTS committer_name text,
  ADD COLUMN IF NOT EXISTS committer_email text,
  ADD COLUMN IF NOT EXISTS committer_username text;

CREATE INDEX IF NOT EXISTS idx_code_inspection_reports_committer_count
  ON code_inspection_reports(committer_count, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_code_inspection_findings_committer_email
  ON code_inspection_findings(committer_email);

CREATE INDEX IF NOT EXISTS idx_code_inspection_findings_report_committer
  ON code_inspection_findings(report_id, committer_email);

UPDATE permissions
SET
  name = '查看代码巡检',
  description = '查看定期仓库质量、安全和规范巡检报告。',
  updated_at = now()
WHERE code = 'code_inspection.read';

UPDATE menu_resources
SET
  name = '代码巡检',
  updated_at = now()
WHERE code = 'code_inspection.reports';
