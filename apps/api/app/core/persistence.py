from __future__ import annotations

from copy import deepcopy
from time import sleep
from typing import Any, Protocol

from app.core.store import DEFAULT_BRAIN_APP_ID, MemoryStore

STATE_KEY = "memory_store"
BRAIN_APP_FIELDS = [
    "brain_apps",
]
PRODUCT_CONFIG_FIELDS = [
    "products",
    "product_versions",
    "product_modules",
    "product_git_repositories",
    "related_systems",
]
REQUIREMENT_FIELDS = [
    "requirements",
]
AI_TASK_FIELDS = [
    "ai_tasks",
]
WORKFLOW_RUNTIME_FIELDS = [
    "graph_runs",
    "graph_checkpoints",
    "human_reviews",
]
KNOWLEDGE_FIELDS = [
    "knowledge_documents",
    "knowledge_chunks",
    "knowledge_deposits",
]
AUDIT_FIELDS = [
    "audit_events",
]
BUG_FIELDS = [
    "bugs",
]
GITLAB_DAILY_CODE_METRIC_FIELDS = [
    "gitlab_daily_code_metrics",
]
JENKINS_RELEASE_RECORD_FIELDS = [
    "jenkins_release_records",
]
ONLINE_LOG_METRIC_FIELDS = [
    "online_log_metrics",
]
USER_USAGE_METRIC_FIELDS = [
    "user_usage_metrics",
]
USER_FEEDBACK_FIELDS = [
    "user_feedback",
]
ITERATION_PLANNING_FIELDS = [
    "iteration_plan_suggestions",
    "iteration_plan_decisions",
]
LIFECYCLE_CONTEXT_FIELDS = [
    "lifecycle_context_edges",
    "lifecycle_risk_signals",
]
DASHBOARD_FIELDS = [
    "dashboard_metric_snapshots",
]
COLLECTOR_RUN_FIELDS = [
    "collector_runs",
]
PENDING_ATTRIBUTION_FIELDS = [
    "pending_attribution_items",
]
MODEL_GATEWAY_FIELDS = [
    "model_gateway_configs",
    "model_gateway_logs",
]
ASSISTANT_CHAT_FIELDS = [
    "assistant_conversations",
    "assistant_messages",
]
GITLAB_REVIEW_FIELDS = [
    "gitlab_mr_snapshots",
    "code_review_reports",
]
MOCK_WRITEBACK_FIELDS = [
    "mock_writebacks",
]
ID_COUNTER_SOURCE_TABLES = [
    "products",
    "product_versions",
    "product_modules",
    "product_git_repositories",
    "related_systems",
    "model_gateway_configs",
    "model_gateway_logs",
    "assistant_conversations",
    "assistant_messages",
    "gitlab_mr_snapshots",
    "code_review_reports",
    "knowledge_documents",
    "knowledge_deposits",
    "mock_issues",
    "bugs",
    "gitlab_daily_code_metrics",
    "jenkins_release_records",
    "online_log_metrics",
    "user_usage_metrics",
    "user_feedback",
    "iteration_plan_suggestions",
    "iteration_plan_decisions",
    "lifecycle_context_edges",
    "lifecycle_risk_signals",
    "dashboard_metric_snapshots",
    "collector_runs",
    "pending_attribution_items",
    "requirements",
    "ai_tasks",
    "graph_runs",
    "graph_checkpoints",
    "human_reviews",
    "audit_events",
]
COLLECTION_FIELDS = [
    "brain_apps",
    "products",
    "product_versions",
    "product_modules",
    "product_git_repositories",
    "related_systems",
    "model_gateway_configs",
    "model_gateway_logs",
    "assistant_conversations",
    "assistant_messages",
    "gitlab_mr_snapshots",
    "code_review_reports",
    "knowledge_documents",
    "knowledge_chunks",
    "knowledge_deposits",
    "mock_writebacks",
    "bugs",
    "gitlab_daily_code_metrics",
    "jenkins_release_records",
    "online_log_metrics",
    "user_usage_metrics",
    "user_feedback",
    "iteration_plan_suggestions",
    "iteration_plan_decisions",
    "lifecycle_context_edges",
    "lifecycle_risk_signals",
    "dashboard_metric_snapshots",
    "collector_runs",
    "pending_attribution_items",
    "requirements",
    "ai_tasks",
    "graph_runs",
    "graph_checkpoints",
    "human_reviews",
    "audit_events",
    "counters",
]


class SnapshotRepository(Protocol):
    def load(self) -> dict[str, Any] | None: ...

    def save(self, payload: dict[str, Any]) -> None: ...


class ProductConfigRepository(Protocol):
    def load_product_config(self) -> dict[str, Any] | None: ...

    def save_product_config(self, payload: dict[str, Any]) -> None: ...


class BrainAppRepository(Protocol):
    def load_brain_apps(self) -> dict[str, Any] | None: ...


class RequirementRepository(Protocol):
    def load_requirements(self) -> dict[str, Any] | None: ...

    def save_requirements(self, payload: dict[str, Any]) -> None: ...


class AiTaskRepository(Protocol):
    def load_ai_tasks(self) -> dict[str, Any] | None: ...

    def save_ai_tasks(self, payload: dict[str, Any]) -> None: ...


class WorkflowRuntimeRepository(Protocol):
    def load_workflow_runtime(self) -> dict[str, Any] | None: ...

    def save_workflow_runtime(self, payload: dict[str, Any]) -> None: ...


class KnowledgeRepository(Protocol):
    def load_knowledge(self) -> dict[str, Any] | None: ...

    def save_knowledge(self, payload: dict[str, Any]) -> None: ...


class AuditRepository(Protocol):
    def load_audit_events(self) -> dict[str, Any] | None: ...

    def save_audit_events(self, payload: dict[str, Any]) -> None: ...


class BugRepository(Protocol):
    def load_bugs(self) -> dict[str, Any] | None: ...

    def save_bugs(self, payload: dict[str, Any]) -> None: ...


class GitlabDailyCodeMetricRepository(Protocol):
    def load_gitlab_daily_code_metrics(self) -> dict[str, Any] | None: ...

    def save_gitlab_daily_code_metrics(self, payload: dict[str, Any]) -> None: ...


class JenkinsReleaseRecordRepository(Protocol):
    def load_jenkins_release_records(self) -> dict[str, Any] | None: ...

    def save_jenkins_release_records(self, payload: dict[str, Any]) -> None: ...


class OnlineLogMetricRepository(Protocol):
    def load_online_log_metrics(self) -> dict[str, Any] | None: ...

    def save_online_log_metrics(self, payload: dict[str, Any]) -> None: ...


class UserUsageMetricRepository(Protocol):
    def load_user_usage_metrics(self) -> dict[str, Any] | None: ...

    def save_user_usage_metrics(self, payload: dict[str, Any]) -> None: ...


class UserFeedbackRepository(Protocol):
    def load_user_feedback(self) -> dict[str, Any] | None: ...

    def save_user_feedback(self, payload: dict[str, Any]) -> None: ...


class IterationPlanningRepository(Protocol):
    def load_iteration_planning(self) -> dict[str, Any] | None: ...

    def save_iteration_planning(self, payload: dict[str, Any]) -> None: ...


class LifecycleContextRepository(Protocol):
    def load_lifecycle_context(self) -> dict[str, Any] | None: ...

    def save_lifecycle_context(self, payload: dict[str, Any]) -> None: ...


class DashboardRepository(Protocol):
    def load_dashboard_snapshots(self) -> dict[str, Any] | None: ...

    def save_dashboard_snapshots(self, payload: dict[str, Any]) -> None: ...


class CollectorRunRepository(Protocol):
    def load_collector_runs(self) -> dict[str, Any] | None: ...

    def save_collector_runs(self, payload: dict[str, Any]) -> None: ...


class PendingAttributionRepository(Protocol):
    def load_pending_attribution(self) -> dict[str, Any] | None: ...

    def save_pending_attribution(self, payload: dict[str, Any]) -> None: ...


class ModelGatewayRepository(Protocol):
    def load_model_gateway(self) -> dict[str, Any] | None: ...

    def save_model_gateway(self, payload: dict[str, Any]) -> None: ...


class AssistantChatRepository(Protocol):
    def load_assistant_chat(self) -> dict[str, Any] | None: ...

    def save_assistant_chat(self, payload: dict[str, Any]) -> None: ...


class GitlabReviewRepository(Protocol):
    def load_gitlab_review(self) -> dict[str, Any] | None: ...

    def save_gitlab_review(self, payload: dict[str, Any]) -> None: ...


class MockWritebackRepository(Protocol):
    def load_mock_writebacks(self) -> dict[str, Any] | None: ...

    def save_mock_writebacks(self, payload: dict[str, Any]) -> None: ...


def _product_config_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in PRODUCT_CONFIG_FIELDS}


def _brain_apps_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in BRAIN_APP_FIELDS}


def _requirements_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in REQUIREMENT_FIELDS}


def _ai_tasks_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in AI_TASK_FIELDS}


def _workflow_runtime_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in WORKFLOW_RUNTIME_FIELDS}


def _knowledge_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in KNOWLEDGE_FIELDS}


def _parse_vector_text(value: Any) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [float(item) for item in value]
    text = str(value).strip()
    if not text:
        return None
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    if not text:
        return []
    return [float(item) for item in text.split(",")]


def _vector_sql_literal(value: Any) -> str | None:
    vector = _parse_vector_text(value)
    if vector is None:
        return None
    return "[" + ",".join(f"{item:.12g}" for item in vector) + "]"


def _audit_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, [])) for field in AUDIT_FIELDS}


def _bugs_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in BUG_FIELDS}


def _gitlab_daily_code_metric_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in GITLAB_DAILY_CODE_METRIC_FIELDS}


def _jenkins_release_record_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in JENKINS_RELEASE_RECORD_FIELDS}


def _online_log_metric_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in ONLINE_LOG_METRIC_FIELDS}


def _user_usage_metric_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in USER_USAGE_METRIC_FIELDS}


def _user_feedback_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in USER_FEEDBACK_FIELDS}


def _iteration_planning_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in ITERATION_PLANNING_FIELDS}


def _lifecycle_context_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in LIFECYCLE_CONTEXT_FIELDS}


def _dashboard_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in DASHBOARD_FIELDS}


def _collector_run_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in COLLECTOR_RUN_FIELDS}


def _pending_attribution_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in PENDING_ATTRIBUTION_FIELDS}


def _model_gateway_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "model_gateway_configs": deepcopy(payload.get("model_gateway_configs", {})),
        "model_gateway_logs": deepcopy(payload.get("model_gateway_logs", [])),
    }


def _assistant_chat_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "assistant_conversations": deepcopy(payload.get("assistant_conversations", {})),
        "assistant_messages": deepcopy(payload.get("assistant_messages", {})),
    }


def _gitlab_review_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in GITLAB_REVIEW_FIELDS}


def _mock_writebacks_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(payload.get(field, {})) for field in MOCK_WRITEBACK_FIELDS}


def _ai_tasks_merge_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    merge_payload = _ai_tasks_payload(payload or {})
    for task in merge_payload.get("ai_tasks", {}).values():
        for field in ("graph_run_ids", "review_ids"):
            if task.get(field) == []:
                task.pop(field)
    return merge_payload


def _merge_collection_payload(
    payload: dict[str, Any],
    overlay: dict[str, Any],
    fields: list[str],
    *,
    merge_items: bool = False,
) -> None:
    for field in fields:
        existing_items = deepcopy(payload.get(field, {}))
        overlay_items = deepcopy(overlay.get(field, {}))
        if merge_items:
            merged_items = existing_items
            for item_id, item in overlay_items.items():
                merged_items[item_id] = {
                    **deepcopy(merged_items.get(item_id, {})),
                    **item,
                }
            payload[field] = merged_items
        else:
            payload[field] = {**existing_items, **overlay_items}


def _replace_collection_payload(
    payload: dict[str, Any],
    overlay: dict[str, Any],
    fields: list[str],
) -> None:
    for field in fields:
        payload[field] = deepcopy(overlay.get(field, {}))


def _merge_audit_payload(payload: dict[str, Any], overlay: dict[str, Any]) -> None:
    payload["audit_events"] = deepcopy(overlay.get("audit_events", []))


def _repository_load_product_config(repository: SnapshotRepository) -> dict[str, Any] | None:
    load_product_config = getattr(repository, "load_product_config", None)
    if load_product_config is None:
        return None
    return load_product_config()


def _repository_load_brain_apps(repository: SnapshotRepository) -> dict[str, Any] | None:
    load_brain_apps = getattr(repository, "load_brain_apps", None)
    if load_brain_apps is None:
        return None
    return load_brain_apps()


def _repository_save_product_config(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_product_config = getattr(repository, "save_product_config", None)
    if save_product_config is not None:
        save_product_config(_product_config_payload(payload))


def _repository_load_requirements(repository: SnapshotRepository) -> dict[str, Any] | None:
    load_requirements = getattr(repository, "load_requirements", None)
    if load_requirements is None:
        return None
    return load_requirements()


def _repository_save_requirements(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_requirements = getattr(repository, "save_requirements", None)
    if save_requirements is not None:
        save_requirements(_requirements_payload(payload))


def _repository_load_ai_tasks(repository: SnapshotRepository) -> dict[str, Any] | None:
    load_ai_tasks = getattr(repository, "load_ai_tasks", None)
    if load_ai_tasks is None:
        return None
    return load_ai_tasks()


def _repository_save_ai_tasks(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_ai_tasks = getattr(repository, "save_ai_tasks", None)
    if save_ai_tasks is not None:
        save_ai_tasks(_ai_tasks_payload(payload))


def _repository_load_workflow_runtime(repository: SnapshotRepository) -> dict[str, Any] | None:
    load_workflow_runtime = getattr(repository, "load_workflow_runtime", None)
    if load_workflow_runtime is None:
        return None
    return load_workflow_runtime()


def _repository_load_knowledge(repository: SnapshotRepository) -> dict[str, Any] | None:
    load_knowledge = getattr(repository, "load_knowledge", None)
    if load_knowledge is None:
        return None
    return load_knowledge()


def _repository_load_audit_events(repository: SnapshotRepository) -> dict[str, Any] | None:
    load_audit_events = getattr(repository, "load_audit_events", None)
    if load_audit_events is None:
        return None
    return load_audit_events()


def _repository_load_bugs(repository: SnapshotRepository) -> dict[str, Any] | None:
    load_bugs = getattr(repository, "load_bugs", None)
    if load_bugs is None:
        return None
    return load_bugs()


def _repository_load_gitlab_daily_code_metrics(
    repository: SnapshotRepository,
) -> dict[str, Any] | None:
    load_gitlab_daily_code_metrics = getattr(
        repository,
        "load_gitlab_daily_code_metrics",
        None,
    )
    if load_gitlab_daily_code_metrics is None:
        return None
    return load_gitlab_daily_code_metrics()


def _repository_load_jenkins_release_records(
    repository: SnapshotRepository,
) -> dict[str, Any] | None:
    load_jenkins_release_records = getattr(
        repository,
        "load_jenkins_release_records",
        None,
    )
    if load_jenkins_release_records is None:
        return None
    return load_jenkins_release_records()


def _repository_load_online_log_metrics(
    repository: SnapshotRepository,
) -> dict[str, Any] | None:
    load_online_log_metrics = getattr(repository, "load_online_log_metrics", None)
    if load_online_log_metrics is None:
        return None
    return load_online_log_metrics()


def _repository_load_user_usage_metrics(
    repository: SnapshotRepository,
) -> dict[str, Any] | None:
    load_user_usage_metrics = getattr(repository, "load_user_usage_metrics", None)
    if load_user_usage_metrics is None:
        return None
    return load_user_usage_metrics()


def _repository_load_user_feedback(repository: SnapshotRepository) -> dict[str, Any] | None:
    load_user_feedback = getattr(repository, "load_user_feedback", None)
    if load_user_feedback is None:
        return None
    return load_user_feedback()


def _repository_load_iteration_planning(
    repository: SnapshotRepository,
) -> dict[str, Any] | None:
    load_iteration_planning = getattr(repository, "load_iteration_planning", None)
    if load_iteration_planning is None:
        return None
    return load_iteration_planning()


def _repository_load_lifecycle_context(
    repository: SnapshotRepository,
) -> dict[str, Any] | None:
    load_lifecycle_context = getattr(repository, "load_lifecycle_context", None)
    if load_lifecycle_context is None:
        return None
    return load_lifecycle_context()


def _repository_load_dashboard_snapshots(
    repository: SnapshotRepository,
) -> dict[str, Any] | None:
    load_dashboard_snapshots = getattr(repository, "load_dashboard_snapshots", None)
    if load_dashboard_snapshots is None:
        return None
    return load_dashboard_snapshots()


def _repository_load_collector_runs(repository: SnapshotRepository) -> dict[str, Any] | None:
    load_collector_runs = getattr(repository, "load_collector_runs", None)
    if load_collector_runs is None:
        return None
    return load_collector_runs()


def _repository_load_pending_attribution(
    repository: SnapshotRepository,
) -> dict[str, Any] | None:
    load_pending_attribution = getattr(repository, "load_pending_attribution", None)
    if load_pending_attribution is None:
        return None
    return load_pending_attribution()


def _repository_load_model_gateway(repository: SnapshotRepository) -> dict[str, Any] | None:
    load_model_gateway = getattr(repository, "load_model_gateway", None)
    if load_model_gateway is None:
        return None
    return load_model_gateway()


def _repository_load_assistant_chat(repository: SnapshotRepository) -> dict[str, Any] | None:
    load_assistant_chat = getattr(repository, "load_assistant_chat", None)
    if load_assistant_chat is None:
        return None
    return load_assistant_chat()


def _repository_load_gitlab_review(repository: SnapshotRepository) -> dict[str, Any] | None:
    load_gitlab_review = getattr(repository, "load_gitlab_review", None)
    if load_gitlab_review is None:
        return None
    return load_gitlab_review()


def _repository_load_mock_writebacks(repository: SnapshotRepository) -> dict[str, Any] | None:
    load_mock_writebacks = getattr(repository, "load_mock_writebacks", None)
    if load_mock_writebacks is None:
        return None
    return load_mock_writebacks()


def _repository_save_workflow_runtime(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_workflow_runtime = getattr(repository, "save_workflow_runtime", None)
    if save_workflow_runtime is not None:
        save_workflow_runtime(_workflow_runtime_payload(payload))


def _repository_save_knowledge(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_knowledge = getattr(repository, "save_knowledge", None)
    if save_knowledge is not None:
        save_knowledge(_knowledge_payload(payload))


def _repository_save_audit_events(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_audit_events = getattr(repository, "save_audit_events", None)
    if save_audit_events is not None:
        save_audit_events(_audit_payload(payload))


def _repository_save_bugs(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_bugs = getattr(repository, "save_bugs", None)
    if save_bugs is not None:
        save_bugs(_bugs_payload(payload))


def _repository_save_gitlab_daily_code_metrics(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_gitlab_daily_code_metrics = getattr(
        repository,
        "save_gitlab_daily_code_metrics",
        None,
    )
    if save_gitlab_daily_code_metrics is not None:
        clean_payload = deepcopy(payload)
        _drop_gitlab_daily_code_metrics_without_context(clean_payload)
        save_gitlab_daily_code_metrics(_gitlab_daily_code_metric_payload(clean_payload))


def _repository_save_jenkins_release_records(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_jenkins_release_records = getattr(
        repository,
        "save_jenkins_release_records",
        None,
    )
    if save_jenkins_release_records is not None:
        clean_payload = deepcopy(payload)
        _drop_jenkins_release_records_without_context(clean_payload)
        save_jenkins_release_records(_jenkins_release_record_payload(clean_payload))


def _repository_save_online_log_metrics(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_online_log_metrics = getattr(repository, "save_online_log_metrics", None)
    if save_online_log_metrics is not None:
        clean_payload = deepcopy(payload)
        _drop_online_log_metrics_without_context(clean_payload)
        save_online_log_metrics(_online_log_metric_payload(clean_payload))


def _repository_save_user_usage_metrics(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_user_usage_metrics = getattr(repository, "save_user_usage_metrics", None)
    if save_user_usage_metrics is not None:
        clean_payload = deepcopy(payload)
        _drop_user_usage_metrics_without_context(clean_payload)
        save_user_usage_metrics(_user_usage_metric_payload(clean_payload))


def _repository_save_user_feedback(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_user_feedback = getattr(repository, "save_user_feedback", None)
    if save_user_feedback is not None:
        clean_payload = deepcopy(payload)
        _drop_user_feedback_without_context(clean_payload)
        save_user_feedback(_user_feedback_payload(clean_payload))


def _repository_save_iteration_planning(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_iteration_planning = getattr(repository, "save_iteration_planning", None)
    if save_iteration_planning is not None:
        clean_payload = deepcopy(payload)
        _drop_iteration_planning_without_context(clean_payload)
        save_iteration_planning(_iteration_planning_payload(clean_payload))


def _repository_save_lifecycle_context(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_lifecycle_context = getattr(repository, "save_lifecycle_context", None)
    if save_lifecycle_context is not None:
        clean_payload = deepcopy(payload)
        _drop_lifecycle_context_without_context(clean_payload)
        save_lifecycle_context(_lifecycle_context_payload(clean_payload))


def _repository_save_dashboard_snapshots(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_dashboard_snapshots = getattr(repository, "save_dashboard_snapshots", None)
    if save_dashboard_snapshots is not None:
        clean_payload = deepcopy(payload)
        _drop_dashboard_snapshots_without_context(clean_payload)
        save_dashboard_snapshots(_dashboard_payload(clean_payload))


def _repository_save_collector_runs(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_collector_runs = getattr(repository, "save_collector_runs", None)
    if save_collector_runs is not None:
        clean_payload = deepcopy(payload)
        _drop_collector_runs_without_context(clean_payload)
        save_collector_runs(_collector_run_payload(clean_payload))


def _repository_save_pending_attribution(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_pending_attribution = getattr(repository, "save_pending_attribution", None)
    if save_pending_attribution is not None:
        clean_payload = deepcopy(payload)
        _clean_pending_attribution_references(clean_payload)
        save_pending_attribution(_pending_attribution_payload(clean_payload))


def _repository_save_model_gateway(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_model_gateway = getattr(repository, "save_model_gateway", None)
    if save_model_gateway is not None:
        save_model_gateway(_model_gateway_payload(payload))


def _repository_save_assistant_chat(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_assistant_chat = getattr(repository, "save_assistant_chat", None)
    if save_assistant_chat is not None:
        save_assistant_chat(_assistant_chat_payload(payload))


def _repository_save_gitlab_review(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_gitlab_review = getattr(repository, "save_gitlab_review", None)
    if save_gitlab_review is not None:
        clean_payload = deepcopy(payload)
        _drop_gitlab_review_without_context(clean_payload)
        save_gitlab_review(_gitlab_review_payload(clean_payload))


def _repository_save_mock_writebacks(
    repository: SnapshotRepository,
    payload: dict[str, Any],
) -> None:
    save_mock_writebacks = getattr(repository, "save_mock_writebacks", None)
    if save_mock_writebacks is not None:
        clean_payload = deepcopy(payload)
        _drop_mock_writebacks_without_tasks(clean_payload)
        save_mock_writebacks(_mock_writebacks_payload(clean_payload))


def _has_product_config_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in PRODUCT_CONFIG_FIELDS)


def _has_brain_app_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in BRAIN_APP_FIELDS)


def _has_requirement_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in REQUIREMENT_FIELDS)


def _has_ai_task_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in AI_TASK_FIELDS)


def _has_workflow_runtime_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in WORKFLOW_RUNTIME_FIELDS)


def _has_knowledge_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in KNOWLEDGE_FIELDS)


def _has_audit_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in AUDIT_FIELDS)


def _has_bug_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in BUG_FIELDS)


def _has_gitlab_daily_code_metric_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in GITLAB_DAILY_CODE_METRIC_FIELDS)


def _has_jenkins_release_record_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in JENKINS_RELEASE_RECORD_FIELDS)


def _has_online_log_metric_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in ONLINE_LOG_METRIC_FIELDS)


def _has_user_usage_metric_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in USER_USAGE_METRIC_FIELDS)


def _has_user_feedback_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in USER_FEEDBACK_FIELDS)


def _has_iteration_planning_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in ITERATION_PLANNING_FIELDS)


def _has_lifecycle_context_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in LIFECYCLE_CONTEXT_FIELDS)


def _has_dashboard_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in DASHBOARD_FIELDS)


def _has_collector_run_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in COLLECTOR_RUN_FIELDS)


def _has_pending_attribution_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in PENDING_ATTRIBUTION_FIELDS)


def _has_model_gateway_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in MODEL_GATEWAY_FIELDS)


def _has_assistant_chat_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in ASSISTANT_CHAT_FIELDS)


def _has_gitlab_review_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in GITLAB_REVIEW_FIELDS)


def _has_mock_writeback_items(payload: dict[str, Any] | None) -> bool:
    return bool(payload) and any(payload.get(field) for field in MOCK_WRITEBACK_FIELDS)


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


def _drop_requirements_without_product_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    versions = payload.get("product_versions", {})
    requirements = payload.get("requirements", {})
    payload["requirements"] = {
        requirement_id: requirement
        for requirement_id, requirement in requirements.items()
        if requirement.get("product_id") in products
        and (
            requirement.get("version_id") is None
            or (
                requirement.get("version_id") in versions
                and versions[requirement["version_id"]].get("product_id")
                == requirement.get("product_id")
            )
        )
    }


def _drop_ai_tasks_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    versions = payload.get("product_versions", {})
    requirements = payload.get("requirements", {})
    ai_tasks = payload.get("ai_tasks", {})
    payload["ai_tasks"] = {
        task_id: task
        for task_id, task in ai_tasks.items()
        if task.get("product_id") in products
        and task.get("requirement_id") in requirements
        and requirements[task["requirement_id"]].get("product_id") == task.get("product_id")
        and requirements[task["requirement_id"]].get("version_id") == task.get("version_id")
        and (
            task.get("version_id") is None
            or (
                task.get("version_id") in versions
                and versions[task["version_id"]].get("product_id") == task.get("product_id")
            )
        )
    }


def _ensure_ai_task_defaults(payload: dict[str, Any]) -> None:
    for requirement in payload.get("requirements", {}).values():
        requirement.setdefault("brain_app_id", DEFAULT_BRAIN_APP_ID)
    for task in payload.get("ai_tasks", {}).values():
        task.setdefault("brain_app_id", DEFAULT_BRAIN_APP_ID)
        task.setdefault("graph_run_ids", [])
        task.setdefault("input_json", {})
        task.setdefault("product_context", {})
        task.setdefault("review_ids", [])


def _drop_workflow_runtime_without_tasks(payload: dict[str, Any]) -> None:
    ai_tasks = payload.get("ai_tasks", {})
    graph_runs = payload.get("graph_runs", {})
    payload["graph_runs"] = {
        run_id: run
        for run_id, run in graph_runs.items()
        if run.get("ai_task_id") in ai_tasks
    }
    graph_runs = payload["graph_runs"]
    graph_checkpoints = payload.get("graph_checkpoints", {})
    payload["graph_checkpoints"] = {
        checkpoint_id: checkpoint
        for checkpoint_id, checkpoint in graph_checkpoints.items()
        if checkpoint.get("ai_task_id") in ai_tasks
        and checkpoint.get("graph_run_id") in graph_runs
    }
    human_reviews = payload.get("human_reviews", {})
    payload["human_reviews"] = {
        review_id: review
        for review_id, review in human_reviews.items()
        if review.get("ai_task_id") in ai_tasks
    }


def _sync_task_runtime_links(payload: dict[str, Any]) -> None:
    ai_tasks = payload.get("ai_tasks", {})
    for review_id, review in payload.get("human_reviews", {}).items():
        task = ai_tasks.get(review.get("ai_task_id"))
        if task is None:
            continue
        review_ids = task.setdefault("review_ids", [])
        if review_id not in review_ids:
            review_ids.append(review_id)
    for run_id, graph_run in payload.get("graph_runs", {}).items():
        task = ai_tasks.get(graph_run.get("ai_task_id"))
        if task is None:
            continue
        graph_run_ids = task.setdefault("graph_run_ids", [])
        if run_id not in graph_run_ids:
            graph_run_ids.append(run_id)
        if graph_run.get("checkpoint_id"):
            task["checkpoint_id"] = graph_run["checkpoint_id"]


def _sync_code_review_report_links(payload: dict[str, Any]) -> None:
    ai_tasks = payload.get("ai_tasks", {})
    for report_id, report in payload.get("code_review_reports", {}).items():
        task = ai_tasks.get(report.get("task_id"))
        if task is None:
            continue
        task["code_review_report_id"] = report_id


def _drop_knowledge_without_context(payload: dict[str, Any]) -> None:
    ai_tasks = payload.get("ai_tasks", {})
    knowledge_documents = payload.get("knowledge_documents", {})
    knowledge_chunks = payload.get("knowledge_chunks", {})
    knowledge_deposits = payload.get("knowledge_deposits", {})
    payload["knowledge_chunks"] = {
        chunk_id: chunk
        for chunk_id, chunk in knowledge_chunks.items()
        if chunk.get("document_id") in knowledge_documents
    }
    cleaned_deposits = {}
    for deposit_id, deposit in knowledge_deposits.items():
        if ai_tasks and deposit.get("ai_task_id") not in ai_tasks:
            continue
        if deposit.get("knowledge_document_id") not in knowledge_documents:
            deposit = deepcopy(deposit)
            deposit["knowledge_document_id"] = None
        cleaned_deposits[deposit_id] = deposit
    payload["knowledge_deposits"] = cleaned_deposits


def _drop_bugs_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    versions = payload.get("product_versions", {})
    requirements = payload.get("requirements", {})
    ai_tasks = payload.get("ai_tasks", {})
    bugs = payload.get("bugs", {})
    cleaned_bugs = {}
    for bug_id, bug in bugs.items():
        product_id = bug.get("product_id")
        version_id = bug.get("version_id")
        requirement_id = bug.get("requirement_id")
        related_task_id = bug.get("related_task_id")
        if products and product_id not in products:
            continue
        if version_id and versions and (
            version_id not in versions or versions[version_id].get("product_id") != product_id
        ):
            continue
        if requirement_id and requirements and requirement_id not in requirements:
            continue
        if related_task_id and ai_tasks and related_task_id not in ai_tasks:
            continue
        cleaned_bugs[bug_id] = deepcopy(bug)
    for bug_id, bug in cleaned_bugs.items():
        duplicate_of_bug_id = bug.get("duplicate_of_bug_id")
        if duplicate_of_bug_id and duplicate_of_bug_id not in cleaned_bugs:
            bug["duplicate_of_bug_id"] = None
        if duplicate_of_bug_id == bug_id:
            bug["duplicate_of_bug_id"] = None
    payload["bugs"] = cleaned_bugs


def _drop_user_feedback_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    requirements = payload.get("requirements", {})
    feedback_items = payload.get("user_feedback", {})
    cleaned_feedback = {}
    for feedback_id, feedback in feedback_items.items():
        product_id = feedback.get("product_id")
        requirement_id = feedback.get("related_requirement_id")
        if products and product_id not in products:
            continue
        if requirement_id and requirements and requirement_id not in requirements:
            continue
        cleaned_feedback[feedback_id] = deepcopy(feedback)
    payload["user_feedback"] = cleaned_feedback


def _drop_user_usage_metrics_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    metrics = payload.get("user_usage_metrics", {})
    cleaned_metrics = {}
    for metric_id, metric in metrics.items():
        product_id = metric.get("product_id")
        if products and product_id not in products:
            continue
        cleaned_metrics[metric_id] = deepcopy(metric)
    payload["user_usage_metrics"] = cleaned_metrics


def _drop_gitlab_daily_code_metrics_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    repositories = payload.get("product_git_repositories", {})
    metrics = payload.get("gitlab_daily_code_metrics", {})
    cleaned_metrics = {}
    for metric_id, metric in metrics.items():
        product_id = metric.get("product_id")
        repository_id = metric.get("repository_id")
        if products and product_id not in products:
            continue
        if repositories and repository_id not in repositories:
            continue
        if repositories and repositories[repository_id].get("product_id") != product_id:
            continue
        cleaned_metrics[metric_id] = deepcopy(metric)
    payload["gitlab_daily_code_metrics"] = cleaned_metrics


def _drop_jenkins_release_records_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    versions = payload.get("product_versions", {})
    releases = payload.get("jenkins_release_records", {})
    cleaned_releases = {}
    for release_id, release in releases.items():
        product_id = release.get("product_id")
        version_id = release.get("version_id")
        if products and product_id not in products:
            continue
        if versions and version_id not in versions:
            continue
        if versions and versions[version_id].get("product_id") != product_id:
            continue
        cleaned_releases[release_id] = deepcopy(release)
    payload["jenkins_release_records"] = cleaned_releases


def _drop_online_log_metrics_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    metrics = payload.get("online_log_metrics", {})
    cleaned_metrics = {}
    for metric_id, metric in metrics.items():
        product_id = metric.get("product_id")
        if products and product_id not in products:
            continue
        cleaned_metrics[metric_id] = deepcopy(metric)
    payload["online_log_metrics"] = cleaned_metrics


def _drop_iteration_planning_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    versions = payload.get("product_versions", {})
    requirements = payload.get("requirements", {})
    suggestions = payload.get("iteration_plan_suggestions", {})
    decisions = payload.get("iteration_plan_decisions", {})
    cleaned_suggestions = {}
    for suggestion_id, suggestion in suggestions.items():
        product_id = suggestion.get("product_id")
        version_id = suggestion.get("version_id")
        if products and product_id not in products:
            continue
        if version_id and versions and (
            version_id not in versions or versions[version_id].get("product_id") != product_id
        ):
            continue
        cleaned = deepcopy(suggestion)
        converted_requirement_id = cleaned.get("converted_requirement_id")
        if (
            converted_requirement_id
            and requirements
            and converted_requirement_id not in requirements
        ):
            cleaned["converted_requirement_id"] = None
        cleaned_suggestions[suggestion_id] = cleaned
    cleaned_decisions = {}
    for decision_id, decision in decisions.items():
        suggestion_id = decision.get("suggestion_id")
        if suggestion_id not in cleaned_suggestions:
            continue
        cleaned = deepcopy(decision)
        requirement_id = cleaned.get("created_requirement_id")
        if requirement_id and requirements and requirement_id not in requirements:
            cleaned["created_requirement_id"] = None
        cleaned_decisions[decision_id] = cleaned
    payload["iteration_plan_suggestions"] = cleaned_suggestions
    payload["iteration_plan_decisions"] = cleaned_decisions


def _known_lifecycle_subject(
    payload: dict[str, Any],
    subject_type: str | None,
    subject_id: str | None,
) -> bool:
    if not subject_type or not subject_id:
        return False
    subject_collections = {
        "ai_task": "ai_tasks",
        "bug": "bugs",
        "code_review_report": "code_review_reports",
        "gitlab_daily_code_metric": "gitlab_daily_code_metrics",
        "gitlab_mr_snapshot": "gitlab_mr_snapshots",
        "graph_checkpoint": "graph_checkpoints",
        "graph_run": "graph_runs",
        "human_review": "human_reviews",
        "iteration_plan_suggestion": "iteration_plan_suggestions",
        "jenkins_release": "jenkins_release_records",
        "knowledge_deposit": "knowledge_deposits",
        "knowledge_document": "knowledge_documents",
        "mock_issue": "mock_writebacks",
        "online_log_metric": "online_log_metrics",
        "product": "products",
        "requirement": "requirements",
        "user_feedback": "user_feedback",
        "user_usage_metric": "user_usage_metrics",
    }
    if subject_type == "audit_event":
        return any(event.get("id") == subject_id for event in payload.get("audit_events", []))
    if subject_type == "mock_issue":
        return any(
            issue.get("id") == subject_id
            for writeback in payload.get("mock_writebacks", {}).values()
            for issue in writeback.get("issues", [])
        )
    collection_name = subject_collections.get(subject_type)
    if collection_name is None:
        return True
    collection = payload.get(collection_name, {})
    return not collection or subject_id in collection


def _drop_lifecycle_context_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    requirements = payload.get("requirements", {})
    ai_tasks = payload.get("ai_tasks", {})
    edges = payload.get("lifecycle_context_edges", {})
    payload["lifecycle_context_edges"] = {
        edge_id: deepcopy(edge)
        for edge_id, edge in edges.items()
        if (not products or not edge.get("product_id") or edge.get("product_id") in products)
        and _known_lifecycle_subject(
            payload,
            edge.get("source_subject_type"),
            edge.get("source_subject_id"),
        )
        and _known_lifecycle_subject(
            payload,
            edge.get("target_subject_type"),
            edge.get("target_subject_id"),
        )
    }
    risks = payload.get("lifecycle_risk_signals", {})
    payload["lifecycle_risk_signals"] = {
        risk_id: deepcopy(risk)
        for risk_id, risk in risks.items()
        if (not products or not risk.get("product_id") or risk.get("product_id") in products)
        and (
            not risk.get("requirement_id")
            or not requirements
            or risk.get("requirement_id") in requirements
        )
        and (
            not risk.get("task_id")
            or not ai_tasks
            or risk.get("task_id") in ai_tasks
        )
        and _known_lifecycle_subject(
            payload,
            risk.get("source_subject_type"),
            risk.get("source_subject_id"),
        )
    }


def _drop_dashboard_snapshots_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    snapshots = payload.get("dashboard_metric_snapshots", {})
    payload["dashboard_metric_snapshots"] = {
        snapshot_id: deepcopy(snapshot)
        for snapshot_id, snapshot in snapshots.items()
        if not products or not snapshot.get("product_id") or snapshot.get("product_id") in products
    }


def _drop_collector_runs_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    runs = payload.get("collector_runs", {})
    cleaned_runs = {}
    for run_id, run in runs.items():
        product_id = run.get("product_id")
        if product_id and products and product_id not in products:
            continue
        cleaned_runs[run_id] = deepcopy(run)
    payload["collector_runs"] = cleaned_runs


def _clean_pending_attribution_references(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    modules = payload.get("product_modules", {})
    requirements = payload.get("requirements", {})
    collector_runs = payload.get("collector_runs", {})
    cleaned_items = {}
    for item_id, item in payload.get("pending_attribution_items", {}).items():
        cleaned = deepcopy(item)
        collector_run_id = cleaned.get("collector_run_id")
        if collector_run_id and collector_run_id not in collector_runs:
            cleaned["collector_run_id"] = None
        suggested_product_id = cleaned.get("suggested_product_id")
        if suggested_product_id and suggested_product_id not in products:
            cleaned["suggested_product_id"] = None
            cleaned["suggested_module_code"] = None
        resolved_product_id = cleaned.get("resolved_product_id")
        if resolved_product_id and resolved_product_id not in products:
            cleaned["resolved_product_id"] = None
            cleaned["resolved_module_code"] = None
        resolved_requirement_id = cleaned.get("resolved_requirement_id")
        if resolved_requirement_id and resolved_requirement_id not in requirements:
            cleaned["resolved_requirement_id"] = None
        if cleaned.get("resolved_requirement_id") and requirements:
            requirement = requirements[cleaned["resolved_requirement_id"]]
            if cleaned.get("resolved_product_id") and requirement.get("product_id") != cleaned.get(
                "resolved_product_id"
            ):
                cleaned["resolved_requirement_id"] = None
        resolved_module_code = cleaned.get("resolved_module_code")
        if resolved_module_code and cleaned.get("resolved_product_id"):
            module_matches = any(
                module.get("product_id") == cleaned["resolved_product_id"]
                and module.get("code") == resolved_module_code
                for module in modules.values()
            )
            if not module_matches:
                cleaned["resolved_module_code"] = None
        cleaned_items[item_id] = cleaned
    payload["pending_attribution_items"] = cleaned_items


def _drop_gitlab_review_without_context(payload: dict[str, Any]) -> None:
    products = payload.get("products", {})
    repositories = payload.get("product_git_repositories", {})
    versions = payload.get("product_versions", {})
    requirements = payload.get("requirements", {})
    ai_tasks = payload.get("ai_tasks", {})
    human_reviews = payload.get("human_reviews", {})
    snapshots = payload.get("gitlab_mr_snapshots", {})

    cleaned_snapshots = {}
    for snapshot_id, snapshot in snapshots.items():
        repository = repositories.get(snapshot.get("repository_id"))
        product_id = snapshot.get("product_id")
        version_id = snapshot.get("version_id")
        requirement = requirements.get(snapshot.get("requirement_id"))
        solution_task = ai_tasks.get(snapshot.get("technical_solution_task_id"))
        if repository is None or repository.get("product_id") != product_id:
            continue
        if product_id not in products:
            continue
        if version_id and (
            version_id not in versions or versions[version_id].get("product_id") != product_id
        ):
            continue
        if requirement is None or requirement.get("product_id") != product_id:
            continue
        if version_id and requirement.get("version_id") != version_id:
            continue
        if solution_task is None or solution_task.get("product_id") != product_id:
            continue
        if solution_task.get("requirement_id") != snapshot.get("requirement_id"):
            continue
        if version_id and solution_task.get("version_id") != version_id:
            continue
        cleaned_snapshots[snapshot_id] = deepcopy(snapshot)

    cleaned_reports = {}
    for report_id, report in payload.get("code_review_reports", {}).items():
        if report.get("gitlab_mr_snapshot_id") not in cleaned_snapshots:
            continue
        task = ai_tasks.get(report.get("task_id"))
        if task is None:
            continue
        cleaned_report = deepcopy(report)
        review_id = cleaned_report.get("review_id")
        if review_id:
            review = human_reviews.get(review_id)
            if review is None or review.get("ai_task_id") != report.get("task_id"):
                cleaned_report["review_id"] = None
        cleaned_reports[report_id] = cleaned_report

    payload["gitlab_mr_snapshots"] = cleaned_snapshots
    payload["code_review_reports"] = cleaned_reports


def _drop_mock_writebacks_without_tasks(payload: dict[str, Any]) -> None:
    ai_tasks = payload.get("ai_tasks", {})
    cleaned_writebacks = {}
    for idempotency_key, writeback in payload.get("mock_writebacks", {}).items():
        task_id = writeback.get("task_id")
        if task_id not in ai_tasks:
            continue
        cleaned_issues = []
        for issue in writeback.get("issues", []):
            if issue.get("source_task_id") != task_id:
                continue
            cleaned_issues.append(deepcopy(issue))
        if not cleaned_issues:
            continue
        cleaned_writeback = deepcopy(writeback)
        cleaned_writeback["idempotency_key"] = writeback.get("idempotency_key") or idempotency_key
        cleaned_writeback["issues"] = cleaned_issues
        cleaned_writeback["task_id"] = task_id
        cleaned_writebacks[idempotency_key] = cleaned_writeback
    payload["mock_writebacks"] = cleaned_writebacks


class PersistentMemoryStore(MemoryStore):
    def __init__(self, repository: SnapshotRepository) -> None:
        super().__init__()
        self.repository = repository

    @classmethod
    def from_repository(cls, repository: SnapshotRepository) -> PersistentMemoryStore:
        store = cls(repository)
        payload = repository.load() or {}
        brain_apps_payload = _repository_load_brain_apps(repository)
        if _has_brain_app_items(brain_apps_payload):
            _replace_collection_payload(
                payload,
                _brain_apps_payload(brain_apps_payload),
                BRAIN_APP_FIELDS,
            )
        product_config_payload = _repository_load_product_config(repository)
        has_structured_product_config = _has_product_config_items(product_config_payload)
        if has_structured_product_config:
            _merge_collection_payload(
                payload,
                _product_config_payload(product_config_payload),
                PRODUCT_CONFIG_FIELDS,
            )
            _sync_product_config_counters(payload)
        requirements_payload = _repository_load_requirements(repository)
        if _has_requirement_items(requirements_payload):
            _merge_collection_payload(
                payload,
                _requirements_payload(requirements_payload),
                REQUIREMENT_FIELDS,
            )
            _sync_requirement_counters(payload)
        ai_tasks_payload = _repository_load_ai_tasks(repository)
        has_structured_ai_tasks = _has_ai_task_items(ai_tasks_payload)
        if has_structured_ai_tasks:
            _merge_collection_payload(
                payload,
                _ai_tasks_merge_payload(ai_tasks_payload),
                AI_TASK_FIELDS,
                merge_items=True,
            )
            _sync_ai_task_counters(payload)
        workflow_runtime_payload = _repository_load_workflow_runtime(repository)
        has_structured_workflow_runtime = _has_workflow_runtime_items(workflow_runtime_payload)
        if has_structured_workflow_runtime:
            _merge_collection_payload(
                payload,
                _workflow_runtime_payload(workflow_runtime_payload),
                WORKFLOW_RUNTIME_FIELDS,
            )
            _sync_workflow_runtime_counters(payload)
        knowledge_payload = _repository_load_knowledge(repository)
        if _has_knowledge_items(knowledge_payload):
            _replace_collection_payload(
                payload,
                _knowledge_payload(knowledge_payload),
                KNOWLEDGE_FIELDS,
            )
            _sync_knowledge_counters(payload)
        audit_payload = _repository_load_audit_events(repository)
        if _has_audit_items(audit_payload):
            _merge_audit_payload(payload, _audit_payload(audit_payload))
            _sync_audit_counters(payload)
        bugs_payload = _repository_load_bugs(repository)
        if _has_bug_items(bugs_payload):
            _replace_collection_payload(
                payload,
                _bugs_payload(bugs_payload),
                BUG_FIELDS,
            )
            _sync_bug_counters(payload)
        gitlab_daily_code_metric_payload = _repository_load_gitlab_daily_code_metrics(repository)
        if _has_gitlab_daily_code_metric_items(gitlab_daily_code_metric_payload):
            _replace_collection_payload(
                payload,
                _gitlab_daily_code_metric_payload(gitlab_daily_code_metric_payload),
                GITLAB_DAILY_CODE_METRIC_FIELDS,
            )
            _sync_gitlab_daily_code_metric_counters(payload)
        jenkins_release_record_payload = _repository_load_jenkins_release_records(repository)
        if _has_jenkins_release_record_items(jenkins_release_record_payload):
            _replace_collection_payload(
                payload,
                _jenkins_release_record_payload(jenkins_release_record_payload),
                JENKINS_RELEASE_RECORD_FIELDS,
            )
            _sync_jenkins_release_record_counters(payload)
        online_log_metric_payload = _repository_load_online_log_metrics(repository)
        if _has_online_log_metric_items(online_log_metric_payload):
            _replace_collection_payload(
                payload,
                _online_log_metric_payload(online_log_metric_payload),
                ONLINE_LOG_METRIC_FIELDS,
            )
            _sync_online_log_metric_counters(payload)
        user_usage_metric_payload = _repository_load_user_usage_metrics(repository)
        if _has_user_usage_metric_items(user_usage_metric_payload):
            _replace_collection_payload(
                payload,
                _user_usage_metric_payload(user_usage_metric_payload),
                USER_USAGE_METRIC_FIELDS,
            )
            _sync_user_usage_metric_counters(payload)
        user_feedback_payload = _repository_load_user_feedback(repository)
        if _has_user_feedback_items(user_feedback_payload):
            _replace_collection_payload(
                payload,
                _user_feedback_payload(user_feedback_payload),
                USER_FEEDBACK_FIELDS,
            )
            _sync_user_feedback_counters(payload)
        iteration_planning_payload = _repository_load_iteration_planning(repository)
        if _has_iteration_planning_items(iteration_planning_payload):
            _replace_collection_payload(
                payload,
                _iteration_planning_payload(iteration_planning_payload),
                ITERATION_PLANNING_FIELDS,
            )
            _sync_iteration_planning_counters(payload)
        lifecycle_context_payload = _repository_load_lifecycle_context(repository)
        if _has_lifecycle_context_items(lifecycle_context_payload):
            _replace_collection_payload(
                payload,
                _lifecycle_context_payload(lifecycle_context_payload),
                LIFECYCLE_CONTEXT_FIELDS,
            )
            _sync_lifecycle_context_counters(payload)
        dashboard_payload = _repository_load_dashboard_snapshots(repository)
        if _has_dashboard_items(dashboard_payload):
            _replace_collection_payload(
                payload,
                _dashboard_payload(dashboard_payload),
                DASHBOARD_FIELDS,
            )
        collector_run_payload = _repository_load_collector_runs(repository)
        if _has_collector_run_items(collector_run_payload):
            _replace_collection_payload(
                payload,
                _collector_run_payload(collector_run_payload),
                COLLECTOR_RUN_FIELDS,
            )
            _sync_collector_run_counters(payload)
        pending_attribution_payload = _repository_load_pending_attribution(repository)
        if _has_pending_attribution_items(pending_attribution_payload):
            _replace_collection_payload(
                payload,
                _pending_attribution_payload(pending_attribution_payload),
                PENDING_ATTRIBUTION_FIELDS,
            )
            _sync_pending_attribution_counters(payload)
        model_gateway_payload = _repository_load_model_gateway(repository)
        if _has_model_gateway_items(model_gateway_payload):
            _replace_collection_payload(
                payload,
                _model_gateway_payload(model_gateway_payload),
                MODEL_GATEWAY_FIELDS,
            )
            _sync_model_gateway_counters(payload)
        assistant_chat_payload = _repository_load_assistant_chat(repository)
        if _has_assistant_chat_items(assistant_chat_payload):
            _replace_collection_payload(
                payload,
                _assistant_chat_payload(assistant_chat_payload),
                ASSISTANT_CHAT_FIELDS,
            )
            _sync_assistant_chat_counters(payload)
        gitlab_review_payload = _repository_load_gitlab_review(repository)
        if _has_gitlab_review_items(gitlab_review_payload):
            _replace_collection_payload(
                payload,
                _gitlab_review_payload(gitlab_review_payload),
                GITLAB_REVIEW_FIELDS,
            )
            _sync_gitlab_review_counters(payload)
        mock_writebacks_payload = _repository_load_mock_writebacks(repository)
        if _has_mock_writeback_items(mock_writebacks_payload):
            _replace_collection_payload(
                payload,
                _mock_writebacks_payload(mock_writebacks_payload),
                MOCK_WRITEBACK_FIELDS,
            )
            _sync_mock_writeback_counters(payload)
        if has_structured_product_config:
            _drop_requirements_without_product_context(payload)
        if has_structured_product_config or _has_requirement_items(requirements_payload):
            _drop_ai_tasks_without_context(payload)
        if has_structured_ai_tasks:
            _drop_workflow_runtime_without_tasks(payload)
            _drop_knowledge_without_context(payload)
        if has_structured_product_config or _has_requirement_items(requirements_payload):
            _drop_bugs_without_context(payload)
            _drop_gitlab_daily_code_metrics_without_context(payload)
            _drop_jenkins_release_records_without_context(payload)
            _drop_online_log_metrics_without_context(payload)
            _drop_user_usage_metrics_without_context(payload)
            _drop_user_feedback_without_context(payload)
            _drop_iteration_planning_without_context(payload)
            _drop_lifecycle_context_without_context(payload)
            _drop_dashboard_snapshots_without_context(payload)
            _drop_collector_runs_without_context(payload)
            _clean_pending_attribution_references(payload)
        _drop_gitlab_review_without_context(payload)
        _drop_mock_writebacks_without_tasks(payload)
        _drop_lifecycle_context_without_context(payload)
        _ensure_ai_task_defaults(payload)
        _sync_task_runtime_links(payload)
        _sync_code_review_report_links(payload)
        if payload:
            store.load_payload(payload)
        return store

    def to_payload(self) -> dict[str, Any]:
        return {field: deepcopy(getattr(self, field)) for field in COLLECTION_FIELDS}

    def load_payload(self, payload: dict[str, Any]) -> None:
        self.reset()
        for field in COLLECTION_FIELDS:
            if field in payload:
                setattr(self, field, deepcopy(payload[field]))

    def new_id(self, prefix: str) -> str:
        next_id = getattr(self.repository, "next_id", None)
        if not callable(next_id):
            return super().new_id(prefix)
        allocated_id = next_id(prefix)
        suffix = allocated_id.removeprefix(f"{prefix}_")
        if suffix.isdigit():
            self.counters[prefix] = max(self.counters.get(prefix, 0), int(suffix))
        return allocated_id

    def persist(self) -> None:
        payload = self.to_payload()
        self.repository.save(payload)
        _repository_save_product_config(self.repository, payload)
        _repository_save_requirements(self.repository, payload)
        _repository_save_ai_tasks(self.repository, payload)
        _repository_save_workflow_runtime(self.repository, payload)
        _repository_save_knowledge(self.repository, payload)
        _repository_save_audit_events(self.repository, payload)
        _repository_save_bugs(self.repository, payload)
        _repository_save_gitlab_daily_code_metrics(self.repository, payload)
        _repository_save_jenkins_release_records(self.repository, payload)
        _repository_save_online_log_metrics(self.repository, payload)
        _repository_save_user_usage_metrics(self.repository, payload)
        _repository_save_user_feedback(self.repository, payload)
        _repository_save_iteration_planning(self.repository, payload)
        _repository_save_lifecycle_context(self.repository, payload)
        _repository_save_dashboard_snapshots(self.repository, payload)
        _repository_save_collector_runs(self.repository, payload)
        _repository_save_pending_attribution(self.repository, payload)
        _repository_save_model_gateway(self.repository, payload)
        _repository_save_assistant_chat(self.repository, payload)
        _repository_save_gitlab_review(self.repository, payload)
        _repository_save_mock_writebacks(self.repository, payload)


class PostgresSnapshotRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _connect(self, *, autocommit: bool = True):
        import psycopg

        last_error: Exception | None = None
        for _ in range(20):
            try:
                return psycopg.connect(self.database_url, autocommit=autocommit)
            except psycopg.OperationalError as exc:
                last_error = exc
                sleep(0.5)
        raise last_error or RuntimeError("PostgreSQL connection failed")

    def next_id(self, prefix: str) -> str:
        with self._connect(autocommit=False) as connection:
            with connection.cursor() as cursor:
                cursor.execute("LOCK TABLE id_counters IN EXCLUSIVE MODE")
                cursor.execute(
                    "SELECT next_value FROM id_counters WHERE prefix = %s",
                    (prefix,),
                )
                row = cursor.fetchone()
                if row is None:
                    used_value = self._max_existing_id_suffix(cursor, prefix) + 1
                    cursor.execute(
                        """
                        INSERT INTO id_counters (prefix, next_value)
                        VALUES (%s, %s)
                        """,
                        (prefix, used_value + 1),
                    )
                else:
                    used_value = int(row[0])
                    cursor.execute(
                        """
                        UPDATE id_counters
                        SET next_value = %s, updated_at = now()
                        WHERE prefix = %s
                        """,
                        (used_value + 1, prefix),
                    )
        return f"{prefix}_{used_value:03d}"

    def _max_existing_id_suffix(self, cursor, prefix: str) -> int:
        marker = f"{prefix}_"
        max_value = 0
        for table_name in ID_COUNTER_SOURCE_TABLES:
            cursor.execute(
                f"SELECT id FROM {table_name} WHERE id LIKE %s",
                (f"{marker}%",),
            )
            for row in cursor.fetchall():
                item_id = str(row[0])
                suffix = item_id.removeprefix(marker)
                if suffix.isdigit():
                    max_value = max(max_value, int(suffix))
        return max_value

    def load(self) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT payload FROM app_state_snapshots WHERE key = %s",
                    (STATE_KEY,),
                )
                row = cursor.fetchone()
        return row[0] if row else None

    def save(self, payload: dict[str, Any]) -> None:
        import json

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO app_state_snapshots (key, payload, updated_at)
                    VALUES (%s, %s::jsonb, now())
                    ON CONFLICT (key) DO UPDATE SET
                      payload = EXCLUDED.payload,
                      updated_at = now()
                    """,
                    (STATE_KEY, json.dumps(payload, ensure_ascii=False)),
                )

    def load_product_config(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                products = self._load_products(cursor)
                versions = self._load_product_versions(cursor)
                modules = self._load_product_modules(cursor)
                repositories = self._load_product_git_repositories(cursor)
                related_systems = self._load_related_systems(cursor)
        return {
            "product_git_repositories": repositories,
            "product_modules": modules,
            "product_versions": versions,
            "products": products,
            "related_systems": related_systems,
        }

    def load_brain_apps(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                brain_apps = self._load_brain_apps(cursor)
        return {"brain_apps": brain_apps}

    def load_requirements(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                requirements = self._load_requirements(cursor)
        return {"requirements": requirements}

    def list_product_version_summaries(self, *, active_only: bool = False) -> list[dict[str, Any]]:
        where_clause = "WHERE v.status = 'active'" if active_only else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT v.id, v.product_id, v.code, v.name, v.description, v.status,
                           v.start_date, v.release_date, p.code, p.name
                    FROM product_versions v
                    JOIN products p ON p.id = v.product_id
                    {where_clause}
                    ORDER BY p.code, v.code
                    """
                )
                return [
                    {
                        "code": row[2],
                        "description": row[4],
                        "id": row[0],
                        "name": row[3],
                        "product_code": row[8],
                        "product_id": row[1],
                        "product_name": row[9],
                        "release_date": row[7].isoformat() if row[7] else None,
                        "start_date": row[6].isoformat() if row[6] else None,
                        "status": row[5],
                    }
                    for row in cursor.fetchall()
                ]

    def list_requirement_summaries(self, *, product_id: str | None = None) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if product_id is not None:
            where_clauses.append("r.product_id = %s")
            params.append(product_id)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT r.id, r.brain_app_id, r.title, r.product_id, r.version_id,
                           r.module_code, r.description, r.priority, r.status, r.created_by,
                           r.approval_comment, r.rejection_reason, r.task_ids,
                           r.created_at, r.updated_at, p.code, p.name, v.code, v.name
                    FROM requirements r
                    JOIN products p ON p.id = r.product_id
                    LEFT JOIN product_versions v ON v.id = r.version_id
                    {where_clause}
                    ORDER BY r.created_at DESC, r.id
                    """,
                    tuple(params),
                )
                requirements = []
                for row in cursor.fetchall():
                    requirement = {
                        "brain_app_id": row[1] or DEFAULT_BRAIN_APP_ID,
                        "content": row[6],
                        "created_at": row[13].isoformat() if row[13] else None,
                        "created_by": row[9],
                        "id": row[0],
                        "module_code": row[5],
                        "priority": row[7],
                        "product_code": row[15],
                        "product_id": row[3],
                        "product_name": row[16],
                        "status": row[8],
                        "task_ids": list(row[12] or []),
                        "title": row[2],
                        "updated_at": row[14].isoformat() if row[14] else None,
                        "version_code": row[17],
                        "version_id": row[4],
                        "version_name": row[18],
                    }
                    if row[10] is not None:
                        requirement["approval_comment"] = row[10]
                    if row[11] is not None:
                        requirement["rejection_reason"] = row[11]
                    requirements.append(requirement)
                return requirements

    def list_ai_task_summaries(
        self,
        *,
        status: str | None = None,
        task_type: str | None = None,
        product_id: str | None = None,
        requirement_id: str | None = None,
        created_from: Any | None = None,
        created_to: Any | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            where_clauses.append("t.status = %s")
            params.append(status)
        if task_type is not None:
            where_clauses.append("t.task_type = %s")
            params.append(task_type)
        if product_id is not None:
            where_clauses.append("t.product_id = %s")
            params.append(product_id)
        if requirement_id is not None:
            where_clauses.append("t.requirement_id = %s")
            params.append(requirement_id)
        if created_from is not None:
            where_clauses.append("COALESCE(t.created_at, t.updated_at) >= %s")
            params.append(created_from)
        if created_to is not None:
            where_clauses.append("COALESCE(t.created_at, t.updated_at) <= %s")
            params.append(created_to)
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT t.id, t.brain_app_id, t.requirement_id, t.task_type, t.title,
                           t.status, t.product_id, t.version_id, t.module_code,
                           t.current_step, t.created_by, t.created_at, t.updated_at,
                           COALESCE(p.name, t.product_context->'product'->>'name')
                    FROM ai_tasks t
                    LEFT JOIN products p ON p.id = t.product_id
                    {where_clause}
                    ORDER BY t.id
                    """,
                    tuple(params),
                )
                return [
                    {
                        "brain_app_id": row[1] or DEFAULT_BRAIN_APP_ID,
                        "created_at": row[11].isoformat() if row[11] else None,
                        "created_by": row[10],
                        "current_step": row[9],
                        "id": row[0],
                        "module_code": row[8],
                        "product_id": row[6],
                        "product_name": row[13],
                        "requirement_id": row[2],
                        "status": row[5],
                        "task_type": row[3],
                        "title": row[4],
                        "updated_at": row[12].isoformat() if row[12] else None,
                        "version_id": row[7],
                    }
                    for row in cursor.fetchall()
                ]

    def load_ai_tasks(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                ai_tasks = self._load_ai_tasks(cursor)
        return {"ai_tasks": ai_tasks}

    def load_workflow_runtime(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                graph_runs = self._load_graph_runs(cursor)
                graph_checkpoints = self._load_graph_checkpoints(cursor)
                human_reviews = self._load_human_reviews(cursor)
        return {
            "graph_checkpoints": graph_checkpoints,
            "graph_runs": graph_runs,
            "human_reviews": human_reviews,
        }

    def load_knowledge(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                knowledge_documents = self._load_knowledge_documents(cursor)
                knowledge_chunks = self._load_knowledge_chunks(cursor)
                knowledge_deposits = self._load_knowledge_deposits(cursor)
        return {
            "knowledge_chunks": knowledge_chunks,
            "knowledge_deposits": knowledge_deposits,
            "knowledge_documents": knowledge_documents,
        }

    def load_audit_events(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                audit_events = self._load_audit_events(cursor)
        return {"audit_events": audit_events}

    def load_bugs(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                bugs = self._load_bugs(cursor)
        return {"bugs": bugs}

    def load_gitlab_daily_code_metrics(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                metrics = self._load_gitlab_daily_code_metrics(cursor)
        return {"gitlab_daily_code_metrics": metrics}

    def load_jenkins_release_records(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                releases = self._load_jenkins_release_records(cursor)
        return {"jenkins_release_records": releases}

    def load_online_log_metrics(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                metrics = self._load_online_log_metrics(cursor)
        return {"online_log_metrics": metrics}

    def load_user_feedback(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                feedback = self._load_user_feedback(cursor)
        return {"user_feedback": feedback}

    def load_user_usage_metrics(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                metrics = self._load_user_usage_metrics(cursor)
        return {"user_usage_metrics": metrics}

    def load_iteration_planning(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                suggestions = self._load_iteration_plan_suggestions(cursor)
                decisions = self._load_iteration_plan_decisions(cursor)
        return {
            "iteration_plan_decisions": decisions,
            "iteration_plan_suggestions": suggestions,
        }

    def load_lifecycle_context(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                edges = self._load_lifecycle_context_edges(cursor)
                risks = self._load_lifecycle_risk_signals(cursor)
        return {
            "lifecycle_context_edges": edges,
            "lifecycle_risk_signals": risks,
        }

    def load_dashboard_snapshots(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                snapshots = self._load_dashboard_metric_snapshots(cursor)
        return {"dashboard_metric_snapshots": snapshots}

    def load_collector_runs(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                runs = self._load_collector_runs(cursor)
        return {"collector_runs": runs}

    def load_pending_attribution(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                items = self._load_pending_attribution_items(cursor)
        return {"pending_attribution_items": items}

    def load_model_gateway(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                configs = self._load_model_gateway_configs(cursor)
                logs = self._load_model_gateway_logs(cursor)
        return {
            "model_gateway_configs": configs,
            "model_gateway_logs": logs,
        }

    def load_assistant_chat(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                conversations = self._load_assistant_conversations(cursor)
                messages = self._load_assistant_messages(cursor)
        return {
            "assistant_conversations": conversations,
            "assistant_messages": messages,
        }

    def load_gitlab_review(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                snapshots = self._load_gitlab_mr_snapshots(cursor)
                reports = self._load_code_review_reports(cursor)
        return {
            "code_review_reports": reports,
            "gitlab_mr_snapshots": snapshots,
        }

    def load_mock_writebacks(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                writebacks = self._load_mock_writebacks(cursor)
        return {"mock_writebacks": writebacks}

    def save_product_config(self, payload: dict[str, Any]) -> None:
        products = payload.get("products", {})
        versions = payload.get("product_versions", {})
        modules = payload.get("product_modules", {})
        repositories = payload.get("product_git_repositories", {})
        related_systems = payload.get("related_systems", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "related_systems", related_systems)
                self._delete_missing(cursor, "product_git_repositories", repositories)
                self._delete_missing(cursor, "product_modules", modules)
                self._delete_missing(cursor, "product_versions", versions)
                self._delete_missing(cursor, "products", products)
                self._upsert_products(cursor, products)
                self._upsert_product_versions(cursor, versions)
                self._upsert_product_modules(cursor, modules)
                self._upsert_product_git_repositories(cursor, repositories)
                self._upsert_related_systems(cursor, related_systems)

    def save_requirements(self, payload: dict[str, Any]) -> None:
        requirements = payload.get("requirements", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "requirements", requirements)
                self._upsert_requirements(cursor, requirements)

    def save_ai_tasks(self, payload: dict[str, Any]) -> None:
        ai_tasks = payload.get("ai_tasks", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "ai_tasks", ai_tasks)
                self._upsert_ai_tasks(cursor, ai_tasks)

    def save_workflow_runtime(self, payload: dict[str, Any]) -> None:
        graph_runs = payload.get("graph_runs", {})
        graph_checkpoints = payload.get("graph_checkpoints", {})
        human_reviews = payload.get("human_reviews", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "human_reviews", human_reviews)
                self._delete_missing(cursor, "graph_checkpoints", graph_checkpoints)
                self._delete_missing(cursor, "graph_runs", graph_runs)
                self._upsert_graph_runs(cursor, graph_runs)
                self._upsert_graph_checkpoints(cursor, graph_checkpoints)
                self._upsert_human_reviews(cursor, human_reviews)

    def save_knowledge(self, payload: dict[str, Any]) -> None:
        documents = payload.get("knowledge_documents", {})
        chunks = self._clean_knowledge_chunk_references(
            documents,
            payload.get("knowledge_chunks", {}),
        )
        deposits = payload.get("knowledge_deposits", {})
        deposits = self._clean_knowledge_deposit_references(documents, deposits)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._clear_dangling_knowledge_deposit_documents(cursor, documents)
                self._clear_dangling_knowledge_chunk_documents(cursor, documents)
                self._delete_missing(cursor, "knowledge_deposits", deposits)
                self._delete_missing(cursor, "knowledge_chunks", chunks)
                self._delete_missing(cursor, "knowledge_documents", documents)
                self._upsert_knowledge_documents(cursor, documents)
                self._upsert_knowledge_chunks(cursor, chunks)
                self._upsert_knowledge_deposits(cursor, deposits)

    def save_audit_events(self, payload: dict[str, Any]) -> None:
        audit_events = payload.get("audit_events", [])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing_ids(
                    cursor,
                    "audit_events",
                    [str(event["id"]) for event in audit_events if event.get("id")],
                )
                self._upsert_audit_events(cursor, audit_events)

    def save_bugs(self, payload: dict[str, Any]) -> None:
        bugs = self._clean_bug_references(payload.get("bugs", {}))
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._clear_dangling_bug_duplicates(cursor, bugs)
                self._delete_missing(cursor, "bugs", bugs)
                self._upsert_bugs(cursor, bugs)

    def save_gitlab_daily_code_metrics(self, payload: dict[str, Any]) -> None:
        metrics = payload.get("gitlab_daily_code_metrics", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "gitlab_daily_code_metrics", metrics)
                self._upsert_gitlab_daily_code_metrics(cursor, metrics)

    def save_jenkins_release_records(self, payload: dict[str, Any]) -> None:
        releases = payload.get("jenkins_release_records", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "jenkins_release_records", releases)
                self._upsert_jenkins_release_records(cursor, releases)

    def save_online_log_metrics(self, payload: dict[str, Any]) -> None:
        metrics = payload.get("online_log_metrics", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "online_log_metrics", metrics)
                self._upsert_online_log_metrics(cursor, metrics)

    def save_user_feedback(self, payload: dict[str, Any]) -> None:
        feedback = payload.get("user_feedback", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "user_feedback", feedback)
                self._upsert_user_feedback(cursor, feedback)

    def save_user_usage_metrics(self, payload: dict[str, Any]) -> None:
        metrics = payload.get("user_usage_metrics", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "user_usage_metrics", metrics)
                self._upsert_user_usage_metrics(cursor, metrics)

    def save_iteration_planning(self, payload: dict[str, Any]) -> None:
        suggestions = payload.get("iteration_plan_suggestions", {})
        decisions = payload.get("iteration_plan_decisions", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "iteration_plan_decisions", decisions)
                self._delete_missing(cursor, "iteration_plan_suggestions", suggestions)
                self._upsert_iteration_plan_suggestions(cursor, suggestions)
                self._upsert_iteration_plan_decisions(cursor, decisions)

    def save_lifecycle_context(self, payload: dict[str, Any]) -> None:
        edges = payload.get("lifecycle_context_edges", {})
        risks = payload.get("lifecycle_risk_signals", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "lifecycle_risk_signals", risks)
                self._delete_missing(cursor, "lifecycle_context_edges", edges)
                self._upsert_lifecycle_context_edges(cursor, edges)
                self._upsert_lifecycle_risk_signals(cursor, risks)

    def save_dashboard_snapshots(self, payload: dict[str, Any]) -> None:
        snapshots = payload.get("dashboard_metric_snapshots", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "dashboard_metric_snapshots", snapshots)
                self._upsert_dashboard_metric_snapshots(cursor, snapshots)

    def save_collector_runs(self, payload: dict[str, Any]) -> None:
        runs = payload.get("collector_runs", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "collector_runs", runs)
                self._upsert_collector_runs(cursor, runs)

    def save_pending_attribution(self, payload: dict[str, Any]) -> None:
        items = payload.get("pending_attribution_items", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "pending_attribution_items", items)
                self._upsert_pending_attribution_items(cursor, items)

    def save_model_gateway(self, payload: dict[str, Any]) -> None:
        configs = payload.get("model_gateway_configs", {})
        logs = payload.get("model_gateway_logs", [])
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing_ids(
                    cursor,
                    "model_gateway_logs",
                    [str(log["id"]) for log in logs if log.get("id")],
                )
                self._delete_missing(cursor, "model_gateway_configs", configs)
                self._upsert_model_gateway_configs(cursor, configs)
                self._upsert_model_gateway_logs(cursor, logs)

    def save_assistant_chat(self, payload: dict[str, Any]) -> None:
        conversations = payload.get("assistant_conversations", {})
        messages = payload.get("assistant_messages", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "assistant_messages", messages)
                self._delete_missing(cursor, "assistant_conversations", conversations)
                self._upsert_assistant_conversations(cursor, conversations)
                self._upsert_assistant_messages(cursor, messages)

    def save_gitlab_review(self, payload: dict[str, Any]) -> None:
        snapshots = payload.get("gitlab_mr_snapshots", {})
        reports = payload.get("code_review_reports", {})
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "code_review_reports", reports)
                self._delete_missing(cursor, "gitlab_mr_snapshots", snapshots)
                self._upsert_gitlab_mr_snapshots(cursor, snapshots)
                self._upsert_code_review_reports(cursor, reports)

    def save_mock_writebacks(self, payload: dict[str, Any]) -> None:
        issues = self._mock_issue_rows(payload.get("mock_writebacks", {}))
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._delete_missing(cursor, "mock_issues", issues)
                self._upsert_mock_issues(cursor, issues)

    def _load_brain_apps(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, code, name, description, status, config, created_at, updated_at
            FROM brain_apps
            ORDER BY code
            """
        )
        return {
            row[0]: {
                "code": row[1],
                "config": dict(row[5] or {}),
                "created_at": row[6].isoformat() if row[6] else None,
                "description": row[3],
                "id": row[0],
                "name": row[2],
                "status": row[4],
                "updated_at": row[7].isoformat() if row[7] else None,
            }
            for row in cursor.fetchall()
        }

    def _load_products(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, code, name, description, owner_team, status, display_order
            FROM products
            ORDER BY display_order, code
            """
        )
        return {
            row[0]: {
                "code": row[1],
                "description": row[3],
                "display_order": row[6],
                "id": row[0],
                "name": row[2],
                "owner_team": row[4],
                "status": row[5],
            }
            for row in cursor.fetchall()
        }

    def _load_product_versions(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, code, name, description, status, start_date, release_date
            FROM product_versions
            ORDER BY product_id, code
            """
        )
        return {
            row[0]: {
                "code": row[2],
                "description": row[4],
                "id": row[0],
                "name": row[3],
                "product_id": row[1],
                "release_date": row[7].isoformat() if row[7] else None,
                "start_date": row[6].isoformat() if row[6] else None,
                "status": row[5],
            }
            for row in cursor.fetchall()
        }

    def _load_product_modules(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, code, name, description, owner_team, status, display_order
            FROM product_modules
            ORDER BY product_id, display_order, code
            """
        )
        return {
            row[0]: {
                "code": row[2],
                "description": row[4],
                "display_order": row[7],
                "id": row[0],
                "name": row[3],
                "owner_team": row[5],
                "product_id": row[1],
                "status": row[6],
            }
            for row in cursor.fetchall()
        }

    def _load_product_git_repositories(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, repo_type, name, remote_url, git_provider, project_id,
                   project_path, credential_ref, default_branch, root_path, status
            FROM product_git_repositories
            ORDER BY product_id, name
            """
        )
        return {
            row[0]: {
                "credential_ref": row[8],
                "default_branch": row[9],
                "git_provider": row[5],
                "id": row[0],
                "name": row[3],
                "product_id": row[1],
                "project_id": row[6],
                "project_path": row[7],
                "remote_url": row[4],
                "repo_type": row[2],
                "root_path": row[10],
                "status": row[11],
            }
            for row in cursor.fetchall()
        }

    def _load_related_systems(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, code, name, description, owner_team, status, display_order, product_id
            FROM related_systems
            ORDER BY display_order, code
            """
        )
        return {
            row[0]: {
                "code": row[1],
                "description": row[3],
                "display_order": row[6],
                "id": row[0],
                "name": row[2],
                "owner_team": row[4],
                "product_id": row[7],
                "status": row[5],
            }
            for row in cursor.fetchall()
        }

    def _load_requirements(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, brain_app_id, title, product_id, version_id, module_code,
                   description, priority,
                   status, created_by, approval_comment, rejection_reason, task_ids,
                   created_at, updated_at
            FROM requirements
            ORDER BY created_at DESC, id
            """
        )
        requirements = {}
        for row in cursor.fetchall():
            requirement = {
                "brain_app_id": row[1] or DEFAULT_BRAIN_APP_ID,
                "content": row[6],
                "created_at": row[13].isoformat() if row[13] else None,
                "created_by": row[9],
                "id": row[0],
                "module_code": row[5],
                "priority": row[7],
                "product_id": row[3],
                "status": row[8],
                "task_ids": list(row[12] or []),
                "title": row[2],
                "updated_at": row[14].isoformat() if row[14] else None,
                "version_id": row[4],
            }
            if row[10] is not None:
                requirement["approval_comment"] = row[10]
            if row[11] is not None:
                requirement["rejection_reason"] = row[11]
            requirements[row[0]] = requirement
        return requirements

    def _load_ai_tasks(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, brain_app_id, requirement_id, task_type, title, status,
                   product_id, version_id,
                   module_code, requirement_snapshot, product_context, input_json, output_json,
                   current_step, error_code, error_message, created_by, created_at, updated_at
            FROM ai_tasks
            ORDER BY id
            """
        )
        ai_tasks = {}
        for row in cursor.fetchall():
            task = {
                "brain_app_id": row[1] or DEFAULT_BRAIN_APP_ID,
                "created_at": row[17].isoformat() if row[17] else None,
                "created_by": row[16],
                "current_step": row[13],
                "error_code": row[14],
                "error_message": row[15],
                "graph_run_ids": [],
                "id": row[0],
                "input_json": dict(row[11] or {}),
                "module_code": row[8],
                "output_json": row[12],
                "product_context": dict(row[10] or {}),
                "product_id": row[6],
                "requirement_id": row[2],
                "requirement_snapshot": row[9],
                "review_ids": [],
                "status": row[5],
                "task_type": row[3],
                "title": row[4],
                "updated_at": row[18].isoformat() if row[18] else None,
                "version_id": row[7],
            }
            ai_tasks[row[0]] = task
        return ai_tasks

    def _load_graph_runs(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, ai_task_id, task_type, status, current_step, checkpoint_id,
                   runtime, node_path, state_snapshot, started_at, completed_at,
                   created_at, updated_at
            FROM graph_runs
            ORDER BY started_at, id
            """
        )
        return {
            row[0]: {
                "ai_task_id": row[1],
                "checkpoint_id": row[5],
                "completed_at": row[10].isoformat() if row[10] else None,
                "created_at": row[11].isoformat() if row[11] else None,
                "current_step": row[4],
                "id": row[0],
                "node_path": list(row[7] or []),
                "runtime": row[6],
                "started_at": row[9].isoformat() if row[9] else None,
                "state_snapshot": dict(row[8] or {}),
                "status": row[3],
                "task_type": row[2],
                "updated_at": row[12].isoformat() if row[12] else None,
            }
            for row in cursor.fetchall()
        }

    def _load_graph_checkpoints(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, graph_run_id, ai_task_id, current_step, state_snapshot,
                   created_at, updated_at
            FROM graph_checkpoints
            ORDER BY created_at, id
            """
        )
        return {
            row[0]: {
                "ai_task_id": row[2],
                "created_at": row[5].isoformat() if row[5] else None,
                "current_step": row[3],
                "graph_run_id": row[1],
                "id": row[0],
                "state_snapshot": dict(row[4] or {}),
                "updated_at": row[6].isoformat() if row[6] else None,
            }
            for row in cursor.fetchall()
        }

    def _load_human_reviews(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, ai_task_id, stage, status, version, content, edited_content,
                   decision_reason, decided_by, questions, decided_at, created_at, updated_at
            FROM human_reviews
            ORDER BY created_at, id
            """
        )
        human_reviews = {}
        for row in cursor.fetchall():
            review = {
                "ai_task_id": row[1],
                "content": dict(row[5] or {}),
                "created_at": row[11].isoformat() if row[11] else None,
                "decided_at": row[10].isoformat() if row[10] else None,
                "decided_by": row[8],
                "decision_reason": row[7],
                "edited_content": row[6],
                "id": row[0],
                "questions": list(row[9] or []),
                "stage": row[2],
                "status": row[3],
                "updated_at": row[12].isoformat() if row[12] else None,
                "version": row[4],
            }
            if review["edited_content"] is None:
                review.pop("edited_content")
            if review["decision_reason"] is None:
                review.pop("decision_reason")
            if review["decided_by"] is None:
                review.pop("decided_by")
            if review["decided_at"] is None:
                review.pop("decided_at")
            if not review["questions"]:
                review.pop("questions")
            human_reviews[row[0]] = review
        return human_reviews

    def _load_knowledge_documents(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, brain_app_id, product_id, version_id, title, content, source_type,
                   doc_type, permission_scope, permission_roles, index_status, index_error,
                   vector_index_error, tags, created_by, created_at, updated_at
            FROM knowledge_documents
            ORDER BY id
            """
        )
        documents = {}
        for row in cursor.fetchall():
            document = {
                "brain_app_id": row[1],
                "content": row[5],
                "created_at": row[15].isoformat() if row[15] else None,
                "created_by": row[14],
                "doc_type": row[7],
                "id": row[0],
                "index_error": row[11],
                "index_status": row[10],
                "permission_roles": list(row[9] or []),
                "permission_scope": dict(row[8] or {}),
                "product_id": row[2],
                "source_type": row[6],
                "tags": list(row[13] or []),
                "title": row[4],
                "updated_at": row[16].isoformat() if row[16] else None,
                "version_id": row[3],
                "vector_index_error": row[12],
            }
            for optional_key in (
                "brain_app_id",
                "created_at",
                "index_error",
                "product_id",
                "updated_at",
                "vector_index_error",
                "version_id",
            ):
                if document[optional_key] is None:
                    document.pop(optional_key)
            if not document["permission_scope"]:
                document.pop("permission_scope")
            documents[row[0]] = document
        return documents

    def _load_knowledge_chunks(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, document_id, chunk_index, content, embedding::text, metadata,
                   permission_scope, created_at, updated_at
            FROM knowledge_chunks
            ORDER BY document_id, chunk_index, id
            """
        )
        chunks = {}
        for row in cursor.fetchall():
            permission_scope = dict(row[6] or {})
            chunk = {
                "chunk_index": row[2],
                "content": row[3],
                "created_at": row[7].isoformat() if row[7] else None,
                "document_id": row[1],
                "embedding": _parse_vector_text(row[4]),
                "id": row[0],
                "metadata": dict(row[5] or {}),
                "permission_roles": list(permission_scope.get("roles") or []),
                "permission_scope": permission_scope,
                "updated_at": row[8].isoformat() if row[8] else None,
            }
            if chunk["embedding"] is None:
                chunk.pop("embedding")
            if not chunk["permission_roles"]:
                chunk.pop("permission_roles")
            if not chunk["permission_scope"]:
                chunk.pop("permission_scope")
            if chunk["created_at"] is None:
                chunk.pop("created_at")
            if chunk["updated_at"] is None:
                chunk.pop("updated_at")
            chunks[row[0]] = chunk
        return chunks

    def _load_knowledge_deposits(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, ai_task_id, deposit_type, title, content, content_hash, status,
                   knowledge_document_id, rejection_reason, created_at, updated_at
            FROM knowledge_deposits
            ORDER BY created_at, id
            """
        )
        deposits = {}
        for row in cursor.fetchall():
            deposit = {
                "ai_task_id": row[1],
                "content": row[4],
                "content_hash": row[5],
                "created_at": row[9].isoformat() if row[9] else None,
                "deposit_type": row[2],
                "id": row[0],
                "knowledge_document_id": row[7],
                "rejection_reason": row[8],
                "status": row[6],
                "title": row[3],
                "updated_at": row[10].isoformat() if row[10] else None,
            }
            for optional_key in (
                "content_hash",
                "created_at",
                "deposit_type",
                "knowledge_document_id",
                "rejection_reason",
                "updated_at",
            ):
                if deposit[optional_key] is None:
                    deposit.pop(optional_key)
            deposits[row[0]] = deposit
        return deposits

    def _load_audit_events(self, cursor) -> list[dict[str, Any]]:
        cursor.execute(
            """
            SELECT id::text, event_type, actor_id, ai_task_id, subject_type, subject_id,
                   payload, sequence, created_at, updated_at
            FROM audit_events
            ORDER BY sequence, created_at, id
            """
        )
        return [
            {
                "actor_id": row[2],
                "ai_task_id": row[3],
                "created_at": row[8].isoformat() if row[8] else None,
                "event_type": row[1],
                "id": row[0],
                "payload": dict(row[6] or {}),
                "sequence": row[7],
                "subject_id": row[5],
                "subject_type": row[4],
                "updated_at": row[9].isoformat() if row[9] else None,
            }
            for row in cursor.fetchall()
        ]

    def _load_bugs(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, version_id, module_code, source, title, severity,
                   description, status, assignee, related_task_id, requirement_id,
                   reproduce_steps, evidence, duplicate_of_bug_id, created_by,
                   created_at, updated_at
            FROM bugs
            ORDER BY created_at, id
            """
        )
        bugs = {}
        for row in cursor.fetchall():
            bug = {
                "assignee": row[9],
                "created_at": row[16].isoformat() if row[16] else None,
                "created_by": row[15],
                "description": row[7],
                "duplicate_of_bug_id": row[14],
                "evidence": dict(row[13] or {}),
                "id": row[0],
                "module_code": row[3],
                "product_id": row[1],
                "related_task_id": row[10],
                "reproduce_steps": list(row[12] or []),
                "requirement_id": row[11],
                "severity": row[6],
                "source": row[4],
                "status": row[8],
                "title": row[5],
                "updated_at": row[17].isoformat() if row[17] else None,
                "version_id": row[2],
            }
            for optional_key in (
                "assignee",
                "created_at",
                "duplicate_of_bug_id",
                "module_code",
                "related_task_id",
                "requirement_id",
                "updated_at",
                "version_id",
            ):
                if bug[optional_key] is None:
                    bug.pop(optional_key)
            bugs[row[0]] = bug
        return bugs

    def _load_user_feedback(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, module_code, feature_code, source_channel,
                   feedback_type, sentiment, satisfaction_score, content, tags,
                   related_requirement_id, status, triage_note, created_by,
                   created_at, updated_at
            FROM user_feedback
            ORDER BY created_at, id
            """
        )
        feedback_items = {}
        for row in cursor.fetchall():
            feedback = {
                "content": row[8],
                "created_at": row[14].isoformat() if row[14] else None,
                "created_by": row[13],
                "feature_code": row[3],
                "feedback_type": row[5],
                "id": row[0],
                "module_code": row[2],
                "product_id": row[1],
                "related_requirement_id": row[10],
                "satisfaction_score": row[7],
                "sentiment": row[6],
                "source_channel": row[4],
                "status": row[11],
                "tags": list(row[9] or []),
                "triage_note": row[12],
                "updated_at": row[15].isoformat() if row[15] else None,
            }
            for optional_key in (
                "created_at",
                "feature_code",
                "module_code",
                "related_requirement_id",
                "satisfaction_score",
                "sentiment",
                "triage_note",
                "updated_at",
            ):
                if feedback[optional_key] is None:
                    feedback.pop(optional_key)
            feedback_items[row[0]] = feedback
        return feedback_items

    def _load_user_usage_metrics(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, module_code, feature_code, user_segment,
                   window_start, window_end, active_users, event_count,
                   conversion_count, conversion_rate, avg_duration_seconds,
                   bounce_rate, error_count, source_channel, created_by,
                   created_at, updated_at
            FROM user_usage_metrics
            ORDER BY window_start, id
            """
        )
        metrics = {}
        for row in cursor.fetchall():
            metric = {
                "active_users": row[7],
                "avg_duration_seconds": float(row[11]) if row[11] is not None else None,
                "bounce_rate": float(row[12]) if row[12] is not None else None,
                "conversion_count": row[9],
                "conversion_rate": float(row[10]) if row[10] is not None else None,
                "created_at": row[16].isoformat() if row[16] else None,
                "created_by": row[15],
                "error_count": row[13],
                "event_count": row[8],
                "feature_code": row[3],
                "id": row[0],
                "module_code": row[2],
                "product_id": row[1],
                "source_channel": row[14],
                "updated_at": row[17].isoformat() if row[17] else None,
                "user_segment": row[4],
                "window_end": row[6].isoformat() if row[6] else None,
                "window_start": row[5].isoformat() if row[5] else None,
            }
            for optional_key in (
                "avg_duration_seconds",
                "bounce_rate",
                "conversion_rate",
                "created_at",
                "module_code",
                "source_channel",
                "updated_at",
            ):
                if metric[optional_key] is None:
                    metric.pop(optional_key)
            metrics[row[0]] = metric
        return metrics

    def _load_collector_runs(self, cursor) -> dict[str, dict[str, Any]]:
        import json

        cursor.execute(
            """
            SELECT id, collector_type, product_id, status, source_system,
                   started_at, finished_at, records_imported, error_message,
                   payload_summary, created_by, created_at, updated_at
            FROM collector_runs
            ORDER BY started_at, id
            """
        )
        runs = {}
        for row in cursor.fetchall():
            payload_summary = row[9] or {}
            if isinstance(payload_summary, str):
                payload_summary = json.loads(payload_summary)
            run = {
                "collector_type": row[1],
                "created_at": row[11].isoformat() if row[11] else None,
                "created_by": row[10],
                "error_message": row[8],
                "finished_at": row[6].isoformat() if row[6] else None,
                "id": row[0],
                "payload_summary": payload_summary,
                "product_id": row[2],
                "records_imported": row[7],
                "source_system": row[4],
                "started_at": row[5].isoformat() if row[5] else None,
                "status": row[3],
                "updated_at": row[12].isoformat() if row[12] else None,
            }
            runs[row[0]] = run
        return runs

    def _load_pending_attribution_items(self, cursor) -> dict[str, dict[str, Any]]:
        import json

        cursor.execute(
            """
            SELECT id, source_type, source_system, collector_run_id, raw_subject_id,
                   summary, raw_payload, suggested_product_id, suggested_module_code,
                   confidence, status, resolution_action, resolution_note,
                   resolved_product_id, resolved_module_code, resolved_requirement_id,
                   resolved_subject_type, resolved_subject_id, resolved_by, resolved_at,
                   created_by, created_at, updated_at
            FROM pending_attribution_items
            ORDER BY created_at, id
            """
        )
        items = {}
        for row in cursor.fetchall():
            raw_payload = row[6] or {}
            if isinstance(raw_payload, str):
                raw_payload = json.loads(raw_payload)
            item = {
                "collector_run_id": row[3],
                "confidence": float(row[9]) if row[9] is not None else None,
                "created_at": row[21].isoformat() if row[21] else None,
                "created_by": row[20],
                "id": row[0],
                "raw_payload": raw_payload,
                "raw_subject_id": row[4],
                "resolution_action": row[11],
                "resolution_note": row[12],
                "resolved_at": row[19].isoformat() if row[19] else None,
                "resolved_by": row[18],
                "resolved_module_code": row[14],
                "resolved_product_id": row[13],
                "resolved_requirement_id": row[15],
                "resolved_subject_id": row[17],
                "resolved_subject_type": row[16],
                "source_system": row[2],
                "source_type": row[1],
                "status": row[10],
                "suggested_module_code": row[8],
                "suggested_product_id": row[7],
                "summary": row[5],
                "updated_at": row[22].isoformat() if row[22] else None,
            }
            items[row[0]] = item
        return items

    def _load_gitlab_daily_code_metrics(self, cursor) -> dict[str, dict[str, Any]]:
        import json

        cursor.execute(
            """
            SELECT id, product_id, repository_id, metric_date, commit_count,
                   active_author_count, merge_request_count, changed_files,
                   additions, deletions, quality_score, risk_count,
                   author_metrics, status, source_channel, collected_at,
                   created_by, created_at, updated_at
            FROM gitlab_daily_code_metrics
            ORDER BY metric_date, id
            """
        )
        metrics = {}
        for row in cursor.fetchall():
            author_metrics = row[12] or []
            if isinstance(author_metrics, str):
                author_metrics = json.loads(author_metrics)
            metric = {
                "active_author_count": row[5],
                "additions": row[8],
                "author_metrics": author_metrics,
                "changed_files": row[7],
                "collected_at": row[15].isoformat() if row[15] else None,
                "commit_count": row[4],
                "created_at": row[17].isoformat() if row[17] else None,
                "created_by": row[16],
                "deletions": row[9],
                "id": row[0],
                "merge_request_count": row[6],
                "metric_date": row[3].isoformat() if row[3] else None,
                "product_id": row[1],
                "quality_score": float(row[10]) if row[10] is not None else None,
                "repository_id": row[2],
                "risk_count": row[11],
                "source_channel": row[14],
                "status": row[13],
                "updated_at": row[18].isoformat() if row[18] else None,
            }
            for optional_key in (
                "collected_at",
                "created_at",
                "quality_score",
                "source_channel",
                "updated_at",
            ):
                if metric[optional_key] is None:
                    metric.pop(optional_key)
            metrics[row[0]] = metric
        return metrics

    def _load_jenkins_release_records(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, version_id, job_name, build_id, build_number,
                   environment, status, trigger_actor, commit_sha, duration_seconds,
                   started_at, deployed_at, failure_reason, source_channel,
                   created_by, created_at, updated_at
            FROM jenkins_release_records
            ORDER BY COALESCE(deployed_at, created_at), id
            """
        )
        releases = {}
        for row in cursor.fetchall():
            release = {
                "build_id": row[4],
                "build_number": row[5],
                "commit_sha": row[9],
                "created_at": row[16].isoformat() if row[16] else None,
                "created_by": row[15],
                "deployed_at": row[12].isoformat() if row[12] else None,
                "duration_seconds": row[10],
                "environment": row[6],
                "failure_reason": row[13],
                "id": row[0],
                "job_name": row[3],
                "product_id": row[1],
                "source_channel": row[14],
                "started_at": row[11].isoformat() if row[11] else None,
                "status": row[7],
                "trigger_actor": row[8],
                "updated_at": row[17].isoformat() if row[17] else None,
                "version_id": row[2],
            }
            for optional_key in (
                "build_number",
                "commit_sha",
                "created_at",
                "deployed_at",
                "duration_seconds",
                "failure_reason",
                "source_channel",
                "started_at",
                "trigger_actor",
                "updated_at",
            ):
                if release[optional_key] is None:
                    release.pop(optional_key)
            releases[row[0]] = release
        return releases

    def _load_online_log_metrics(self, cursor) -> dict[str, dict[str, Any]]:
        import json

        cursor.execute(
            """
            SELECT id, product_id, module_code, environment, window_start, window_end,
                   request_count, error_count, error_rate, p95_latency_ms,
                   p99_latency_ms, core_event_count, top_errors, anomaly_summary,
                   status, source_channel, created_by, created_at, updated_at
            FROM online_log_metrics
            ORDER BY window_start, id
            """
        )
        metrics = {}
        for row in cursor.fetchall():
            top_errors = row[12] or []
            if isinstance(top_errors, str):
                top_errors = json.loads(top_errors)
            metric = {
                "anomaly_summary": row[13],
                "core_event_count": row[11],
                "created_at": row[17].isoformat() if row[17] else None,
                "created_by": row[16],
                "environment": row[3],
                "error_count": row[7],
                "error_rate": float(row[8]) if row[8] is not None else None,
                "id": row[0],
                "module_code": row[2],
                "p95_latency_ms": float(row[9]) if row[9] is not None else None,
                "p99_latency_ms": float(row[10]) if row[10] is not None else None,
                "product_id": row[1],
                "request_count": row[6],
                "source_channel": row[15],
                "status": row[14],
                "top_errors": top_errors,
                "updated_at": row[18].isoformat() if row[18] else None,
                "window_end": row[5].isoformat() if row[5] else None,
                "window_start": row[4].isoformat() if row[4] else None,
            }
            for optional_key in (
                "anomaly_summary",
                "created_at",
                "error_rate",
                "module_code",
                "p95_latency_ms",
                "p99_latency_ms",
                "source_channel",
                "updated_at",
            ):
                if metric[optional_key] is None:
                    metric.pop(optional_key)
            metrics[row[0]] = metric
        return metrics

    def _load_iteration_plan_suggestions(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, planning_cycle, version_id, module_codes, title,
                   status, priority, priority_score, confidence_level,
                   recommendation_reason, business_value, risk_signals, dependencies,
                   estimated_effort, evidence, evidence_insufficient, created_by,
                   converted_requirement_id, created_at, updated_at
            FROM iteration_plan_suggestions
            ORDER BY created_at, id
            """
        )
        suggestions = {}
        for row in cursor.fetchall():
            suggestion = {
                "business_value": row[11],
                "confidence_level": row[9],
                "converted_requirement_id": row[18],
                "created_at": row[19].isoformat() if row[19] else None,
                "created_by": row[17],
                "dependencies": list(row[13] or []),
                "estimated_effort": row[14],
                "evidence": list(row[15] or []),
                "evidence_insufficient": row[16],
                "id": row[0],
                "module_codes": list(row[4] or []),
                "planning_cycle": row[2],
                "priority": row[7],
                "priority_score": row[8],
                "product_id": row[1],
                "recommendation_reason": row[10],
                "risk_signals": list(row[12] or []),
                "status": row[6],
                "title": row[5],
                "updated_at": row[20].isoformat() if row[20] else None,
                "version_id": row[3],
            }
            for optional_key in (
                "converted_requirement_id",
                "created_at",
                "updated_at",
                "version_id",
            ):
                if suggestion[optional_key] is None:
                    suggestion.pop(optional_key)
            suggestions[row[0]] = suggestion
        return suggestions

    def _load_iteration_plan_decisions(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, suggestion_id, decision, comment, edited_title, edited_scope,
                   convert_to_requirement, created_requirement_id, decided_by, decided_at,
                   created_at, updated_at
            FROM iteration_plan_decisions
            ORDER BY decided_at, id
            """
        )
        decisions = {}
        for row in cursor.fetchall():
            decision = {
                "comment": row[3],
                "convert_to_requirement": row[6],
                "created_at": row[10].isoformat() if row[10] else None,
                "created_requirement_id": row[7],
                "decided_at": row[9].isoformat() if row[9] else None,
                "decided_by": row[8],
                "decision": row[2],
                "edited_scope": row[5],
                "edited_title": row[4],
                "id": row[0],
                "suggestion_id": row[1],
                "updated_at": row[11].isoformat() if row[11] else None,
            }
            for optional_key in (
                "comment",
                "created_at",
                "created_requirement_id",
                "decided_at",
                "edited_scope",
                "edited_title",
                "updated_at",
            ):
                if decision[optional_key] is None:
                    decision.pop(optional_key)
            decisions[row[0]] = decision
        return decisions

    def _load_lifecycle_context_edges(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, source_subject_type, source_subject_id, target_subject_type,
                   target_subject_id, relation_type, product_id, version_id,
                   module_code, confidence, source_module, observed_at, metadata,
                   summary, created_at, updated_at
            FROM lifecycle_context_edges
            ORDER BY observed_at, id
            """
        )
        edges = {}
        for row in cursor.fetchall():
            edge = {
                "confidence": float(row[9]) if row[9] is not None else 1.0,
                "created_at": row[14].isoformat() if row[14] else None,
                "id": row[0],
                "metadata": dict(row[12] or {}),
                "module_code": row[8],
                "observed_at": row[11].isoformat() if row[11] else None,
                "product_id": row[6],
                "relation_type": row[5],
                "source_module": row[10],
                "source_subject_id": row[2],
                "source_subject_type": row[1],
                "summary": row[13],
                "target_subject_id": row[4],
                "target_subject_type": row[3],
                "updated_at": row[15].isoformat() if row[15] else None,
                "version_id": row[7],
            }
            for optional_key in (
                "created_at",
                "module_code",
                "observed_at",
                "product_id",
                "summary",
                "updated_at",
                "version_id",
            ):
                if edge[optional_key] is None:
                    edge.pop(optional_key)
            edges[row[0]] = edge
        return edges

    def _load_lifecycle_risk_signals(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, version_id, module_code, requirement_id, task_id,
                   risk_type, severity, source_subject_type, source_subject_id,
                   impact_summary, recommendation, observed_at, created_at, updated_at
            FROM lifecycle_risk_signals
            ORDER BY observed_at, id
            """
        )
        risks = {}
        for row in cursor.fetchall():
            risk = {
                "created_at": row[13].isoformat() if row[13] else None,
                "id": row[0],
                "impact_summary": row[10],
                "module_code": row[3],
                "observed_at": row[12].isoformat() if row[12] else None,
                "product_id": row[1],
                "recommendation": row[11],
                "requirement_id": row[4],
                "risk_type": row[6],
                "severity": row[7],
                "source_subject_id": row[9],
                "source_subject_type": row[8],
                "task_id": row[5],
                "updated_at": row[14].isoformat() if row[14] else None,
                "version_id": row[2],
            }
            for optional_key in (
                "created_at",
                "module_code",
                "observed_at",
                "product_id",
                "requirement_id",
                "task_id",
                "updated_at",
                "version_id",
            ):
                if risk[optional_key] is None:
                    risk.pop(optional_key)
            risks[row[0]] = risk
        return risks

    def _load_dashboard_metric_snapshots(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, product_id, time_range, window_start, window_end, metrics,
                   created_at, updated_at
            FROM dashboard_metric_snapshots
            ORDER BY updated_at, id
            """
        )
        snapshots = {}
        for row in cursor.fetchall():
            snapshot = {
                "created_at": row[6].isoformat() if row[6] else None,
                "id": row[0],
                "metrics": dict(row[5] or {}),
                "product_id": row[1],
                "time_range": row[2],
                "updated_at": row[7].isoformat() if row[7] else None,
                "window_end": row[4].isoformat() if row[4] else None,
                "window_start": row[3].isoformat() if row[3] else None,
            }
            for optional_key in (
                "created_at",
                "product_id",
                "updated_at",
                "window_end",
                "window_start",
            ):
                if snapshot[optional_key] is None:
                    snapshot.pop(optional_key)
            snapshots[row[0]] = snapshot
        return snapshots

    def _load_model_gateway_configs(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, name, provider, base_url, api_key_ref, default_chat_model,
                   default_embedding_model, timeout_seconds, max_retries, status,
                   is_default, created_at, updated_at, embedding_connection_mode,
                   embedding_base_url, embedding_api_key_ref, embedding_dimension
            FROM model_gateway_configs
            ORDER BY id
            """
        )
        configs = {}
        for row in cursor.fetchall():
            config = {
                "api_key": row[4],
                "base_url": row[3],
                "created_at": row[11].isoformat() if row[11] else None,
                "default_chat_model": row[5],
                "default_embedding_model": row[6],
                "embedding_api_key": row[15],
                "embedding_base_url": row[14],
                "embedding_connection_mode": row[13],
                "embedding_dimension": row[16],
                "id": row[0],
                "is_default": row[10],
                "max_retries": row[8],
                "name": row[1],
                "provider": row[2],
                "status": row[9],
                "timeout_seconds": row[7],
                "updated_at": row[12].isoformat() if row[12] else None,
            }
            for optional_key in (
                "api_key",
                "created_at",
                "default_embedding_model",
                "embedding_api_key",
                "embedding_base_url",
                "embedding_connection_mode",
                "embedding_dimension",
                "updated_at",
            ):
                if config[optional_key] is None:
                    config.pop(optional_key)
            configs[row[0]] = config
        return configs

    def _load_model_gateway_logs(self, cursor) -> list[dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, ai_task_id, provider, model, purpose, tokens, latency_ms,
                   status, error, model_gateway_config_id, created_at, updated_at
            FROM model_gateway_logs
            ORDER BY created_at, id
            """
        )
        logs = []
        for row in cursor.fetchall():
            log = {
                "ai_task_id": row[1],
                "created_at": row[10].isoformat() if row[10] else None,
                "error": row[8],
                "id": row[0],
                "latency_ms": row[6],
                "model": row[3],
                "model_gateway_config_id": row[9],
                "provider": row[2],
                "purpose": row[4],
                "status": row[7],
                "tokens": dict(row[5] or {}),
                "updated_at": row[11].isoformat() if row[11] else None,
            }
            for optional_key in (
                "ai_task_id",
                "created_at",
                "error",
                "model_gateway_config_id",
                "updated_at",
            ):
                if log[optional_key] is None:
                    log.pop(optional_key)
            logs.append(log)
        return logs

    def _load_assistant_conversations(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, user_id, product_id, title, message_count, last_message_at,
                   created_at, updated_at
            FROM assistant_conversations
            ORDER BY updated_at, id
            """
        )
        conversations = {}
        for row in cursor.fetchall():
            conversation = {
                "created_at": row[6].isoformat() if row[6] else None,
                "id": row[0],
                "last_message_at": row[5].isoformat() if row[5] else None,
                "message_count": row[4],
                "product_id": row[2],
                "title": row[3],
                "updated_at": row[7].isoformat() if row[7] else None,
                "user_id": row[1],
            }
            for optional_key in (
                "created_at",
                "last_message_at",
                "product_id",
                "updated_at",
            ):
                if conversation[optional_key] is None:
                    conversation.pop(optional_key)
            conversations[row[0]] = conversation
        return conversations

    def _load_assistant_messages(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, conversation_id, user_id, role, content, product_id, model,
                   suggestions, created_at, updated_at
            FROM assistant_messages
            ORDER BY created_at, id
            """
        )
        messages = {}
        for row in cursor.fetchall():
            message = {
                "content": row[4],
                "conversation_id": row[1],
                "created_at": row[8].isoformat() if row[8] else None,
                "id": row[0],
                "model": row[6],
                "product_id": row[5],
                "role": row[3],
                "suggestions": list(row[7] or []),
                "updated_at": row[9].isoformat() if row[9] else None,
                "user_id": row[2],
            }
            for optional_key in ("created_at", "model", "product_id", "updated_at"):
                if message[optional_key] is None:
                    message.pop(optional_key)
            messages[row[0]] = message
        return messages

    def _load_gitlab_mr_snapshots(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, repository_id, product_id, version_id, project_id, project_path,
                   mr_iid, title, author, source_branch, target_branch, base_sha,
                   head_sha, diff_refs, changed_files_summary, diff_storage_ref,
                   diff_size_bytes, diff_limit_bytes, snapshot_hash, requirement_id,
                   technical_solution_task_id, created_by, created_at, updated_at,
                   writeback_allowed
            FROM gitlab_mr_snapshots
            ORDER BY created_at, id
            """
        )
        snapshots = {}
        for row in cursor.fetchall():
            snapshot = {
                "author": dict(row[8] or {}),
                "base_sha": row[11],
                "changed_files_summary": list(row[14] or []),
                "created_at": row[22].isoformat() if row[22] else None,
                "created_by": row[21],
                "diff_limit_bytes": row[17],
                "diff_refs": dict(row[13] or {}),
                "diff_size_bytes": row[16],
                "diff_storage_ref": row[15],
                "head_sha": row[12],
                "id": row[0],
                "mr_iid": row[6],
                "product_id": row[2],
                "project_id": row[4],
                "project_path": row[5],
                "repository_id": row[1],
                "requirement_id": row[19],
                "snapshot_hash": row[18],
                "source_branch": row[9],
                "target_branch": row[10],
                "technical_solution_task_id": row[20],
                "title": row[7],
                "updated_at": row[23].isoformat() if row[23] else None,
                "version_id": row[3],
                "writeback_allowed": row[24],
            }
            for optional_key in (
                "base_sha",
                "created_at",
                "project_id",
                "project_path",
                "updated_at",
                "version_id",
            ):
                if snapshot[optional_key] is None:
                    snapshot.pop(optional_key)
            snapshots[row[0]] = snapshot
        return snapshots

    def _load_code_review_reports(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, task_id, gitlab_mr_snapshot_id, executor, summary, risk_level,
                   findings, status, review_id, archived_at, error_code,
                   gitlab_writeback_performed, created_at, updated_at
            FROM code_review_reports
            ORDER BY created_at, id
            """
        )
        reports = {}
        for row in cursor.fetchall():
            report = {
                "archived_at": row[9].isoformat() if row[9] else None,
                "created_at": row[12].isoformat() if row[12] else None,
                "error_code": row[10],
                "executor": dict(row[3] or {}),
                "findings": list(row[6] or []),
                "gitlab_mr_snapshot_id": row[2],
                "gitlab_writeback_performed": row[11],
                "id": row[0],
                "review_id": row[8],
                "risk_level": row[5],
                "status": row[7],
                "summary": row[4],
                "task_id": row[1],
                "updated_at": row[13].isoformat() if row[13] else None,
            }
            for optional_key in (
                "archived_at",
                "created_at",
                "error_code",
                "review_id",
                "updated_at",
            ):
                if report[optional_key] is None:
                    report.pop(optional_key)
            reports[row[0]] = report
        return reports

    def _load_mock_writebacks(self, cursor) -> dict[str, dict[str, Any]]:
        cursor.execute(
            """
            SELECT id, source_task_id, title, status, idempotency_key, payload,
                   created_at, updated_at
            FROM mock_issues
            ORDER BY created_at, id
            """
        )
        writebacks: dict[str, dict[str, Any]] = {}
        for row in cursor.fetchall():
            issue_payload = dict(row[5] or {})
            issue = {
                **issue_payload,
                "id": row[0],
                "source_task_id": row[1],
                "status": row[3],
                "title": row[2],
            }
            if row[6] is not None:
                issue["created_at"] = row[6].isoformat()
            if row[7] is not None:
                issue["updated_at"] = row[7].isoformat()
            idempotency_key = row[4]
            writeback = writebacks.setdefault(
                idempotency_key,
                {
                    "idempotency_key": idempotency_key,
                    "issues": [],
                    "status": "completed",
                    "task_id": row[1],
                },
            )
            writeback["issues"].append(issue)
        return writebacks

    def _delete_missing(
        self,
        cursor,
        table_name: str,
        items: dict[str, dict[str, Any]],
    ) -> None:
        if not items:
            cursor.execute(f"DELETE FROM {table_name}")  # noqa: S608
            return
        placeholders = ", ".join(["%s"] * len(items))
        cursor.execute(
            f"DELETE FROM {table_name} WHERE id NOT IN ({placeholders})",  # noqa: S608
            tuple(items.keys()),
        )

    def _delete_missing_ids(self, cursor, table_name: str, item_ids: list[str]) -> None:
        if not item_ids:
            cursor.execute(f"DELETE FROM {table_name}")  # noqa: S608
            return
        placeholders = ", ".join(["%s"] * len(item_ids))
        cursor.execute(
            f"DELETE FROM {table_name} WHERE id NOT IN ({placeholders})",  # noqa: S608
            tuple(item_ids),
        )

    def _upsert_products(self, cursor, products: dict[str, dict[str, Any]]) -> None:
        for product in products.values():
            cursor.execute(
                """
                INSERT INTO products (
                  id, code, name, description, owner_team, status, display_order, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                  code = EXCLUDED.code,
                  name = EXCLUDED.name,
                  description = EXCLUDED.description,
                  owner_team = EXCLUDED.owner_team,
                  status = EXCLUDED.status,
                  display_order = EXCLUDED.display_order,
                  updated_at = now()
                """,
                (
                    product["id"],
                    product["code"],
                    product["name"],
                    product.get("description"),
                    product.get("owner_team"),
                    product.get("status", "active"),
                    product.get("display_order", 0),
                ),
            )

    def _upsert_product_versions(self, cursor, versions: dict[str, dict[str, Any]]) -> None:
        for version in versions.values():
            cursor.execute(
                """
                INSERT INTO product_versions (
                  id, product_id, code, name, description, status, start_date, release_date,
                  updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  code = EXCLUDED.code,
                  name = EXCLUDED.name,
                  description = EXCLUDED.description,
                  status = EXCLUDED.status,
                  start_date = EXCLUDED.start_date,
                  release_date = EXCLUDED.release_date,
                  updated_at = now()
                """,
                (
                    version["id"],
                    version["product_id"],
                    version["code"],
                    version["name"],
                    version.get("description"),
                    version.get("status", "planning"),
                    version.get("start_date"),
                    version.get("release_date"),
                ),
            )

    def _upsert_product_modules(self, cursor, modules: dict[str, dict[str, Any]]) -> None:
        for module in modules.values():
            cursor.execute(
                """
                INSERT INTO product_modules (
                  id, product_id, code, name, description, owner_team, status, display_order,
                  updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  code = EXCLUDED.code,
                  name = EXCLUDED.name,
                  description = EXCLUDED.description,
                  owner_team = EXCLUDED.owner_team,
                  status = EXCLUDED.status,
                  display_order = EXCLUDED.display_order,
                  updated_at = now()
                """,
                (
                    module["id"],
                    module["product_id"],
                    module["code"],
                    module["name"],
                    module.get("description"),
                    module.get("owner_team"),
                    module.get("status", "active"),
                    module.get("display_order", 0),
                ),
            )

    def _upsert_product_git_repositories(
        self,
        cursor,
        repositories: dict[str, dict[str, Any]],
    ) -> None:
        for repository in repositories.values():
            cursor.execute(
                """
                INSERT INTO product_git_repositories (
                  id, product_id, repo_type, name, remote_url, git_provider, project_id,
                  project_path, credential_ref, default_branch, root_path, status, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  repo_type = EXCLUDED.repo_type,
                  name = EXCLUDED.name,
                  remote_url = EXCLUDED.remote_url,
                  git_provider = EXCLUDED.git_provider,
                  project_id = EXCLUDED.project_id,
                  project_path = EXCLUDED.project_path,
                  credential_ref = EXCLUDED.credential_ref,
                  default_branch = EXCLUDED.default_branch,
                  root_path = EXCLUDED.root_path,
                  status = EXCLUDED.status,
                  updated_at = now()
                """,
                (
                    repository["id"],
                    repository["product_id"],
                    repository.get("repo_type", "code"),
                    repository["name"],
                    repository.get("remote_url"),
                    repository.get("git_provider", "gitlab"),
                    repository.get("project_id"),
                    repository.get("project_path"),
                    repository.get("credential_ref"),
                    repository.get("default_branch", "main"),
                    repository.get("root_path", "/"),
                    repository.get("status", "active"),
                ),
            )

    def _upsert_related_systems(
        self,
        cursor,
        related_systems: dict[str, dict[str, Any]],
    ) -> None:
        for related_system in related_systems.values():
            cursor.execute(
                """
                INSERT INTO related_systems (
                  id, product_id, code, name, description, owner_team, status,
                  display_order, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  code = EXCLUDED.code,
                  name = EXCLUDED.name,
                  description = EXCLUDED.description,
                  owner_team = EXCLUDED.owner_team,
                  status = EXCLUDED.status,
                  display_order = EXCLUDED.display_order,
                  updated_at = now()
                """,
                (
                    related_system["id"],
                    related_system.get("product_id"),
                    related_system["code"],
                    related_system["name"],
                    related_system.get("description"),
                    related_system.get("owner_team"),
                    related_system.get("status", "active"),
                    related_system.get("display_order", 0),
                ),
            )

    def _upsert_requirements(self, cursor, requirements: dict[str, dict[str, Any]]) -> None:
        import json

        for requirement in requirements.values():
            created_at = requirement.get("created_at")
            updated_at = requirement.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO requirements (
                  id, brain_app_id, title, product_id, version_id, module_code,
                  description, priority,
                  status, created_by, approval_comment, rejection_reason, task_ids,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  brain_app_id = EXCLUDED.brain_app_id,
                  title = EXCLUDED.title,
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  module_code = EXCLUDED.module_code,
                  description = EXCLUDED.description,
                  priority = EXCLUDED.priority,
                  status = EXCLUDED.status,
                  created_by = EXCLUDED.created_by,
                  approval_comment = EXCLUDED.approval_comment,
                  rejection_reason = EXCLUDED.rejection_reason,
                  task_ids = EXCLUDED.task_ids,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    requirement["id"],
                    requirement.get("brain_app_id", DEFAULT_BRAIN_APP_ID),
                    requirement["title"],
                    requirement["product_id"],
                    requirement["version_id"],
                    requirement.get("module_code"),
                    requirement["content"],
                    requirement.get("priority", "P1"),
                    requirement.get("status", "submitted"),
                    requirement["created_by"],
                    requirement.get("approval_comment"),
                    requirement.get("rejection_reason"),
                    json.dumps(requirement.get("task_ids", []), ensure_ascii=False),
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_ai_tasks(self, cursor, ai_tasks: dict[str, dict[str, Any]]) -> None:
        import json

        for task in ai_tasks.values():
            created_at = task.get("created_at")
            updated_at = task.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO ai_tasks (
                  id, brain_app_id, requirement_id, task_type, title, status,
                  product_id, version_id,
                  module_code, requirement_snapshot, product_context, input_json, output_json,
                  current_step, error_code, error_message, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb,
                  %s::jsonb, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  brain_app_id = EXCLUDED.brain_app_id,
                  requirement_id = EXCLUDED.requirement_id,
                  task_type = EXCLUDED.task_type,
                  title = EXCLUDED.title,
                  status = EXCLUDED.status,
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  module_code = EXCLUDED.module_code,
                  requirement_snapshot = EXCLUDED.requirement_snapshot,
                  product_context = EXCLUDED.product_context,
                  input_json = EXCLUDED.input_json,
                  output_json = EXCLUDED.output_json,
                  current_step = EXCLUDED.current_step,
                  error_code = EXCLUDED.error_code,
                  error_message = EXCLUDED.error_message,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    task["id"],
                    task.get("brain_app_id", DEFAULT_BRAIN_APP_ID),
                    task["requirement_id"],
                    task["task_type"],
                    task["title"],
                    task.get("status", "draft"),
                    task["product_id"],
                    task["version_id"],
                    task.get("module_code"),
                    json.dumps(task.get("requirement_snapshot"), ensure_ascii=False),
                    json.dumps(task.get("product_context", {}), ensure_ascii=False),
                    json.dumps(task.get("input_json", {}), ensure_ascii=False),
                    json.dumps(task.get("output_json"), ensure_ascii=False),
                    task.get("current_step"),
                    task.get("error_code"),
                    task.get("error_message"),
                    task["created_by"],
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_graph_runs(self, cursor, graph_runs: dict[str, dict[str, Any]]) -> None:
        import json

        for graph_run in graph_runs.values():
            created_at = graph_run.get("created_at") or graph_run.get("started_at")
            updated_at = graph_run.get("updated_at") or graph_run.get("completed_at") or created_at
            cursor.execute(
                """
                INSERT INTO graph_runs (
                  id, ai_task_id, task_type, status, current_step, checkpoint_id,
                  runtime, node_path, state_snapshot, started_at, completed_at,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb,
                  COALESCE(%s::timestamptz, now()), %s::timestamptz,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  ai_task_id = EXCLUDED.ai_task_id,
                  task_type = EXCLUDED.task_type,
                  status = EXCLUDED.status,
                  current_step = EXCLUDED.current_step,
                  checkpoint_id = EXCLUDED.checkpoint_id,
                  runtime = EXCLUDED.runtime,
                  node_path = EXCLUDED.node_path,
                  state_snapshot = EXCLUDED.state_snapshot,
                  completed_at = EXCLUDED.completed_at,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    graph_run["id"],
                    graph_run["ai_task_id"],
                    graph_run["task_type"],
                    graph_run["status"],
                    graph_run.get("current_step"),
                    graph_run.get("checkpoint_id"),
                    graph_run.get("runtime"),
                    json.dumps(graph_run.get("node_path", []), ensure_ascii=False),
                    json.dumps(graph_run.get("state_snapshot", {}), ensure_ascii=False),
                    graph_run.get("started_at"),
                    graph_run.get("completed_at"),
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_graph_checkpoints(
        self,
        cursor,
        graph_checkpoints: dict[str, dict[str, Any]],
    ) -> None:
        import json

        for checkpoint in graph_checkpoints.values():
            created_at = checkpoint.get("created_at")
            updated_at = checkpoint.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO graph_checkpoints (
                  id, graph_run_id, ai_task_id, current_step, state_snapshot, created_at,
                  updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s::jsonb, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  graph_run_id = EXCLUDED.graph_run_id,
                  ai_task_id = EXCLUDED.ai_task_id,
                  current_step = EXCLUDED.current_step,
                  state_snapshot = EXCLUDED.state_snapshot,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    checkpoint["id"],
                    checkpoint["graph_run_id"],
                    checkpoint["ai_task_id"],
                    checkpoint["current_step"],
                    json.dumps(checkpoint.get("state_snapshot", {}), ensure_ascii=False),
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_human_reviews(self, cursor, human_reviews: dict[str, dict[str, Any]]) -> None:
        import json

        for review in human_reviews.values():
            created_at = review.get("created_at")
            updated_at = review.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO human_reviews (
                  id, ai_task_id, stage, status, version, content, edited_content,
                  decision_reason, decided_by, questions, decided_at, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s::jsonb,
                  %s::timestamptz, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  ai_task_id = EXCLUDED.ai_task_id,
                  stage = EXCLUDED.stage,
                  status = EXCLUDED.status,
                  version = EXCLUDED.version,
                  content = EXCLUDED.content,
                  edited_content = EXCLUDED.edited_content,
                  decision_reason = EXCLUDED.decision_reason,
                  decided_by = EXCLUDED.decided_by,
                  questions = EXCLUDED.questions,
                  decided_at = EXCLUDED.decided_at,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    review["id"],
                    review["ai_task_id"],
                    review["stage"],
                    review.get("status", "pending"),
                    review.get("version", 1),
                    json.dumps(review.get("content", {}), ensure_ascii=False),
                    json.dumps(review.get("edited_content"), ensure_ascii=False),
                    review.get("decision_reason"),
                    review.get("decided_by"),
                    json.dumps(review.get("questions", []), ensure_ascii=False),
                    review.get("decided_at"),
                    created_at,
                    updated_at,
                ),
            )

    def _clean_knowledge_deposit_references(
        self,
        documents: dict[str, dict[str, Any]],
        deposits: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        cleaned = deepcopy(deposits)
        for deposit in cleaned.values():
            if deposit.get("knowledge_document_id") not in documents:
                deposit["knowledge_document_id"] = None
        return cleaned

    def _clean_knowledge_chunk_references(
        self,
        documents: dict[str, dict[str, Any]],
        chunks: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        return {
            chunk_id: chunk
            for chunk_id, chunk in deepcopy(chunks).items()
            if chunk.get("document_id") in documents
        }

    def _clear_dangling_knowledge_chunk_documents(
        self,
        cursor,
        documents: dict[str, dict[str, Any]],
    ) -> None:
        if not documents:
            cursor.execute("DELETE FROM knowledge_chunks")
            return
        placeholders = ", ".join(["%s"] * len(documents))
        cursor.execute(
            f"""
            DELETE FROM knowledge_chunks
            WHERE document_id NOT IN ({placeholders})
            """,  # noqa: S608
            tuple(documents.keys()),
        )

    def _clear_dangling_knowledge_deposit_documents(
        self,
        cursor,
        documents: dict[str, dict[str, Any]],
    ) -> None:
        if not documents:
            cursor.execute("UPDATE knowledge_deposits SET knowledge_document_id = NULL")
            return
        placeholders = ", ".join(["%s"] * len(documents))
        cursor.execute(
            f"""
            UPDATE knowledge_deposits
            SET knowledge_document_id = NULL
            WHERE knowledge_document_id IS NOT NULL
              AND knowledge_document_id NOT IN ({placeholders})
            """,  # noqa: S608
            tuple(documents.keys()),
        )

    def _upsert_knowledge_documents(
        self,
        cursor,
        documents: dict[str, dict[str, Any]],
    ) -> None:
        import json

        for document in documents.values():
            created_at = document.get("created_at")
            updated_at = document.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO knowledge_documents (
                  id, brain_app_id, product_id, version_id, title, content, source_type,
                  doc_type, permission_scope, permission_roles, index_status, index_error,
                  vector_index_error, tags, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s,
                  %s, %s::jsonb, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  brain_app_id = EXCLUDED.brain_app_id,
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  title = EXCLUDED.title,
                  content = EXCLUDED.content,
                  source_type = EXCLUDED.source_type,
                  doc_type = EXCLUDED.doc_type,
                  permission_scope = EXCLUDED.permission_scope,
                  permission_roles = EXCLUDED.permission_roles,
                  index_status = EXCLUDED.index_status,
                  index_error = EXCLUDED.index_error,
                  vector_index_error = EXCLUDED.vector_index_error,
                  tags = EXCLUDED.tags,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    document["id"],
                    document.get("brain_app_id", "rd_brain"),
                    document.get("product_id"),
                    document.get("version_id"),
                    document["title"],
                    document["content"],
                    document.get("source_type", "manual"),
                    document.get("doc_type", "manual"),
                    json.dumps(document.get("permission_scope", {}), ensure_ascii=False),
                    json.dumps(document.get("permission_roles", ["admin"]), ensure_ascii=False),
                    document.get("index_status", "pending_index"),
                    document.get("index_error"),
                    document.get("vector_index_error"),
                    json.dumps(document.get("tags", []), ensure_ascii=False),
                    document["created_by"],
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_knowledge_chunks(
        self,
        cursor,
        chunks: dict[str, dict[str, Any]],
    ) -> None:
        import json

        for chunk in chunks.values():
            created_at = chunk.get("created_at")
            updated_at = chunk.get("updated_at") or created_at
            permission_scope = deepcopy(chunk.get("permission_scope", {}))
            if chunk.get("permission_roles"):
                permission_scope["roles"] = list(chunk["permission_roles"])
            cursor.execute(
                """
                INSERT INTO knowledge_chunks (
                  id, document_id, chunk_index, content, embedding, metadata,
                  permission_scope, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s::vector, %s::jsonb, %s::jsonb,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  document_id = EXCLUDED.document_id,
                  chunk_index = EXCLUDED.chunk_index,
                  content = EXCLUDED.content,
                  embedding = EXCLUDED.embedding,
                  metadata = EXCLUDED.metadata,
                  permission_scope = EXCLUDED.permission_scope,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    chunk["id"],
                    chunk["document_id"],
                    chunk["chunk_index"],
                    chunk["content"],
                    _vector_sql_literal(chunk.get("embedding")),
                    json.dumps(chunk.get("metadata", {}), ensure_ascii=False),
                    json.dumps(permission_scope, ensure_ascii=False),
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_knowledge_deposits(
        self,
        cursor,
        deposits: dict[str, dict[str, Any]],
    ) -> None:
        for deposit in deposits.values():
            created_at = deposit.get("created_at")
            updated_at = deposit.get("updated_at") or created_at
            content_hash = deposit.get("content_hash") or deposit["id"]
            cursor.execute(
                """
                INSERT INTO knowledge_deposits (
                  id, ai_task_id, deposit_type, title, content, content_hash, status,
                  knowledge_document_id, rejection_reason, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  ai_task_id = EXCLUDED.ai_task_id,
                  deposit_type = EXCLUDED.deposit_type,
                  title = EXCLUDED.title,
                  content = EXCLUDED.content,
                  content_hash = EXCLUDED.content_hash,
                  status = EXCLUDED.status,
                  knowledge_document_id = EXCLUDED.knowledge_document_id,
                  rejection_reason = EXCLUDED.rejection_reason,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    deposit["id"],
                    deposit["ai_task_id"],
                    deposit.get("deposit_type", "task_output"),
                    deposit["title"],
                    deposit["content"],
                    content_hash,
                    deposit.get("status", "pending"),
                    deposit.get("knowledge_document_id"),
                    deposit.get("rejection_reason"),
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_audit_events(self, cursor, audit_events: list[dict[str, Any]]) -> None:
        import json

        for event in audit_events:
            created_at = event.get("created_at")
            updated_at = event.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO audit_events (
                  id, event_type, actor_id, ai_task_id, subject_type, subject_id, payload,
                  sequence, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s::jsonb, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  event_type = EXCLUDED.event_type,
                  actor_id = EXCLUDED.actor_id,
                  ai_task_id = EXCLUDED.ai_task_id,
                  subject_type = EXCLUDED.subject_type,
                  subject_id = EXCLUDED.subject_id,
                  payload = EXCLUDED.payload,
                  sequence = EXCLUDED.sequence,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    event["id"],
                    event["event_type"],
                    event["actor_id"],
                    event.get("ai_task_id"),
                    event.get("subject_type"),
                    event.get("subject_id"),
                    json.dumps(event.get("payload", {}), ensure_ascii=False),
                    event.get("sequence", 0),
                    created_at,
                    updated_at,
                ),
            )

    def _clean_bug_references(
        self,
        bugs: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        cleaned = deepcopy(bugs)
        for bug_id, bug in cleaned.items():
            duplicate_of_bug_id = bug.get("duplicate_of_bug_id")
            if duplicate_of_bug_id == bug_id or duplicate_of_bug_id not in cleaned:
                bug["duplicate_of_bug_id"] = None
        return cleaned

    def _clear_dangling_bug_duplicates(
        self,
        cursor,
        bugs: dict[str, dict[str, Any]],
    ) -> None:
        if not bugs:
            cursor.execute("UPDATE bugs SET duplicate_of_bug_id = NULL")
            return
        placeholders = ", ".join(["%s"] * len(bugs))
        cursor.execute(
            f"""
            UPDATE bugs
            SET duplicate_of_bug_id = NULL
            WHERE duplicate_of_bug_id IS NOT NULL
              AND duplicate_of_bug_id NOT IN ({placeholders})
            """,  # noqa: S608
            tuple(bugs.keys()),
        )

    def _upsert_bugs(self, cursor, bugs: dict[str, dict[str, Any]]) -> None:
        import json

        for bug in bugs.values():
            created_at = bug.get("created_at")
            updated_at = bug.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO bugs (
                  id, product_id, version_id, module_code, source, title, severity,
                  description, status, assignee, related_task_id, requirement_id,
                  reproduce_steps, evidence, duplicate_of_bug_id, created_by,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  %s::jsonb, %s::jsonb, NULL, %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  module_code = EXCLUDED.module_code,
                  source = EXCLUDED.source,
                  title = EXCLUDED.title,
                  severity = EXCLUDED.severity,
                  description = EXCLUDED.description,
                  status = EXCLUDED.status,
                  assignee = EXCLUDED.assignee,
                  related_task_id = EXCLUDED.related_task_id,
                  requirement_id = EXCLUDED.requirement_id,
                  reproduce_steps = EXCLUDED.reproduce_steps,
                  evidence = EXCLUDED.evidence,
                  duplicate_of_bug_id = NULL,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    bug["id"],
                    bug["product_id"],
                    bug.get("version_id"),
                    bug.get("module_code"),
                    bug["source"],
                    bug["title"],
                    bug["severity"],
                    bug["description"],
                    bug.get("status", "open"),
                    bug.get("assignee"),
                    bug.get("related_task_id"),
                    bug.get("requirement_id"),
                    json.dumps(bug.get("reproduce_steps", []), ensure_ascii=False),
                    json.dumps(bug.get("evidence", {}), ensure_ascii=False),
                    bug["created_by"],
                    created_at,
                    updated_at,
                ),
            )
        for bug in bugs.values():
            duplicate_of_bug_id = bug.get("duplicate_of_bug_id")
            if duplicate_of_bug_id:
                cursor.execute(
                    """
                    UPDATE bugs
                    SET duplicate_of_bug_id = %s, updated_at = COALESCE(%s::timestamptz, updated_at)
                    WHERE id = %s
                    """,
                    (duplicate_of_bug_id, bug.get("updated_at"), bug["id"]),
                )

    def _upsert_user_feedback(
        self,
        cursor,
        feedback_items: dict[str, dict[str, Any]],
    ) -> None:
        import json

        for feedback in feedback_items.values():
            created_at = feedback.get("created_at")
            updated_at = feedback.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO user_feedback (
                  id, product_id, module_code, feature_code, source_channel,
                  feedback_type, sentiment, satisfaction_score, content, tags,
                  related_requirement_id, status, triage_note, created_by,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  module_code = EXCLUDED.module_code,
                  feature_code = EXCLUDED.feature_code,
                  source_channel = EXCLUDED.source_channel,
                  feedback_type = EXCLUDED.feedback_type,
                  sentiment = EXCLUDED.sentiment,
                  satisfaction_score = EXCLUDED.satisfaction_score,
                  content = EXCLUDED.content,
                  tags = EXCLUDED.tags,
                  related_requirement_id = EXCLUDED.related_requirement_id,
                  status = EXCLUDED.status,
                  triage_note = EXCLUDED.triage_note,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    feedback["id"],
                    feedback["product_id"],
                    feedback.get("module_code"),
                    feedback.get("feature_code"),
                    feedback.get("source_channel", "in_app"),
                    feedback["feedback_type"],
                    feedback.get("sentiment"),
                    feedback.get("satisfaction_score"),
                    feedback["content"],
                    json.dumps(feedback.get("tags", []), ensure_ascii=False),
                    feedback.get("related_requirement_id"),
                    feedback.get("status", "open"),
                    feedback.get("triage_note"),
                    feedback["created_by"],
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_user_usage_metrics(
        self,
        cursor,
        metrics: dict[str, dict[str, Any]],
    ) -> None:
        for metric in metrics.values():
            created_at = metric.get("created_at")
            updated_at = metric.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO user_usage_metrics (
                  id, product_id, module_code, feature_code, user_segment,
                  window_start, window_end, active_users, event_count,
                  conversion_count, conversion_rate, avg_duration_seconds,
                  bounce_rate, error_count, source_channel, created_by,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s::timestamptz, %s::timestamptz,
                  %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  module_code = EXCLUDED.module_code,
                  feature_code = EXCLUDED.feature_code,
                  user_segment = EXCLUDED.user_segment,
                  window_start = EXCLUDED.window_start,
                  window_end = EXCLUDED.window_end,
                  active_users = EXCLUDED.active_users,
                  event_count = EXCLUDED.event_count,
                  conversion_count = EXCLUDED.conversion_count,
                  conversion_rate = EXCLUDED.conversion_rate,
                  avg_duration_seconds = EXCLUDED.avg_duration_seconds,
                  bounce_rate = EXCLUDED.bounce_rate,
                  error_count = EXCLUDED.error_count,
                  source_channel = EXCLUDED.source_channel,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    metric["id"],
                    metric["product_id"],
                    metric.get("module_code"),
                    metric["feature_code"],
                    metric.get("user_segment", "all"),
                    metric["window_start"],
                    metric["window_end"],
                    metric.get("active_users", 0),
                    metric.get("event_count", 0),
                    metric.get("conversion_count", 0),
                    metric.get("conversion_rate"),
                    metric.get("avg_duration_seconds"),
                    metric.get("bounce_rate"),
                    metric.get("error_count", 0),
                    metric.get("source_channel"),
                    metric["created_by"],
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_gitlab_daily_code_metrics(
        self,
        cursor,
        metrics: dict[str, dict[str, Any]],
    ) -> None:
        import json

        for metric in metrics.values():
            created_at = metric.get("created_at")
            updated_at = metric.get("updated_at") or created_at
            collected_at = metric.get("collected_at") or created_at
            cursor.execute(
                """
                INSERT INTO gitlab_daily_code_metrics (
                  id, product_id, repository_id, metric_date, commit_count,
                  active_author_count, merge_request_count, changed_files,
                  additions, deletions, quality_score, risk_count,
                  author_metrics, status, source_channel, collected_at,
                  created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s::date, %s,
                  %s, %s, %s, %s, %s, %s, %s,
                  %s::jsonb, %s, %s,
                  COALESCE(%s::timestamptz, now()),
                  %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  repository_id = EXCLUDED.repository_id,
                  metric_date = EXCLUDED.metric_date,
                  commit_count = EXCLUDED.commit_count,
                  active_author_count = EXCLUDED.active_author_count,
                  merge_request_count = EXCLUDED.merge_request_count,
                  changed_files = EXCLUDED.changed_files,
                  additions = EXCLUDED.additions,
                  deletions = EXCLUDED.deletions,
                  quality_score = EXCLUDED.quality_score,
                  risk_count = EXCLUDED.risk_count,
                  author_metrics = EXCLUDED.author_metrics,
                  status = EXCLUDED.status,
                  source_channel = EXCLUDED.source_channel,
                  collected_at = EXCLUDED.collected_at,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    metric["id"],
                    metric["product_id"],
                    metric["repository_id"],
                    metric["metric_date"],
                    metric.get("commit_count", 0),
                    metric.get("active_author_count", 0),
                    metric.get("merge_request_count", 0),
                    metric.get("changed_files", 0),
                    metric.get("additions", 0),
                    metric.get("deletions", 0),
                    metric.get("quality_score"),
                    metric.get("risk_count", 0),
                    json.dumps(metric.get("author_metrics", []), ensure_ascii=False),
                    metric.get("status", "collected"),
                    metric.get("source_channel"),
                    collected_at,
                    metric["created_by"],
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_jenkins_release_records(
        self,
        cursor,
        releases: dict[str, dict[str, Any]],
    ) -> None:
        for release in releases.values():
            created_at = release.get("created_at")
            updated_at = release.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO jenkins_release_records (
                  id, product_id, version_id, job_name, build_id, build_number,
                  environment, status, trigger_actor, commit_sha, duration_seconds,
                  started_at, deployed_at, failure_reason, source_channel,
                  created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s, %s,
                  %s::timestamptz, %s::timestamptz, %s, %s,
                  %s, COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  job_name = EXCLUDED.job_name,
                  build_id = EXCLUDED.build_id,
                  build_number = EXCLUDED.build_number,
                  environment = EXCLUDED.environment,
                  status = EXCLUDED.status,
                  trigger_actor = EXCLUDED.trigger_actor,
                  commit_sha = EXCLUDED.commit_sha,
                  duration_seconds = EXCLUDED.duration_seconds,
                  started_at = EXCLUDED.started_at,
                  deployed_at = EXCLUDED.deployed_at,
                  failure_reason = EXCLUDED.failure_reason,
                  source_channel = EXCLUDED.source_channel,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    release["id"],
                    release["product_id"],
                    release["version_id"],
                    release["job_name"],
                    release["build_id"],
                    release.get("build_number"),
                    release.get("environment", "prod"),
                    release.get("status", "success"),
                    release.get("trigger_actor"),
                    release.get("commit_sha"),
                    release.get("duration_seconds"),
                    release.get("started_at"),
                    release.get("deployed_at"),
                    release.get("failure_reason"),
                    release.get("source_channel"),
                    release["created_by"],
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_online_log_metrics(
        self,
        cursor,
        metrics: dict[str, dict[str, Any]],
    ) -> None:
        import json

        for metric in metrics.values():
            created_at = metric.get("created_at")
            updated_at = metric.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO online_log_metrics (
                  id, product_id, module_code, environment, window_start, window_end,
                  request_count, error_count, error_rate, p95_latency_ms,
                  p99_latency_ms, core_event_count, top_errors, anomaly_summary,
                  status, source_channel, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s::timestamptz, %s::timestamptz,
                  %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s,
                  %s, COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  module_code = EXCLUDED.module_code,
                  environment = EXCLUDED.environment,
                  window_start = EXCLUDED.window_start,
                  window_end = EXCLUDED.window_end,
                  request_count = EXCLUDED.request_count,
                  error_count = EXCLUDED.error_count,
                  error_rate = EXCLUDED.error_rate,
                  p95_latency_ms = EXCLUDED.p95_latency_ms,
                  p99_latency_ms = EXCLUDED.p99_latency_ms,
                  core_event_count = EXCLUDED.core_event_count,
                  top_errors = EXCLUDED.top_errors,
                  anomaly_summary = EXCLUDED.anomaly_summary,
                  status = EXCLUDED.status,
                  source_channel = EXCLUDED.source_channel,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    metric["id"],
                    metric["product_id"],
                    metric.get("module_code"),
                    metric.get("environment", "prod"),
                    metric["window_start"],
                    metric["window_end"],
                    metric.get("request_count", 0),
                    metric.get("error_count", 0),
                    metric.get("error_rate"),
                    metric.get("p95_latency_ms"),
                    metric.get("p99_latency_ms"),
                    metric.get("core_event_count", 0),
                    json.dumps(metric.get("top_errors", []), ensure_ascii=False),
                    metric.get("anomaly_summary"),
                    metric.get("status", "collected"),
                    metric.get("source_channel"),
                    metric["created_by"],
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_collector_runs(
        self,
        cursor,
        runs: dict[str, dict[str, Any]],
    ) -> None:
        import json

        for run in runs.values():
            created_at = run.get("created_at")
            updated_at = run.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO collector_runs (
                  id, collector_type, product_id, status, source_system,
                  started_at, finished_at, records_imported, error_message,
                  payload_summary, created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), %s::timestamptz,
                  %s, %s, %s::jsonb, %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  collector_type = EXCLUDED.collector_type,
                  product_id = EXCLUDED.product_id,
                  status = EXCLUDED.status,
                  source_system = EXCLUDED.source_system,
                  started_at = EXCLUDED.started_at,
                  finished_at = EXCLUDED.finished_at,
                  records_imported = EXCLUDED.records_imported,
                  error_message = EXCLUDED.error_message,
                  payload_summary = EXCLUDED.payload_summary,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    run["id"],
                    run["collector_type"],
                    run.get("product_id"),
                    run.get("status", "running"),
                    run["source_system"],
                    run.get("started_at"),
                    run.get("finished_at"),
                    run.get("records_imported", 0),
                    run.get("error_message"),
                    json.dumps(run.get("payload_summary", {}), ensure_ascii=False),
                    run.get("created_by"),
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_pending_attribution_items(
        self,
        cursor,
        items: dict[str, dict[str, Any]],
    ) -> None:
        import json

        for item in items.values():
            created_at = item.get("created_at")
            updated_at = item.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO pending_attribution_items (
                  id, source_type, source_system, collector_run_id, raw_subject_id,
                  summary, raw_payload, suggested_product_id, suggested_module_code,
                  confidence, status, resolution_action, resolution_note,
                  resolved_product_id, resolved_module_code, resolved_requirement_id,
                  resolved_subject_type, resolved_subject_id, resolved_by, resolved_at,
                  created_by, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s,
                  %s, %s::jsonb, %s, %s,
                  %s, %s, %s, %s,
                  %s, %s, %s,
                  %s, %s, %s, %s::timestamptz,
                  %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  source_type = EXCLUDED.source_type,
                  source_system = EXCLUDED.source_system,
                  collector_run_id = EXCLUDED.collector_run_id,
                  raw_subject_id = EXCLUDED.raw_subject_id,
                  summary = EXCLUDED.summary,
                  raw_payload = EXCLUDED.raw_payload,
                  suggested_product_id = EXCLUDED.suggested_product_id,
                  suggested_module_code = EXCLUDED.suggested_module_code,
                  confidence = EXCLUDED.confidence,
                  status = EXCLUDED.status,
                  resolution_action = EXCLUDED.resolution_action,
                  resolution_note = EXCLUDED.resolution_note,
                  resolved_product_id = EXCLUDED.resolved_product_id,
                  resolved_module_code = EXCLUDED.resolved_module_code,
                  resolved_requirement_id = EXCLUDED.resolved_requirement_id,
                  resolved_subject_type = EXCLUDED.resolved_subject_type,
                  resolved_subject_id = EXCLUDED.resolved_subject_id,
                  resolved_by = EXCLUDED.resolved_by,
                  resolved_at = EXCLUDED.resolved_at,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    item["id"],
                    item["source_type"],
                    item["source_system"],
                    item.get("collector_run_id"),
                    item.get("raw_subject_id"),
                    item["summary"],
                    json.dumps(item.get("raw_payload", {}), ensure_ascii=False),
                    item.get("suggested_product_id"),
                    item.get("suggested_module_code"),
                    item.get("confidence"),
                    item.get("status", "pending"),
                    item.get("resolution_action"),
                    item.get("resolution_note"),
                    item.get("resolved_product_id"),
                    item.get("resolved_module_code"),
                    item.get("resolved_requirement_id"),
                    item.get("resolved_subject_type"),
                    item.get("resolved_subject_id"),
                    item.get("resolved_by"),
                    item.get("resolved_at"),
                    item.get("created_by"),
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_iteration_plan_suggestions(
        self,
        cursor,
        suggestions: dict[str, dict[str, Any]],
    ) -> None:
        import json

        for suggestion in suggestions.values():
            created_at = suggestion.get("created_at")
            updated_at = suggestion.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO iteration_plan_suggestions (
                  id, product_id, planning_cycle, version_id, module_codes, title,
                  status, priority, priority_score, confidence_level,
                  recommendation_reason, business_value, risk_signals, dependencies,
                  estimated_effort, evidence, evidence_insufficient, created_by,
                  converted_requirement_id, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s,
                  %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  planning_cycle = EXCLUDED.planning_cycle,
                  version_id = EXCLUDED.version_id,
                  module_codes = EXCLUDED.module_codes,
                  title = EXCLUDED.title,
                  status = EXCLUDED.status,
                  priority = EXCLUDED.priority,
                  priority_score = EXCLUDED.priority_score,
                  confidence_level = EXCLUDED.confidence_level,
                  recommendation_reason = EXCLUDED.recommendation_reason,
                  business_value = EXCLUDED.business_value,
                  risk_signals = EXCLUDED.risk_signals,
                  dependencies = EXCLUDED.dependencies,
                  estimated_effort = EXCLUDED.estimated_effort,
                  evidence = EXCLUDED.evidence,
                  evidence_insufficient = EXCLUDED.evidence_insufficient,
                  created_by = EXCLUDED.created_by,
                  converted_requirement_id = EXCLUDED.converted_requirement_id,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    suggestion["id"],
                    suggestion["product_id"],
                    suggestion["planning_cycle"],
                    suggestion.get("version_id"),
                    json.dumps(suggestion.get("module_codes", []), ensure_ascii=False),
                    suggestion["title"],
                    suggestion.get("status", "suggested"),
                    suggestion.get("priority", "P2"),
                    suggestion.get("priority_score", 0),
                    suggestion.get("confidence_level", "low"),
                    suggestion["recommendation_reason"],
                    suggestion["business_value"],
                    json.dumps(suggestion.get("risk_signals", []), ensure_ascii=False),
                    json.dumps(suggestion.get("dependencies", []), ensure_ascii=False),
                    suggestion.get("estimated_effort", "medium"),
                    json.dumps(suggestion.get("evidence", []), ensure_ascii=False),
                    suggestion.get("evidence_insufficient", False),
                    suggestion["created_by"],
                    suggestion.get("converted_requirement_id"),
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_iteration_plan_decisions(
        self,
        cursor,
        decisions: dict[str, dict[str, Any]],
    ) -> None:
        for decision in decisions.values():
            created_at = decision.get("created_at") or decision.get("decided_at")
            updated_at = decision.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO iteration_plan_decisions (
                  id, suggestion_id, decision, comment, edited_title, edited_scope,
                  convert_to_requirement, created_requirement_id, decided_by, decided_at,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  suggestion_id = EXCLUDED.suggestion_id,
                  decision = EXCLUDED.decision,
                  comment = EXCLUDED.comment,
                  edited_title = EXCLUDED.edited_title,
                  edited_scope = EXCLUDED.edited_scope,
                  convert_to_requirement = EXCLUDED.convert_to_requirement,
                  created_requirement_id = EXCLUDED.created_requirement_id,
                  decided_by = EXCLUDED.decided_by,
                  decided_at = EXCLUDED.decided_at,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    decision["id"],
                    decision["suggestion_id"],
                    decision["decision"],
                    decision.get("comment"),
                    decision.get("edited_title"),
                    decision.get("edited_scope"),
                    decision.get("convert_to_requirement", False),
                    decision.get("created_requirement_id"),
                    decision["decided_by"],
                    decision.get("decided_at"),
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_lifecycle_context_edges(
        self,
        cursor,
        edges: dict[str, dict[str, Any]],
    ) -> None:
        import json

        for edge in edges.values():
            created_at = edge.get("created_at") or edge.get("observed_at")
            updated_at = edge.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO lifecycle_context_edges (
                  id, source_subject_type, source_subject_id, target_subject_type,
                  target_subject_id, relation_type, product_id, version_id,
                  module_code, confidence, source_module, observed_at, metadata,
                  summary, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), %s::jsonb, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  source_subject_type = EXCLUDED.source_subject_type,
                  source_subject_id = EXCLUDED.source_subject_id,
                  target_subject_type = EXCLUDED.target_subject_type,
                  target_subject_id = EXCLUDED.target_subject_id,
                  relation_type = EXCLUDED.relation_type,
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  module_code = EXCLUDED.module_code,
                  confidence = EXCLUDED.confidence,
                  source_module = EXCLUDED.source_module,
                  observed_at = EXCLUDED.observed_at,
                  metadata = EXCLUDED.metadata,
                  summary = EXCLUDED.summary,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    edge["id"],
                    edge["source_subject_type"],
                    edge["source_subject_id"],
                    edge["target_subject_type"],
                    edge["target_subject_id"],
                    edge["relation_type"],
                    edge.get("product_id"),
                    edge.get("version_id"),
                    edge.get("module_code"),
                    edge.get("confidence", 1.0),
                    edge.get("source_module", "lifecycle_context"),
                    edge.get("observed_at"),
                    json.dumps(edge.get("metadata", {}), ensure_ascii=False),
                    edge.get("summary"),
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_lifecycle_risk_signals(
        self,
        cursor,
        risks: dict[str, dict[str, Any]],
    ) -> None:
        for risk in risks.values():
            created_at = risk.get("created_at") or risk.get("observed_at")
            updated_at = risk.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO lifecycle_risk_signals (
                  id, product_id, version_id, module_code, requirement_id, task_id,
                  risk_type, severity, source_subject_type, source_subject_id,
                  impact_summary, recommendation, observed_at, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  module_code = EXCLUDED.module_code,
                  requirement_id = EXCLUDED.requirement_id,
                  task_id = EXCLUDED.task_id,
                  risk_type = EXCLUDED.risk_type,
                  severity = EXCLUDED.severity,
                  source_subject_type = EXCLUDED.source_subject_type,
                  source_subject_id = EXCLUDED.source_subject_id,
                  impact_summary = EXCLUDED.impact_summary,
                  recommendation = EXCLUDED.recommendation,
                  observed_at = EXCLUDED.observed_at,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    risk["id"],
                    risk.get("product_id"),
                    risk.get("version_id"),
                    risk.get("module_code"),
                    risk.get("requirement_id"),
                    risk.get("task_id"),
                    risk["risk_type"],
                    risk["severity"],
                    risk["source_subject_type"],
                    risk["source_subject_id"],
                    risk["impact_summary"],
                    risk["recommendation"],
                    risk.get("observed_at"),
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_dashboard_metric_snapshots(
        self,
        cursor,
        snapshots: dict[str, dict[str, Any]],
    ) -> None:
        import json

        for snapshot in snapshots.values():
            created_at = snapshot.get("created_at")
            updated_at = snapshot.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO dashboard_metric_snapshots (
                  id, product_id, time_range, window_start, window_end, metrics,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s::timestamptz, %s::timestamptz, %s::jsonb,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  product_id = EXCLUDED.product_id,
                  time_range = EXCLUDED.time_range,
                  window_start = EXCLUDED.window_start,
                  window_end = EXCLUDED.window_end,
                  metrics = EXCLUDED.metrics,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    snapshot["id"],
                    snapshot.get("product_id"),
                    snapshot.get("time_range", "all"),
                    snapshot.get("window_start"),
                    snapshot.get("window_end"),
                    json.dumps(snapshot.get("metrics", {}), ensure_ascii=False),
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_model_gateway_configs(
        self,
        cursor,
        configs: dict[str, dict[str, Any]],
    ) -> None:
        cursor.execute("UPDATE model_gateway_configs SET is_default = false")
        for config in configs.values():
            created_at = config.get("created_at")
            updated_at = config.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO model_gateway_configs (
                  id, name, provider, base_url, api_key_ref, default_chat_model,
                  default_embedding_model, embedding_connection_mode, embedding_base_url,
                  embedding_api_key_ref, embedding_dimension, timeout_seconds, max_retries, status,
                  is_default, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  name = EXCLUDED.name,
                  provider = EXCLUDED.provider,
                  base_url = EXCLUDED.base_url,
                  api_key_ref = EXCLUDED.api_key_ref,
                  default_chat_model = EXCLUDED.default_chat_model,
                  default_embedding_model = EXCLUDED.default_embedding_model,
                  embedding_connection_mode = EXCLUDED.embedding_connection_mode,
                  embedding_base_url = EXCLUDED.embedding_base_url,
                  embedding_api_key_ref = EXCLUDED.embedding_api_key_ref,
                  embedding_dimension = EXCLUDED.embedding_dimension,
                  timeout_seconds = EXCLUDED.timeout_seconds,
                  max_retries = EXCLUDED.max_retries,
                  status = EXCLUDED.status,
                  is_default = EXCLUDED.is_default,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    config["id"],
                    config["name"],
                    config.get("provider", "openai_compatible"),
                    config["base_url"],
                    config.get("api_key"),
                    config["default_chat_model"],
                    config.get("default_embedding_model"),
                    config.get("embedding_connection_mode", "reuse_chat"),
                    config.get("embedding_base_url"),
                    config.get("embedding_api_key"),
                    config.get("embedding_dimension"),
                    config.get("timeout_seconds", 60),
                    config.get("max_retries", 1),
                    config.get("status", "active"),
                    config.get("is_default", False),
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_model_gateway_logs(self, cursor, logs: list[dict[str, Any]]) -> None:
        import json

        for log in logs:
            created_at = log.get("created_at")
            updated_at = log.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO model_gateway_logs (
                  id, ai_task_id, provider, model, purpose, tokens, latency_ms,
                  status, error, model_gateway_config_id, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  ai_task_id = EXCLUDED.ai_task_id,
                  provider = EXCLUDED.provider,
                  model = EXCLUDED.model,
                  purpose = EXCLUDED.purpose,
                  tokens = EXCLUDED.tokens,
                  latency_ms = EXCLUDED.latency_ms,
                  status = EXCLUDED.status,
                  error = EXCLUDED.error,
                  model_gateway_config_id = EXCLUDED.model_gateway_config_id,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    log["id"],
                    log.get("ai_task_id"),
                    log["provider"],
                    log["model"],
                    log["purpose"],
                    json.dumps(log.get("tokens", {}), ensure_ascii=False),
                    log.get("latency_ms", 0),
                    log["status"],
                    log.get("error"),
                    log.get("model_gateway_config_id"),
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_assistant_conversations(
        self,
        cursor,
        conversations: dict[str, dict[str, Any]],
    ) -> None:
        for conversation in conversations.values():
            created_at = conversation.get("created_at")
            updated_at = conversation.get("updated_at") or conversation.get("last_message_at")
            updated_at = updated_at or created_at
            cursor.execute(
                """
                INSERT INTO assistant_conversations (
                  id, user_id, product_id, title, message_count, last_message_at,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s::timestamptz,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  user_id = EXCLUDED.user_id,
                  product_id = EXCLUDED.product_id,
                  title = EXCLUDED.title,
                  message_count = EXCLUDED.message_count,
                  last_message_at = EXCLUDED.last_message_at,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    conversation["id"],
                    conversation["user_id"],
                    conversation.get("product_id"),
                    conversation.get("title", "新对话"),
                    conversation.get("message_count", 0),
                    conversation.get("last_message_at"),
                    created_at,
                    updated_at,
                ),
            )

    def _upsert_assistant_messages(
        self,
        cursor,
        messages: dict[str, dict[str, Any]],
    ) -> None:
        import json

        for message in messages.values():
            created_at = message.get("created_at")
            updated_at = message.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO assistant_messages (
                  id, conversation_id, user_id, role, content, product_id, model,
                  suggestions, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s::jsonb,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  conversation_id = EXCLUDED.conversation_id,
                  user_id = EXCLUDED.user_id,
                  role = EXCLUDED.role,
                  content = EXCLUDED.content,
                  product_id = EXCLUDED.product_id,
                  model = EXCLUDED.model,
                  suggestions = EXCLUDED.suggestions,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    message["id"],
                    message["conversation_id"],
                    message["user_id"],
                    message["role"],
                    message["content"],
                    message.get("product_id"),
                    message.get("model"),
                    json.dumps(message.get("suggestions", []), ensure_ascii=False),
                    created_at,
                    updated_at,
                ),
            )

    def _mock_issue_rows(
        self,
        writebacks: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        rows = {}
        for fallback_key, writeback in writebacks.items():
            idempotency_key = writeback.get("idempotency_key") or fallback_key
            task_id = writeback.get("task_id")
            for issue in writeback.get("issues", []):
                issue_id = issue.get("id")
                source_task_id = issue.get("source_task_id") or task_id
                if not issue_id or not source_task_id:
                    continue
                rows[str(issue_id)] = {
                    "id": str(issue_id),
                    "idempotency_key": idempotency_key,
                    "payload": deepcopy(issue),
                    "source_task_id": source_task_id,
                    "status": issue.get("status", "open"),
                    "title": issue["title"],
                }
        return rows

    def _upsert_mock_issues(
        self,
        cursor,
        issues: dict[str, dict[str, Any]],
    ) -> None:
        import json

        for issue in issues.values():
            cursor.execute(
                """
                INSERT INTO mock_issues (
                  id, source_task_id, title, status, idempotency_key, payload,
                  created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s::jsonb, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  source_task_id = EXCLUDED.source_task_id,
                  title = EXCLUDED.title,
                  status = EXCLUDED.status,
                  idempotency_key = EXCLUDED.idempotency_key,
                  payload = EXCLUDED.payload,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    issue["id"],
                    issue["source_task_id"],
                    issue["title"],
                    issue.get("status", "open"),
                    issue["idempotency_key"],
                    json.dumps(issue.get("payload", {}), ensure_ascii=False),
                    issue.get("payload", {}).get("created_at"),
                    issue.get("payload", {}).get("updated_at")
                    or issue.get("payload", {}).get("created_at"),
                ),
            )

    def _upsert_gitlab_mr_snapshots(
        self,
        cursor,
        snapshots: dict[str, dict[str, Any]],
    ) -> None:
        import json

        for snapshot in snapshots.values():
            created_at = snapshot.get("created_at")
            updated_at = snapshot.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO gitlab_mr_snapshots (
                  id, repository_id, product_id, version_id, project_id, project_path,
                  mr_iid, title, author, source_branch, target_branch, base_sha, head_sha,
                  diff_refs, changed_files_summary, diff_storage_ref, diff_size_bytes,
                  diff_limit_bytes, snapshot_hash, requirement_id, technical_solution_task_id,
                  created_by, created_at, updated_at, writeback_allowed
                )
                VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s,
                  %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s, %s, %s,
                  COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now()),
                  %s
                )
                ON CONFLICT (id) DO UPDATE SET
                  repository_id = EXCLUDED.repository_id,
                  product_id = EXCLUDED.product_id,
                  version_id = EXCLUDED.version_id,
                  project_id = EXCLUDED.project_id,
                  project_path = EXCLUDED.project_path,
                  mr_iid = EXCLUDED.mr_iid,
                  title = EXCLUDED.title,
                  author = EXCLUDED.author,
                  source_branch = EXCLUDED.source_branch,
                  target_branch = EXCLUDED.target_branch,
                  base_sha = EXCLUDED.base_sha,
                  head_sha = EXCLUDED.head_sha,
                  diff_refs = EXCLUDED.diff_refs,
                  changed_files_summary = EXCLUDED.changed_files_summary,
                  diff_storage_ref = EXCLUDED.diff_storage_ref,
                  diff_size_bytes = EXCLUDED.diff_size_bytes,
                  diff_limit_bytes = EXCLUDED.diff_limit_bytes,
                  snapshot_hash = EXCLUDED.snapshot_hash,
                  requirement_id = EXCLUDED.requirement_id,
                  technical_solution_task_id = EXCLUDED.technical_solution_task_id,
                  created_by = EXCLUDED.created_by,
                  updated_at = EXCLUDED.updated_at,
                  writeback_allowed = EXCLUDED.writeback_allowed
                """,
                (
                    snapshot["id"],
                    snapshot["repository_id"],
                    snapshot["product_id"],
                    snapshot.get("version_id"),
                    snapshot.get("project_id"),
                    snapshot.get("project_path"),
                    snapshot["mr_iid"],
                    snapshot["title"],
                    json.dumps(snapshot.get("author"), ensure_ascii=False),
                    snapshot["source_branch"],
                    snapshot["target_branch"],
                    snapshot.get("base_sha"),
                    snapshot["head_sha"],
                    json.dumps(snapshot.get("diff_refs"), ensure_ascii=False),
                    json.dumps(snapshot.get("changed_files_summary", []), ensure_ascii=False),
                    snapshot["diff_storage_ref"],
                    snapshot.get("diff_size_bytes", 0),
                    snapshot.get("diff_limit_bytes", 0),
                    snapshot["snapshot_hash"],
                    snapshot["requirement_id"],
                    snapshot["technical_solution_task_id"],
                    snapshot["created_by"],
                    created_at,
                    updated_at,
                    snapshot.get("writeback_allowed", False),
                ),
            )

    def _upsert_code_review_reports(
        self,
        cursor,
        reports: dict[str, dict[str, Any]],
    ) -> None:
        import json

        for report in reports.values():
            created_at = report.get("created_at")
            updated_at = report.get("updated_at") or created_at
            cursor.execute(
                """
                INSERT INTO code_review_reports (
                  id, task_id, gitlab_mr_snapshot_id, executor, summary, risk_level,
                  findings, status, review_id, archived_at, error_code,
                  gitlab_writeback_performed, created_at, updated_at
                )
                VALUES (
                  %s, %s, %s, %s::jsonb, %s, %s, %s::jsonb, %s, %s,
                  %s::timestamptz, %s, %s, COALESCE(%s::timestamptz, now()),
                  COALESCE(%s::timestamptz, now())
                )
                ON CONFLICT (id) DO UPDATE SET
                  task_id = EXCLUDED.task_id,
                  gitlab_mr_snapshot_id = EXCLUDED.gitlab_mr_snapshot_id,
                  executor = EXCLUDED.executor,
                  summary = EXCLUDED.summary,
                  risk_level = EXCLUDED.risk_level,
                  findings = EXCLUDED.findings,
                  status = EXCLUDED.status,
                  review_id = EXCLUDED.review_id,
                  archived_at = EXCLUDED.archived_at,
                  error_code = EXCLUDED.error_code,
                  gitlab_writeback_performed = EXCLUDED.gitlab_writeback_performed,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    report["id"],
                    report["task_id"],
                    report["gitlab_mr_snapshot_id"],
                    json.dumps(report.get("executor", {}), ensure_ascii=False),
                    report["summary"],
                    report["risk_level"],
                    json.dumps(report.get("findings", []), ensure_ascii=False),
                    report.get("status", "draft"),
                    report.get("review_id"),
                    report.get("archived_at"),
                    report.get("error_code"),
                    report.get("gitlab_writeback_performed", False),
                    created_at,
                    updated_at,
                ),
            )
