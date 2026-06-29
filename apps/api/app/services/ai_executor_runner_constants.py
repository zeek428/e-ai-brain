from __future__ import annotations

SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID = "ai_executor_runner_system_default"
SYSTEM_DEFAULT_AI_EXECUTOR_TYPE = "model_gateway"

AI_EXECUTOR_TYPES = {
    SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
    "claude",
    "codex",
    "hermes",
    "openclaw",
}
AI_EXECUTOR_LOCAL_RUNNER_TYPES = AI_EXECUTOR_TYPES - {SYSTEM_DEFAULT_AI_EXECUTOR_TYPE}

AI_EXECUTOR_RUNNER_PROTOCOLS = {"mcp_http", "mcp_stdio", "runner_polling", "runner_websocket"}
AI_EXECUTOR_RUNNER_STATUSES = {"active", "disabled", "offline"}
AI_EXECUTOR_RUNNER_PACKAGE_OSES = {"docker", "linux", "macos", "manual", "windows"}
AI_EXECUTOR_RUNNER_PACKAGE_ARCHES = {"amd64", "arm64", "universal"}
AI_EXECUTOR_RUNNER_INSTALL_MODES_BY_OS = {
    "docker": {"docker"},
    "linux": {"shell", "systemd"},
    "macos": {"launchd", "shell"},
    "manual": {"manual"},
    "windows": {"powershell", "service"},
}
AI_EXECUTOR_RUNNER_DEFAULT_INSTALL_MODE_BY_OS = {
    "docker": "docker",
    "linux": "systemd",
    "macos": "launchd",
    "manual": "manual",
    "windows": "service",
}
AI_EXECUTOR_RUNNER_SORT_FIELDS = {
    "created_at",
    "endpoint_url",
    "id",
    "last_heartbeat_at",
    "name",
    "protocol",
    "status",
    "updated_at",
}

AI_EXECUTOR_TASK_STATUSES = {
    "cancelled",
    "claimed",
    "dead_letter",
    "failed",
    "queued",
    "running",
    "succeeded",
    "timed_out",
}
AI_EXECUTOR_TASK_TERMINAL_STATUSES = {
    "cancelled",
    "dead_letter",
    "failed",
    "succeeded",
    "timed_out",
}
AI_EXECUTOR_TASK_SORT_FIELDS = {
    "claimed_at",
    "created_at",
    "executor_type",
    "finished_at",
    "id",
    "runner_id",
    "scheduled_job_run_id",
    "status",
    "updated_at",
}
