from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.core.persistence_contracts import SnapshotRepository
from app.core.persistence_fields import (
    AI_TASK_FIELDS,
    ASSISTANT_CHAT_FIELDS,
    BRAIN_APP_FIELDS,
    BUG_FIELDS,
    COLLECTION_FIELDS,
    COLLECTOR_RUN_FIELDS,
    DASHBOARD_FIELDS,
    GITLAB_DAILY_CODE_METRIC_FIELDS,
    GITLAB_REVIEW_FIELDS,
    ITERATION_PLANNING_FIELDS,
    JENKINS_RELEASE_RECORD_FIELDS,
    KNOWLEDGE_FIELDS,
    LIFECYCLE_CONTEXT_FIELDS,
    MOCK_WRITEBACK_FIELDS,
    MODEL_GATEWAY_FIELDS,
    ONLINE_LOG_METRIC_FIELDS,
    PENDING_ATTRIBUTION_FIELDS,
    PRODUCT_CONFIG_FIELDS,
    REQUIREMENT_FIELDS,
    USER_FEEDBACK_FIELDS,
    USER_USAGE_METRIC_FIELDS,
    WORKFLOW_RUNTIME_FIELDS,
)
from app.core.persistence_payloads import (
    _ai_tasks_merge_payload,
    _assistant_chat_payload,
    _audit_payload,
    _brain_apps_payload,
    _bugs_payload,
    _clean_pending_attribution_references,
    _collector_run_payload,
    _dashboard_payload,
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
    _gitlab_daily_code_metric_payload,
    _gitlab_review_payload,
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
    _repository_load_ai_tasks,
    _repository_load_assistant_chat,
    _repository_load_audit_events,
    _repository_load_brain_apps,
    _repository_load_bugs,
    _repository_load_collector_runs,
    _repository_load_dashboard_snapshots,
    _repository_load_gitlab_daily_code_metrics,
    _repository_load_gitlab_review,
    _repository_load_iteration_planning,
    _repository_load_jenkins_release_records,
    _repository_load_knowledge,
    _repository_load_lifecycle_context,
    _repository_load_mock_writebacks,
    _repository_load_model_gateway,
    _repository_load_online_log_metrics,
    _repository_load_pending_attribution,
    _repository_load_product_config,
    _repository_load_requirements,
    _repository_load_user_feedback,
    _repository_load_user_usage_metrics,
    _repository_load_workflow_runtime,
    _repository_save_ai_tasks,
    _repository_save_assistant_chat,
    _repository_save_audit_events,
    _repository_save_bugs,
    _repository_save_collector_runs,
    _repository_save_dashboard_snapshots,
    _repository_save_gitlab_daily_code_metrics,
    _repository_save_gitlab_review,
    _repository_save_iteration_planning,
    _repository_save_jenkins_release_records,
    _repository_save_knowledge,
    _repository_save_lifecycle_context,
    _repository_save_mock_writebacks,
    _repository_save_model_gateway,
    _repository_save_online_log_metrics,
    _repository_save_pending_attribution,
    _repository_save_product_config,
    _repository_save_requirements,
    _repository_save_user_feedback,
    _repository_save_user_usage_metrics,
    _repository_save_workflow_runtime,
    _requirements_payload,
    _sync_ai_task_counters,
    _sync_assistant_chat_counters,
    _sync_audit_counters,
    _sync_bug_counters,
    _sync_code_review_report_links,
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
    _sync_task_runtime_links,
    _sync_user_feedback_counters,
    _sync_user_usage_metric_counters,
    _sync_workflow_runtime_counters,
    _user_feedback_payload,
    _user_usage_metric_payload,
    _workflow_runtime_payload,
)
from app.core.store import MemoryStore


class PersistentMemoryStore(MemoryStore):
    def __init__(self, repository: SnapshotRepository) -> None:
        super().__init__()
        self.repository = repository

    @classmethod
    def from_repository(cls, repository: SnapshotRepository) -> PersistentMemoryStore:
        store = cls(repository)
        payload: dict[str, Any] = {}
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
