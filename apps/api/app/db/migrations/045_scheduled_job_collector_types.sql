ALTER TABLE IF EXISTS collector_runs
  DROP CONSTRAINT IF EXISTS ck_collector_run_type;

ALTER TABLE IF EXISTS collector_runs
  ADD CONSTRAINT ck_collector_run_type
    CHECK (
      collector_type IN (
        'code_inspection',
        'dashboard_snapshot_refresh',
        'gitlab_daily_code_metric',
        'iteration_plan_suggestion',
        'jenkins_release',
        'lifecycle_context_refresh',
        'online_log_metric',
        'pending_attribution_retry',
        'plugin_action_invoke',
        'user_feedback',
        'user_usage_metric'
      )
    );
