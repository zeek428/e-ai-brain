ALTER TABLE IF EXISTS code_inspection_reports
  ADD COLUMN IF NOT EXISTS plugin_action_id text REFERENCES plugin_actions(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS plugin_connection_id text REFERENCES plugin_connections(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_code_inspection_reports_plugin_action
  ON code_inspection_reports(plugin_action_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_code_inspection_reports_plugin_connection
  ON code_inspection_reports(plugin_connection_id, created_at DESC);
