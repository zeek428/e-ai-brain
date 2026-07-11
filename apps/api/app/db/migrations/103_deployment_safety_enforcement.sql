ALTER TABLE deployment_requests
  ADD COLUMN IF NOT EXISTS artifact_digest text;

INSERT INTO quality_gate_policies (
  id,
  name,
  product_id,
  task_type,
  phase,
  risk_levels,
  required_checks,
  protected_paths,
  max_changed_files,
  max_changed_lines,
  required_ci_contexts,
  minimum_independent_evidence,
  manual_review_on_migration,
  status,
  version,
  created_by
)
VALUES (
  'quality_gate_policy_system_pre_deploy',
  '系统默认生产部署前门禁',
  NULL,
  NULL,
  'pre_deploy',
  '["low", "medium", "high", "critical"]'::jsonb,
  '[{"type":"artifact_integrity","required":true},{"type":"deployment_preflight","required":true}]'::jsonb,
  '[]'::jsonb,
  NULL,
  NULL,
  '[]'::jsonb,
  1,
  true,
  'active',
  1,
  NULL
)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  phase = EXCLUDED.phase,
  required_checks = EXCLUDED.required_checks,
  status = EXCLUDED.status,
  updated_at = now();
