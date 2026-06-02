from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def _next_id(prefix: str, current: int) -> str:
    return f"{prefix}_{current:03d}"


@dataclass
class MemoryStore:
    products: dict[str, dict[str, Any]] = field(default_factory=dict)
    product_versions: dict[str, dict[str, Any]] = field(default_factory=dict)
    product_modules: dict[str, dict[str, Any]] = field(default_factory=dict)
    product_git_repositories: dict[str, dict[str, Any]] = field(default_factory=dict)
    related_systems: dict[str, dict[str, Any]] = field(default_factory=dict)
    model_gateway_configs: dict[str, dict[str, Any]] = field(default_factory=dict)
    model_gateway_logs: list[dict[str, Any]] = field(default_factory=list)
    gitlab_mr_snapshots: dict[str, dict[str, Any]] = field(default_factory=dict)
    code_review_reports: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge_documents: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge_chunks: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge_deposits: dict[str, dict[str, Any]] = field(default_factory=dict)
    mock_writebacks: dict[str, dict[str, Any]] = field(default_factory=dict)
    bugs: dict[str, dict[str, Any]] = field(default_factory=dict)
    gitlab_daily_code_metrics: dict[str, dict[str, Any]] = field(default_factory=dict)
    jenkins_release_records: dict[str, dict[str, Any]] = field(default_factory=dict)
    online_log_metrics: dict[str, dict[str, Any]] = field(default_factory=dict)
    user_usage_metrics: dict[str, dict[str, Any]] = field(default_factory=dict)
    user_feedback: dict[str, dict[str, Any]] = field(default_factory=dict)
    iteration_plan_suggestions: dict[str, dict[str, Any]] = field(default_factory=dict)
    iteration_plan_decisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    collector_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    requirements: dict[str, dict[str, Any]] = field(default_factory=dict)
    ai_tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    graph_runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    graph_checkpoints: dict[str, dict[str, Any]] = field(default_factory=dict)
    human_reviews: dict[str, dict[str, Any]] = field(default_factory=dict)
    audit_events: list[dict[str, Any]] = field(default_factory=list)
    counters: dict[str, int] = field(default_factory=dict)

    def reset(self) -> None:
        self.products.clear()
        self.product_versions.clear()
        self.product_modules.clear()
        self.product_git_repositories.clear()
        self.related_systems.clear()
        self.model_gateway_configs.clear()
        self.model_gateway_logs.clear()
        self.gitlab_mr_snapshots.clear()
        self.code_review_reports.clear()
        self.knowledge_documents.clear()
        self.knowledge_chunks.clear()
        self.knowledge_deposits.clear()
        self.mock_writebacks.clear()
        self.bugs.clear()
        self.gitlab_daily_code_metrics.clear()
        self.jenkins_release_records.clear()
        self.online_log_metrics.clear()
        self.user_usage_metrics.clear()
        self.user_feedback.clear()
        self.iteration_plan_suggestions.clear()
        self.iteration_plan_decisions.clear()
        self.collector_runs.clear()
        self.requirements.clear()
        self.ai_tasks.clear()
        self.graph_runs.clear()
        self.graph_checkpoints.clear()
        self.human_reviews.clear()
        self.audit_events.clear()
        self.counters.clear()

    def new_id(self, prefix: str) -> str:
        next_value = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = next_value
        return _next_id(prefix, next_value)

    def snapshot(self, value: dict[str, Any]) -> dict[str, Any]:
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
