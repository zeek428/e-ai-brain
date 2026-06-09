CREATE TABLE IF NOT EXISTS product_version_branch_configs (
  id text PRIMARY KEY,
  product_id text NOT NULL REFERENCES products(id),
  version_id text NOT NULL REFERENCES product_versions(id) ON DELETE CASCADE,
  repository_id text NOT NULL REFERENCES product_git_repositories(id) ON DELETE CASCADE,
  base_branch text NOT NULL DEFAULT 'main',
  working_branch text NOT NULL,
  branch_status text NOT NULL DEFAULT 'not_created',
  creation_source text NOT NULL DEFAULT 'manual',
  description text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (version_id, repository_id)
);

CREATE INDEX IF NOT EXISTS idx_product_version_branch_configs_product_version
  ON product_version_branch_configs (product_id, version_id);
