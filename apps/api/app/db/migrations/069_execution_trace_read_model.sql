CREATE TABLE IF NOT EXISTS execution_trace_snapshots (
  id text PRIMARY KEY,
  root_type text NOT NULL,
  root_id text NOT NULL,
  title text NOT NULL,
  summary text NOT NULL DEFAULT '',
  status text NOT NULL DEFAULT 'unknown',
  started_at timestamptz,
  updated_at timestamptz,
  duration_ms integer,
  node_count integer NOT NULL DEFAULT 0,
  failed_node_count integer NOT NULL DEFAULT 0,
  running_node_count integer NOT NULL DEFAULT 0,
  related_ids jsonb NOT NULL DEFAULT '{}'::jsonb,
  nodes jsonb NOT NULL DEFAULT '[]'::jsonb,
  edges jsonb NOT NULL DEFAULT '[]'::jsonb,
  source_fingerprint text NOT NULL DEFAULT '',
  built_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_execution_trace_snapshots_root
  ON execution_trace_snapshots (root_type, root_id);

CREATE INDEX IF NOT EXISTS idx_execution_trace_snapshots_status_started
  ON execution_trace_snapshots (status, started_at DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_execution_trace_snapshots_root_type_started
  ON execution_trace_snapshots (root_type, started_at DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_execution_trace_snapshots_updated
  ON execution_trace_snapshots (updated_at DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_execution_trace_snapshots_related_ids
  ON execution_trace_snapshots USING gin (related_ids jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_execution_trace_snapshots_nodes
  ON execution_trace_snapshots USING gin (nodes jsonb_path_ops);
