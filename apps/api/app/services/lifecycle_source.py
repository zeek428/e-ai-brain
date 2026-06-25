from __future__ import annotations

from copy import deepcopy
from typing import Any


class LifecycleContextReadModel:
    def __init__(self) -> None:
        self.ai_tasks: dict[str, dict[str, Any]] = {}
        self.audit_events: list[dict[str, Any]] = []
        self.bugs: dict[str, dict[str, Any]] = {}
        self.code_review_reports: dict[str, dict[str, Any]] = {}
        self.gitlab_daily_code_metrics: dict[str, dict[str, Any]] = {}
        self.gitlab_mr_snapshots: dict[str, dict[str, Any]] = {}
        self.human_reviews: dict[str, dict[str, Any]] = {}
        self.iteration_plan_suggestions: dict[str, dict[str, Any]] = {}
        self.jenkins_release_records: dict[str, dict[str, Any]] = {}
        self.knowledge_deposits: dict[str, dict[str, Any]] = {}
        self.lifecycle_context_edges: dict[str, dict[str, Any]] = {}
        self.lifecycle_risk_signals: dict[str, dict[str, Any]] = {}
        self.mock_writebacks: dict[str, dict[str, Any]] = {}
        self.online_log_metrics: dict[str, dict[str, Any]] = {}
        self.product_git_repositories: dict[str, dict[str, Any]] = {}
        self.product_modules: dict[str, dict[str, Any]] = {}
        self.product_versions: dict[str, dict[str, Any]] = {}
        self.products: dict[str, dict[str, Any]] = {}
        self.requirements: dict[str, dict[str, Any]] = {}
        self.user_feedback: dict[str, dict[str, Any]] = {}
        self.user_usage_metrics: dict[str, dict[str, Any]] = {}

    def snapshot(self, value: Any) -> Any:
        return deepcopy(value)


def lifecycle_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    required_methods = ("get_lifecycle_context_source_rows", "save_lifecycle_context")
    if all(callable(getattr(repository, method_name, None)) for method_name in required_methods):
        return repository
    return None


def _read_memory_dict(current_store: Any, collection_name: str) -> dict[str, Any]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, dict) else {}


def lifecycle_source_store(rows: dict[str, Any]) -> LifecycleContextReadModel:
    source_store = LifecycleContextReadModel()
    source_store.audit_events = list(rows.get("audit_events", []))
    collection_keys = {
        "ai_tasks": "tasks",
        "bugs": "bugs",
        "code_review_reports": "code_review_reports",
        "gitlab_daily_code_metrics": "gitlab_daily_code_metrics",
        "gitlab_mr_snapshots": "gitlab_mr_snapshots",
        "human_reviews": "human_reviews",
        "iteration_plan_suggestions": "iteration_plan_suggestions",
        "jenkins_release_records": "jenkins_release_records",
        "knowledge_deposits": "knowledge_deposits",
        "lifecycle_context_edges": "lifecycle_context_edges",
        "lifecycle_risk_signals": "lifecycle_risk_signals",
        "mock_writebacks": "mock_writebacks",
        "online_log_metrics": "online_log_metrics",
        "product_git_repositories": "product_git_repositories",
        "product_modules": "product_modules",
        "product_versions": "product_versions",
        "products": "products",
        "requirements": "requirements",
        "user_feedback": "user_feedback",
        "user_usage_metrics": "user_usage_metrics",
    }
    for store_key, row_key in collection_keys.items():
        setattr(
            source_store,
            store_key,
            {
                str(item["id"]): dict(item)
                for item in rows.get(row_key, [])
                if item.get("id") is not None
            },
        )
    for result in rows.get("mock_writebacks", []):
        idempotency_key = result.get("idempotency_key") or result.get("task_id") or result.get("id")
        if idempotency_key is not None:
            source_store.mock_writebacks[str(idempotency_key)] = dict(result)
    return source_store


def save_lifecycle_context_records(current_store: Any) -> None:
    repository = getattr(current_store, "repository", None)
    save_records = getattr(repository, "save_lifecycle_context", None)
    if callable(save_records):
        save_records(
            {
                "lifecycle_context_edges": _read_memory_dict(
                    current_store,
                    "lifecycle_context_edges",
                ),
                "lifecycle_risk_signals": _read_memory_dict(
                    current_store,
                    "lifecycle_risk_signals",
                ),
            }
        )
