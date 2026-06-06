from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.core.persistence_contracts import (
    SnapshotRepository,
)
from app.core.persistence_payload_checks import (
    _has_ai_task_items,
    _has_assistant_chat_items,
    _has_audit_items,
    _has_brain_app_items,
    _has_bug_items,
    _has_collector_run_items,
    _has_dashboard_items,
    _has_gitlab_daily_code_metric_items,
    _has_gitlab_review_items,
    _has_iteration_planning_items,
    _has_jenkins_release_record_items,
    _has_knowledge_items,
    _has_lifecycle_context_items,
    _has_mock_writeback_items,
    _has_model_gateway_items,
    _has_online_log_metric_items,
    _has_pending_attribution_items,
    _has_product_config_items,
    _has_requirement_items,
    _has_user_feedback_items,
    _has_user_usage_metric_items,
    _has_workflow_runtime_items,
)
from app.core.persistence_payload_cleanup import (
    _clean_pending_attribution_references,
    _drop_ai_tasks_without_context,
    _drop_bugs_without_context,
    _drop_collector_runs_without_context,
    _drop_dashboard_snapshots_without_context,
    _drop_gitlab_daily_code_metrics_without_context,
    _drop_gitlab_review_without_context,
    _drop_iteration_planning_without_context,
    _drop_jenkins_release_records_without_context,
    _drop_knowledge_without_context,
    _drop_lifecycle_context_without_context,
    _drop_mock_writebacks_without_tasks,
    _drop_online_log_metrics_without_context,
    _drop_requirements_without_product_context,
    _drop_user_feedback_without_context,
    _drop_user_usage_metrics_without_context,
    _drop_workflow_runtime_without_tasks,
    _ensure_ai_task_defaults,
    _sync_code_review_report_links,
    _sync_task_runtime_links,
)
from app.core.persistence_payload_counters import (
    _sync_ai_task_counters,
    _sync_assistant_chat_counters,
    _sync_audit_counters,
    _sync_bug_counters,
    _sync_collector_run_counters,
    _sync_gitlab_daily_code_metric_counters,
    _sync_gitlab_review_counters,
    _sync_iteration_planning_counters,
    _sync_jenkins_release_record_counters,
    _sync_knowledge_counters,
    _sync_lifecycle_context_counters,
    _sync_mock_writeback_counters,
    _sync_model_gateway_counters,
    _sync_online_log_metric_counters,
    _sync_pending_attribution_counters,
    _sync_product_config_counters,
    _sync_requirement_counters,
    _sync_user_feedback_counters,
    _sync_user_usage_metric_counters,
    _sync_workflow_runtime_counters,
)
from app.core.persistence_payload_selectors import (
    _ai_tasks_merge_payload,
    _ai_tasks_payload,
    _assistant_chat_payload,
    _audit_payload,
    _brain_apps_payload,
    _bugs_payload,
    _collector_run_payload,
    _dashboard_payload,
    _gitlab_daily_code_metric_payload,
    _gitlab_review_payload,
    _iteration_planning_payload,
    _jenkins_release_record_payload,
    _knowledge_payload,
    _lifecycle_context_payload,
    _merge_audit_payload,
    _merge_collection_payload,
    _mock_writebacks_payload,
    _model_gateway_payload,
    _online_log_metric_payload,
    _pending_attribution_payload,
    _product_config_payload,
    _replace_collection_payload,
    _requirements_payload,
    _user_feedback_payload,
    _user_usage_metric_payload,
    _workflow_runtime_payload,
)

__all__ = [
    "_ai_tasks_merge_payload",
    "_brain_apps_payload",
    "_clean_pending_attribution_references",
    "_drop_ai_tasks_without_context",
    "_drop_bugs_without_context",
    "_drop_collector_runs_without_context",
    "_drop_dashboard_snapshots_without_context",
    "_drop_gitlab_daily_code_metrics_without_context",
    "_drop_gitlab_review_without_context",
    "_drop_iteration_planning_without_context",
    "_drop_jenkins_release_records_without_context",
    "_drop_knowledge_without_context",
    "_drop_lifecycle_context_without_context",
    "_drop_mock_writebacks_without_tasks",
    "_drop_online_log_metrics_without_context",
    "_drop_requirements_without_product_context",
    "_drop_user_feedback_without_context",
    "_drop_user_usage_metrics_without_context",
    "_drop_workflow_runtime_without_tasks",
    "_ensure_ai_task_defaults",
    "_has_ai_task_items",
    "_has_assistant_chat_items",
    "_has_audit_items",
    "_has_brain_app_items",
    "_has_bug_items",
    "_has_collector_run_items",
    "_has_dashboard_items",
    "_has_gitlab_daily_code_metric_items",
    "_has_gitlab_review_items",
    "_has_iteration_planning_items",
    "_has_jenkins_release_record_items",
    "_has_knowledge_items",
    "_has_lifecycle_context_items",
    "_has_mock_writeback_items",
    "_has_model_gateway_items",
    "_has_online_log_metric_items",
    "_has_pending_attribution_items",
    "_has_product_config_items",
    "_has_requirement_items",
    "_has_user_feedback_items",
    "_has_user_usage_metric_items",
    "_has_workflow_runtime_items",
    "_merge_audit_payload",
    "_merge_collection_payload",
    "_product_config_payload",
    "_replace_collection_payload",
    "_requirements_payload",
    "_sync_ai_task_counters",
    "_sync_assistant_chat_counters",
    "_sync_audit_counters",
    "_sync_bug_counters",
    "_sync_code_review_report_links",
    "_sync_collector_run_counters",
    "_sync_gitlab_daily_code_metric_counters",
    "_sync_gitlab_review_counters",
    "_sync_iteration_planning_counters",
    "_sync_jenkins_release_record_counters",
    "_sync_knowledge_counters",
    "_sync_lifecycle_context_counters",
    "_sync_mock_writeback_counters",
    "_sync_model_gateway_counters",
    "_sync_online_log_metric_counters",
    "_sync_pending_attribution_counters",
    "_sync_product_config_counters",
    "_sync_requirement_counters",
    "_sync_task_runtime_links",
    "_sync_user_feedback_counters",
    "_sync_user_usage_metric_counters",
    "_sync_workflow_runtime_counters",
]


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
