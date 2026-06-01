CREATE TABLE IF NOT EXISTS gitlab_daily_code_metrics (
  id text PRIMARY KEY,
  product_id text NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  repository_id text NOT NULL REFERENCES product_git_repositories(id) ON DELETE CASCADE,
  metric_date date NOT NULL,
  commit_count integer NOT NULL DEFAULT 0,
  active_author_count integer NOT NULL DEFAULT 0,
  merge_request_count integer NOT NULL DEFAULT 0,
  changed_files integer NOT NULL DEFAULT 0,
  additions integer NOT NULL DEFAULT 0,
  deletions integer NOT NULL DEFAULT 0,
  quality_score numeric,
  risk_count integer NOT NULL DEFAULT 0,
  author_metrics jsonb NOT NULL DEFAULT '[]'::jsonb,
  status text NOT NULL DEFAULT 'collected',
  source_channel text,
  collected_at timestamptz NOT NULL DEFAULT now(),
  created_by text NOT NULL REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_gitlab_daily_metric_counts
    CHECK (
      commit_count >= 0
      AND active_author_count >= 0
      AND merge_request_count >= 0
      AND changed_files >= 0
      AND additions >= 0
      AND deletions >= 0
      AND risk_count >= 0
    ),
  CONSTRAINT ck_gitlab_daily_metric_quality_score
    CHECK (quality_score IS NULL OR quality_score BETWEEN 0 AND 100),
  CONSTRAINT ck_gitlab_daily_metric_status
    CHECK (status IN ('collected', 'partial', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_gitlab_daily_metrics_product_date
  ON gitlab_daily_code_metrics (product_id, metric_date DESC);

CREATE INDEX IF NOT EXISTS idx_gitlab_daily_metrics_repository_date
  ON gitlab_daily_code_metrics (repository_id, metric_date DESC);
