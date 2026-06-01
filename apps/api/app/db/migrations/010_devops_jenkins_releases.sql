CREATE TABLE IF NOT EXISTS jenkins_release_records (
  id text PRIMARY KEY,
  product_id text NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  version_id text NOT NULL REFERENCES product_versions(id) ON DELETE CASCADE,
  job_name text NOT NULL,
  build_id text NOT NULL,
  build_number integer,
  environment text NOT NULL DEFAULT 'prod',
  status text NOT NULL DEFAULT 'success',
  trigger_actor text,
  commit_sha text,
  duration_seconds integer,
  started_at timestamptz,
  deployed_at timestamptz,
  failure_reason text,
  source_channel text,
  created_by text NOT NULL REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_jenkins_release_non_negative
    CHECK (
      (build_number IS NULL OR build_number >= 0)
      AND (duration_seconds IS NULL OR duration_seconds >= 0)
    ),
  CONSTRAINT ck_jenkins_release_status
    CHECK (status IN ('success', 'failed', 'running', 'canceled'))
);

CREATE INDEX IF NOT EXISTS idx_jenkins_release_product_time
  ON jenkins_release_records (product_id, deployed_at DESC NULLS LAST, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_jenkins_release_version_time
  ON jenkins_release_records (version_id, deployed_at DESC NULLS LAST, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_jenkins_release_status
  ON jenkins_release_records (product_id, status, created_at DESC);
