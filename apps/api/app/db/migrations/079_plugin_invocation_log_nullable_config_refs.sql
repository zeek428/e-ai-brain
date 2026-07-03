ALTER TABLE plugin_invocation_logs
  DROP CONSTRAINT IF EXISTS plugin_invocation_logs_plugin_id_fkey;

ALTER TABLE plugin_invocation_logs
  DROP CONSTRAINT IF EXISTS plugin_invocation_logs_action_id_fkey;

ALTER TABLE plugin_invocation_logs
  ALTER COLUMN plugin_id DROP NOT NULL,
  ALTER COLUMN action_id DROP NOT NULL;

ALTER TABLE plugin_invocation_logs
  ADD CONSTRAINT plugin_invocation_logs_plugin_id_fkey
  FOREIGN KEY (plugin_id) REFERENCES integration_plugins(id) ON DELETE SET NULL;

ALTER TABLE plugin_invocation_logs
  ADD CONSTRAINT plugin_invocation_logs_action_id_fkey
  FOREIGN KEY (action_id) REFERENCES plugin_actions(id) ON DELETE SET NULL;
