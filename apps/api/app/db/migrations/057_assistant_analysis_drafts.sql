ALTER TABLE IF EXISTS assistant_action_drafts
  DROP CONSTRAINT IF EXISTS ck_assistant_action_drafts_action;

ALTER TABLE IF EXISTS assistant_action_drafts
  ADD CONSTRAINT ck_assistant_action_drafts_action CHECK (
    action IN (
      'create_analysis_draft',
      'create_plugin_action',
      'create_plugin_connection',
      'create_scheduled_job'
    )
  );
