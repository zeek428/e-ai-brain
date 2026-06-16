ALTER TABLE IF EXISTS code_inspection_reports
  ADD COLUMN IF NOT EXISTS artifact_ref text,
  ADD COLUMN IF NOT EXISTS checkout_path text,
  ADD COLUMN IF NOT EXISTS checkout_path_retained boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS remote_url_hash text,
  ADD COLUMN IF NOT EXISTS remote_url_summary text,
  ADD COLUMN IF NOT EXISTS scan_started_at timestamptz,
  ADD COLUMN IF NOT EXISTS scan_finished_at timestamptz,
  ADD COLUMN IF NOT EXISTS scanner_version text,
  ADD COLUMN IF NOT EXISTS rules_version text,
  ADD COLUMN IF NOT EXISTS suppressed_finding_count integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS suppression_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS quality_gate jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS scan_profile jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS previous_report_id text,
  ADD COLUMN IF NOT EXISTS previous_comparison jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_code_inspection_reports_snapshot_commit
  ON code_inspection_reports(repository_id, branch, commit_sha);

CREATE INDEX IF NOT EXISTS idx_code_inspection_reports_previous_lookup
  ON code_inspection_reports(product_id, repository_id, branch, created_at DESC);
