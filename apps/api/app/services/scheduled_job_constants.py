from __future__ import annotations

SCHEDULED_JOB_RUN_STATUSES = {"cancelled", "failed", "queued", "running", "skipped", "succeeded"}
SCHEDULED_JOB_RUN_TERMINAL_STATUSES = {"cancelled", "failed", "skipped", "succeeded"}
SCHEDULED_JOB_RUN_TRIGGER_TYPES = {"manual", "manual_rerun", "scheduler"}
SCHEDULED_JOB_RUN_SORT_FIELDS = {
    "created_at",
    "finished_at",
    "records_imported",
    "started_at",
    "status",
    "trigger_type",
    "updated_at",
}
SCHEDULED_JOB_SORT_FIELDS = {
    "created_at",
    "enabled",
    "job_type",
    "last_failure_at",
    "last_run_at",
    "last_success_at",
    "name",
    "next_run_at",
    "status",
    "updated_at",
}
USER_FEEDBACK_INSIGHT_WRITE_TARGETS = {"scheduled_job_result", "user_feedback_insights"}
DEFAULT_DATA_CONNECTION_POLICY = {
    "failure_policy": "fail_fast",
    "merge_strategy": "append_json_arrays",
    "mode": "sequential",
}
DEFAULT_RESULT_ACTION_POLICY = {
    "failure_policy": "continue_on_error",
    "mode": "sequential",
}
