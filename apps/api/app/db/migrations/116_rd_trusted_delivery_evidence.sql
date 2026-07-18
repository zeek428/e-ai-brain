-- Trusted R&D delivery evidence is an append-only fact chain.  The generic
-- trusted_delivery_records table remains available for historical operational
-- data, but it must not be used as the source of truth for a release decision.

ALTER TABLE IF EXISTS product_versions
  DROP CONSTRAINT IF EXISTS ck_product_versions_status;

ALTER TABLE IF EXISTS product_versions
  ADD CONSTRAINT ck_product_versions_status CHECK (
    status IN (
      'planning', 'active', 'testing', 'ready_for_release',
      'deploying', 'released', 'archived'
    )
  );

ALTER TABLE IF EXISTS rd_collaboration_runs
  DROP CONSTRAINT IF EXISTS ck_rd_collaboration_runs_status;

ALTER TABLE IF EXISTS rd_collaboration_runs
  ADD CONSTRAINT ck_rd_collaboration_runs_status CHECK (
    status IN (
      'draft', 'planning', 'running', 'waiting_human', 'integrating',
      'verifying', 'ready_for_release', 'completed', 'failed', 'cancelled'
    )
  );

-- The trusted remote-push command is a distinct Runner task. It is not a
-- deployment task and must never be used to advance a release transition.
ALTER TABLE IF EXISTS ai_executor_tasks
  DROP CONSTRAINT IF EXISTS ck_ai_executor_tasks_task_kind;

ALTER TABLE IF EXISTS ai_executor_tasks
  ADD CONSTRAINT ck_ai_executor_tasks_task_kind CHECK (
    task_kind IN (
      'coding', 'quality_gate', 'deployment', 'integration', 'assessment', 'git_push'
    )
  );

CREATE TABLE IF NOT EXISTS rd_delivery_evidence_records (
  id text PRIMARY KEY,
  evidence_type text NOT NULL,
  product_id text NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
  collaboration_run_id text NOT NULL REFERENCES rd_collaboration_runs(id) ON DELETE RESTRICT,
  product_version_id text NOT NULL REFERENCES product_versions(id) ON DELETE RESTRICT,
  delivery_id text REFERENCES rd_delivery_evidence_records(id) ON DELETE RESTRICT,
  predecessor_evidence_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  payload_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  evidence_hash text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_rd_delivery_evidence_type CHECK (
    evidence_type IN ('delivery', 'reconciliation', 'readiness')
  ),
  CONSTRAINT ck_rd_delivery_evidence_delivery_ref CHECK (
    (evidence_type = 'delivery' AND delivery_id IS NULL)
    OR (evidence_type IN ('reconciliation', 'readiness') AND delivery_id IS NOT NULL)
  ),
  UNIQUE (evidence_type, evidence_hash)
);

CREATE INDEX IF NOT EXISTS idx_rd_delivery_evidence_run_type_created
  ON rd_delivery_evidence_records (collaboration_run_id, evidence_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_rd_delivery_evidence_delivery
  ON rd_delivery_evidence_records (delivery_id, created_at DESC)
  WHERE delivery_id IS NOT NULL;

CREATE OR REPLACE FUNCTION verify_rd_delivery_evidence_hash()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.evidence_hash <> (
    'sha256:' || encode(digest(convert_to(NEW.payload_json::text, 'UTF8'), 'sha256'), 'hex')
  ) THEN
    RAISE EXCEPTION 'rd_delivery_evidence_records evidence_hash does not match payload';
  END IF;
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION prevent_rd_delivery_evidence_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'rd_delivery_evidence_records are append-only';
END;
$$;

DROP TRIGGER IF EXISTS trg_rd_delivery_evidence_hash ON rd_delivery_evidence_records;
CREATE TRIGGER trg_rd_delivery_evidence_hash
  BEFORE INSERT ON rd_delivery_evidence_records
  FOR EACH ROW EXECUTE FUNCTION verify_rd_delivery_evidence_hash();

DROP TRIGGER IF EXISTS trg_rd_delivery_evidence_immutable ON rd_delivery_evidence_records;
CREATE TRIGGER trg_rd_delivery_evidence_immutable
  BEFORE UPDATE OR DELETE ON rd_delivery_evidence_records
  FOR EACH ROW EXECUTE FUNCTION prevent_rd_delivery_evidence_mutation();

ALTER TABLE IF EXISTS rd_collaboration_runs
  ADD COLUMN IF NOT EXISTS delivery_evidence_id text
    REFERENCES rd_delivery_evidence_records(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS delivery_evidence_hash text;

CREATE UNIQUE INDEX IF NOT EXISTS uq_rd_collaboration_runs_delivery_evidence
  ON rd_collaboration_runs (delivery_evidence_id)
  WHERE delivery_evidence_id IS NOT NULL;
