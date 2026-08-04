CREATE UNIQUE INDEX IF NOT EXISTS uq_trusted_delivery_acceptance_gate_case
  ON trusted_delivery_records (
    (payload_json ->> 'quality_gate_run_id'),
    (payload_json ->> 'case_id')
  )
  WHERE record_type = 'acceptance_test_run'
    AND payload_json ? 'quality_gate_run_id'
    AND payload_json ? 'case_id';
