from __future__ import annotations

from copy import deepcopy
from typing import Any


def _max_numeric_suffix(items: dict[str, dict[str, Any]], prefix: str) -> int:
    marker = f"{prefix}_"
    max_value = 0
    for item_id in items:
        if not item_id.startswith(marker):
            continue
        suffix = item_id.removeprefix(marker)
        if suffix.isdigit():
            max_value = max(max_value, int(suffix))
    return max_value


def _max_numeric_suffix_from_values(items: list[dict[str, Any]], prefix: str) -> int:
    return _max_numeric_suffix(
        {str(item.get("id")): item for item in items if item.get("id")},
        prefix,
    )


def _sync_product_config_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    for prefix, field in [
        ("product", "products"),
        ("version", "product_versions"),
        ("version_branch", "product_version_branch_configs"),
        ("module", "product_modules"),
        ("repo", "product_git_repositories"),
        ("system", "related_systems"),
    ]:
        counters[prefix] = max(
            counters.get(prefix, 0),
            _max_numeric_suffix(payload.get(field, {}), prefix),
        )
    payload["counters"] = counters


def _sync_requirement_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    counters["requirement"] = max(
        counters.get("requirement", 0),
        _max_numeric_suffix(payload.get("requirements", {}), "requirement"),
    )
    payload["counters"] = counters


def _sync_ai_task_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    counters["task"] = max(
        counters.get("task", 0),
        _max_numeric_suffix(payload.get("ai_tasks", {}), "task"),
    )
    payload["counters"] = counters


def _sync_workflow_runtime_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    for prefix, field in [
        ("graph_run", "graph_runs"),
        ("checkpoint", "graph_checkpoints"),
        ("review", "human_reviews"),
    ]:
        counters[prefix] = max(
            counters.get(prefix, 0),
            _max_numeric_suffix(payload.get(field, {}), prefix),
        )
    payload["counters"] = counters


def _sync_knowledge_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    for prefix, field in [
        ("knowledge", "knowledge_documents"),
        ("deposit", "knowledge_deposits"),
    ]:
        counters[prefix] = max(
            counters.get(prefix, 0),
            _max_numeric_suffix(payload.get(field, {}), prefix),
        )
    payload["counters"] = counters


def _sync_audit_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    counters["audit"] = max(
        counters.get("audit", 0),
        _max_numeric_suffix_from_values(payload.get("audit_events", []), "audit"),
    )
    payload["counters"] = counters


def _sync_bug_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    counters["bug"] = max(
        counters.get("bug", 0),
        _max_numeric_suffix(payload.get("bugs", {}), "bug"),
    )
    payload["counters"] = counters


def _sync_gitlab_daily_code_metric_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    counters["gitlab_metric"] = max(
        counters.get("gitlab_metric", 0),
        _max_numeric_suffix(
            payload.get("gitlab_daily_code_metrics", {}),
            "gitlab_metric",
        ),
    )
    payload["counters"] = counters


def _sync_jenkins_release_record_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    counters["jenkins_release"] = max(
        counters.get("jenkins_release", 0),
        _max_numeric_suffix(
            payload.get("jenkins_release_records", {}),
            "jenkins_release",
        ),
    )
    payload["counters"] = counters


def _sync_online_log_metric_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    counters["online_log_metric"] = max(
        counters.get("online_log_metric", 0),
        _max_numeric_suffix(
            payload.get("online_log_metrics", {}),
            "online_log_metric",
        ),
    )
    payload["counters"] = counters


def _sync_user_usage_metric_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    counters["usage"] = max(
        counters.get("usage", 0),
        _max_numeric_suffix(payload.get("user_usage_metrics", {}), "usage"),
    )
    payload["counters"] = counters


def _sync_user_feedback_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    counters["feedback"] = max(
        counters.get("feedback", 0),
        _max_numeric_suffix(payload.get("user_feedback", {}), "feedback"),
    )
    payload["counters"] = counters


def _sync_iteration_planning_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    counters["suggestion"] = max(
        counters.get("suggestion", 0),
        _max_numeric_suffix(
            payload.get("iteration_plan_suggestions", {}),
            "suggestion",
        ),
    )
    counters["iteration_decision"] = max(
        counters.get("iteration_decision", 0),
        _max_numeric_suffix(
            payload.get("iteration_plan_decisions", {}),
            "iteration_decision",
        ),
    )
    payload["counters"] = counters


def _sync_lifecycle_context_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    counters["lifecycle_edge"] = max(
        counters.get("lifecycle_edge", 0),
        _max_numeric_suffix(
            payload.get("lifecycle_context_edges", {}),
            "lifecycle_edge",
        ),
    )
    counters["lifecycle_risk"] = max(
        counters.get("lifecycle_risk", 0),
        _max_numeric_suffix(
            payload.get("lifecycle_risk_signals", {}),
            "lifecycle_risk",
        ),
    )
    payload["counters"] = counters


def _sync_collector_run_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    counters["collector_run"] = max(
        counters.get("collector_run", 0),
        _max_numeric_suffix(payload.get("collector_runs", {}), "collector_run"),
    )
    payload["counters"] = counters


def _sync_pending_attribution_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    counters["pending_attr"] = max(
        counters.get("pending_attr", 0),
        _max_numeric_suffix(payload.get("pending_attribution_items", {}), "pending_attr"),
    )
    payload["counters"] = counters


def _sync_model_gateway_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    counters["model_gateway_config"] = max(
        counters.get("model_gateway_config", 0),
        _max_numeric_suffix(
            payload.get("model_gateway_configs", {}),
            "model_gateway_config",
        ),
    )
    counters["model_log"] = max(
        counters.get("model_log", 0),
        _max_numeric_suffix_from_values(payload.get("model_gateway_logs", []), "model_log"),
    )
    payload["counters"] = counters


def _sync_assistant_chat_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    counters["conversation"] = max(
        counters.get("conversation", 0),
        _max_numeric_suffix(payload.get("assistant_conversations", {}), "conversation"),
    )
    counters["assistant_message"] = max(
        counters.get("assistant_message", 0),
        _max_numeric_suffix(
            payload.get("assistant_messages", {}),
            "assistant_message",
        ),
    )
    payload["counters"] = counters


def _sync_gitlab_review_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    counters["snapshot"] = max(
        counters.get("snapshot", 0),
        _max_numeric_suffix(payload.get("gitlab_mr_snapshots", {}), "snapshot"),
    )
    counters["report"] = max(
        counters.get("report", 0),
        _max_numeric_suffix(payload.get("code_review_reports", {}), "report"),
    )
    payload["counters"] = counters


def _sync_mock_writeback_counters(payload: dict[str, Any]) -> None:
    counters = deepcopy(payload.get("counters", {}))
    issue_items = {
        str(issue.get("id")): issue
        for writeback in payload.get("mock_writebacks", {}).values()
        for issue in writeback.get("issues", [])
        if issue.get("id")
    }
    counters["mock_issue"] = max(
        counters.get("mock_issue", 0),
        _max_numeric_suffix(issue_items, "mock_issue"),
    )
    payload["counters"] = counters
