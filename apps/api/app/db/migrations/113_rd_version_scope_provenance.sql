-- The current product-version scope must retain the exact accepted assessment
-- selected by an approved scope change.  Requirements alone cannot represent
-- a replacement when two accepted assessment records share a revision.

CREATE TABLE IF NOT EXISTS rd_product_version_requirement_provenance (
  product_version_id text NOT NULL REFERENCES product_versions(id) ON DELETE RESTRICT,
  requirement_id text NOT NULL REFERENCES requirements(id) ON DELETE RESTRICT,
  requirement_revision bigint NOT NULL,
  assessment_id text NOT NULL REFERENCES requirement_assessments(id) ON DELETE RESTRICT,
  final_strategy_snapshot_id text NOT NULL
    REFERENCES rd_task_executor_policy_snapshots(id) ON DELETE RESTRICT,
  applied_scope_change_request_id text
    REFERENCES rd_scope_change_requests(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (product_version_id, requirement_id),
  UNIQUE (product_version_id, assessment_id),
  CONSTRAINT ck_rd_version_scope_provenance_revision CHECK (requirement_revision > 0)
);

CREATE INDEX IF NOT EXISTS idx_rd_version_scope_provenance_version
  ON rd_product_version_requirement_provenance (product_version_id, requirement_id);
