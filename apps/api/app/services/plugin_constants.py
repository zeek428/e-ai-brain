from __future__ import annotations

PLUGIN_PROTOCOLS = {"http", "mcp_http", "mcp_stdio", "runner_polling", "runner_websocket"}
PLUGIN_CATEGORIES = {
    "ai_service",
    "business_system",
    "collaboration",
    "data_warehouse",
    "devops",
    "general",
    "issue_tracking",
    "knowledge_base",
    "observability",
}
PLUGIN_STATUSES = {"active", "disabled", "draft"}
PLUGIN_AUTH_TYPES = {"none", "bearer", "api_key_header", "basic"}
PLUGIN_ACTION_TYPES = {"http_request", "mcp_tool"}
PLUGIN_CONNECTION_ENVIRONMENTS = {"default", "dev", "test", "staging", "prod", "sandbox"}
PLUGIN_INVOCATION_STATUSES = {"failed", "succeeded"}
AI_EXECUTOR_RUNNER_PROTOCOLS = {"runner_polling", "runner_websocket"}
MASKED_SECRET_PLACEHOLDER = "***"
DEPRECATED_STANDARD_PLUGIN_CODES = {"aliyun_maxcompute"}
PLUGIN_CONNECTION_SORT_FIELDS = {
    "created_at",
    "endpoint_url",
    "environment",
    "id",
    "name",
    "plugin_id",
    "status",
    "updated_at",
}
PLUGIN_ACTION_SORT_FIELDS = {
    "action_type",
    "code",
    "created_at",
    "id",
    "name",
    "plugin_id",
    "status",
    "updated_at",
}
PLUGIN_INVOCATION_LOG_SORT_FIELDS = {
    "action_id",
    "connection_id",
    "created_at",
    "id",
    "latency_ms",
    "plugin_id",
    "scheduled_job_id",
    "scheduled_job_run_id",
    "status",
    "updated_at",
}
