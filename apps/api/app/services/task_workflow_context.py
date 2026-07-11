from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.core.store import default_brain_apps

TASK_WORKFLOW_COLLECTION_KEYS = {
    "ai_tasks": "tasks",
    "bugs": "bugs",
    "code_inspection_reports": "code_inspection_reports",
    "code_inspection_findings": "code_inspection_findings",
    "code_review_reports": "code_review_reports",
    "gitlab_daily_code_metrics": "gitlab_daily_code_metrics",
    "gitlab_mr_snapshots": "gitlab_mr_snapshots",
    "deployment_requests": "deployment_requests",
    "deployment_runs": "deployment_runs",
    "deployment_schemes": "deployment_schemes",
    "graph_checkpoints": "graph_checkpoints",
    "graph_runs": "graph_runs",
    "human_reviews": "human_reviews",
    "jenkins_release_records": "jenkins_release_records",
    "knowledge_chunks": "knowledge_chunks",
    "knowledge_deposits": "knowledge_deposits",
    "knowledge_documents": "knowledge_documents",
    "model_gateway_configs": "model_gateway_configs",
    "mock_writebacks": "mock_writebacks",
    "online_log_metrics": "online_log_metrics",
    "product_git_repositories": "product_git_repositories",
    "product_modules": "product_modules",
    "product_version_branch_configs": "product_version_branch_configs",
    "product_versions": "product_versions",
    "products": "products",
    "related_systems": "related_systems",
    "requirements": "requirements",
}


class TaskWorkflowSourceStore:
    """Task workflow projection that can keep repository-backed id allocation."""

    def __init__(self, repository: Any | None = None) -> None:
        self.repository = repository
        self.brain_apps: dict[str, dict[str, Any]] = default_brain_apps()
        self.products: dict[str, dict[str, Any]] = {}
        self.product_versions: dict[str, dict[str, Any]] = {}
        self.product_version_branch_configs: dict[str, dict[str, Any]] = {}
        self.product_modules: dict[str, dict[str, Any]] = {}
        self.product_git_repositories: dict[str, dict[str, Any]] = {}
        self.related_systems: dict[str, dict[str, Any]] = {}
        self.model_gateway_configs: dict[str, dict[str, Any]] = {}
        self.model_gateway_logs: list[dict[str, Any]] = []
        self.ai_executor_runners: dict[str, dict[str, Any]] = {}
        self.ai_executor_tasks: dict[str, dict[str, Any]] = {}
        self.rd_task_executor_policies: dict[str, dict[str, Any]] = {}
        self.gitlab_mr_snapshots: dict[str, dict[str, Any]] = {}
        self.code_review_reports: dict[str, dict[str, Any]] = {}
        self.knowledge_chunks: dict[str, dict[str, Any]] = {}
        self.knowledge_deposits: dict[str, dict[str, Any]] = {}
        self.knowledge_documents: dict[str, dict[str, Any]] = {}
        self.mock_writebacks: dict[str, dict[str, Any]] = {}
        self.bugs: dict[str, dict[str, Any]] = {}
        self.code_inspection_reports: dict[str, dict[str, Any]] = {}
        self.code_inspection_findings: dict[str, dict[str, Any]] = {}
        self.gitlab_daily_code_metrics: dict[str, dict[str, Any]] = {}
        self.jenkins_release_records: dict[str, dict[str, Any]] = {}
        self.deployment_schemes: dict[str, dict[str, Any]] = {}
        self.deployment_requests: dict[str, dict[str, Any]] = {}
        self.deployment_runs: dict[str, dict[str, Any]] = {}
        self.online_log_metrics: dict[str, dict[str, Any]] = {}
        self.requirements: dict[str, dict[str, Any]] = {}
        self.ai_tasks: dict[str, dict[str, Any]] = {}
        self.graph_runs: dict[str, dict[str, Any]] = {}
        self.graph_checkpoints: dict[str, dict[str, Any]] = {}
        self.human_reviews: dict[str, dict[str, Any]] = {}
        self.audit_events: list[dict[str, Any]] = []
        self.counters: dict[str, int] = {}

    def new_id(self, prefix: str) -> str:
        next_id = getattr(self.repository, "next_id", None)
        if not callable(next_id):
            next_value = self.counters.get(prefix, 0) + 1
            self.counters[prefix] = next_value
            return f"{prefix}_{next_value:03d}"
        allocated_id = next_id(prefix)
        suffix = allocated_id.removeprefix(f"{prefix}_")
        if suffix.isdigit():
            self.counters[prefix] = max(self.counters.get(prefix, 0), int(suffix))
        return allocated_id

    def snapshot(self, value: Any) -> Any:
        return deepcopy(value)

    def audit(
        self,
        *,
        event_type: str,
        actor_id: str,
        ai_task_id: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            "id": self.new_id("audit"),
            "event_type": event_type,
            "actor_id": actor_id,
            "ai_task_id": ai_task_id,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "payload": payload or {},
            "sequence": len(self.audit_events) + 1,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.audit_events.append(event)
        return event


def task_workflow_source_store(
    rows: dict[str, Any],
    repository: Any | None = None,
) -> TaskWorkflowSourceStore:
    source_store = TaskWorkflowSourceStore(repository)
    source_store.audit_events = list(rows.get("audit_events", []))
    source_store.model_gateway_logs = list(rows.get("model_gateway_logs", []))
    for store_key, row_key in TASK_WORKFLOW_COLLECTION_KEYS.items():
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


def task_workflow_read_store(current_store: Any) -> Any:
    repository = getattr(current_store, "repository", None)
    load_rows = getattr(repository, "get_task_workflow_source_rows", None)
    if not callable(load_rows):
        return current_store
    return task_workflow_source_store(load_rows(), repository=repository)


def task_workflow_write_store(current_store: Any) -> Any:
    repository = getattr(current_store, "repository", None)
    load_rows = getattr(repository, "get_task_workflow_source_rows", None)
    if not callable(load_rows):
        return current_store
    return task_workflow_source_store(load_rows(), repository=repository)
