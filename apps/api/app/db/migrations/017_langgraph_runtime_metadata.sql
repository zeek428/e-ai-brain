ALTER TABLE graph_runs
  ADD COLUMN IF NOT EXISTS runtime text,
  ADD COLUMN IF NOT EXISTS node_path jsonb NOT NULL DEFAULT '[]'::jsonb;

UPDATE graph_runs
SET
  runtime = COALESCE(runtime, state_snapshot -> 'graph_runtime' ->> 'package'),
  node_path = COALESCE(state_snapshot -> 'graph_runtime' -> 'node_path', node_path, '[]'::jsonb)
WHERE runtime IS NULL OR node_path IS NULL OR node_path = '[]'::jsonb;
