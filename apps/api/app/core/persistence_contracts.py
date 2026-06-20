from __future__ import annotations

from typing import Any, Protocol

from app.core.persistence_fields import (
    AI_TASK_FIELDS,
    ASSISTANT_CHAT_FIELDS,
    AUDIT_FIELDS,
    BRAIN_APP_FIELDS,
    BUG_FIELDS,
    COLLECTION_FIELDS,
    COLLECTOR_RUN_FIELDS,
    DASHBOARD_FIELDS,
    GITLAB_DAILY_CODE_METRIC_FIELDS,
    GITLAB_REVIEW_FIELDS,
    ID_COUNTER_SOURCE_TABLES,
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
    STATE_KEY,
    USER_FEEDBACK_FIELDS,
    USER_USAGE_METRIC_FIELDS,
    WORKFLOW_RUNTIME_FIELDS,
)

__all__ = [
    "AI_TASK_FIELDS",
    "ASSISTANT_CHAT_FIELDS",
    "AUDIT_FIELDS",
    "BRAIN_APP_FIELDS",
    "BUG_FIELDS",
    "COLLECTION_FIELDS",
    "COLLECTOR_RUN_FIELDS",
    "DASHBOARD_FIELDS",
    "GITLAB_DAILY_CODE_METRIC_FIELDS",
    "GITLAB_REVIEW_FIELDS",
    "ID_COUNTER_SOURCE_TABLES",
    "ITERATION_PLANNING_FIELDS",
    "JENKINS_RELEASE_RECORD_FIELDS",
    "KNOWLEDGE_FIELDS",
    "LIFECYCLE_CONTEXT_FIELDS",
    "MOCK_WRITEBACK_FIELDS",
    "MODEL_GATEWAY_FIELDS",
    "ONLINE_LOG_METRIC_FIELDS",
    "PENDING_ATTRIBUTION_FIELDS",
    "PRODUCT_CONFIG_FIELDS",
    "REQUIREMENT_FIELDS",
    "STATE_KEY",
    "USER_FEEDBACK_FIELDS",
    "USER_USAGE_METRIC_FIELDS",
    "WORKFLOW_RUNTIME_FIELDS",
    "AiTaskRepository",
    "AssistantChatRepository",
    "AuditRepository",
    "BrainAppRepository",
    "BugRepository",
    "CollectorRunRepository",
    "DashboardRepository",
    "GitlabDailyCodeMetricRepository",
    "GitlabReviewRepository",
    "IterationPlanningRepository",
    "JenkinsReleaseRecordRepository",
    "KnowledgeRepository",
    "LifecycleContextRepository",
    "MockWritebackRepository",
    "ModelGatewayRepository",
    "OnlineLogMetricRepository",
    "OperationalMetricReadModelRepository",
    "PendingAttributionRepository",
    "ProductConfigRepository",
    "RequirementRepository",
    "SnapshotRepository",
    "UserFeedbackRepository",
    "UserUsageMetricRepository",
    "WorkflowRuntimeRepository",
]


class SnapshotRepository(Protocol):
    def load(self) -> dict[str, Any] | None: ...

    def save(self, payload: dict[str, Any]) -> None: ...


class ProductConfigRepository(Protocol):
    def load_product_config(self) -> dict[str, Any] | None: ...

    def save_product_config(self, payload: dict[str, Any]) -> None: ...

    def list_products(self, *, active_only: bool = False) -> list[dict[str, Any]]: ...

    def count_product_summaries(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        owner_team: str | None = None,
        status: str | None = None,
    ) -> int: ...

    def list_product_summaries(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        owner_team: str | None = None,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str = "display_order",
        sort_order: str = "asc",
    ) -> list[dict[str, Any]]: ...

    def get_product(self, product_id: str) -> dict[str, Any] | None: ...

    def list_product_versions(
        self,
        product_id: str,
        *,
        active_only: bool = False,
    ) -> list[dict[str, Any]]: ...

    def count_product_version_summaries(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        status: str | None = None,
    ) -> int: ...

    def list_product_version_summaries_page(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str = "code",
        sort_order: str = "asc",
    ) -> list[dict[str, Any]]: ...

    def list_product_modules(
        self,
        product_id: str,
        *,
        active_only: bool = False,
    ) -> list[dict[str, Any]]: ...

    def list_product_git_repositories(
        self,
        product_id: str,
        *,
        active_only: bool = False,
    ) -> list[dict[str, Any]]: ...

    def list_related_systems(
        self,
        *,
        active_only: bool = False,
        product_id: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def save_product_config_record(
        self,
        collection_name: str,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...

    def delete_product_config_record(
        self,
        collection_name: str,
        record_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...


class BrainAppRepository(Protocol):
    def load_brain_apps(self) -> dict[str, Any] | None: ...


class RequirementRepository(Protocol):
    def load_requirements(self) -> dict[str, Any] | None: ...

    def save_requirements(self, payload: dict[str, Any]) -> None: ...

    def save_requirement_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...

    def delete_requirement_record(
        self,
        record_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...


class AiTaskRepository(Protocol):
    def load_ai_tasks(self) -> dict[str, Any] | None: ...

    def save_ai_tasks(self, payload: dict[str, Any]) -> None: ...

    def save_requirement_and_ai_task_records(
        self,
        *,
        requirement: dict[str, Any],
        task: dict[str, Any],
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...

    def save_task_start_records(
        self,
        *,
        task: dict[str, Any],
        review: dict[str, Any],
        graph_run: dict[str, Any],
        checkpoint: dict[str, Any],
        audit_events: list[dict[str, Any]],
        model_log: dict[str, Any] | None = None,
        code_review_report: dict[str, Any] | None = None,
    ) -> None: ...

    def save_review_decision_records(
        self,
        *,
        task: dict[str, Any],
        review: dict[str, Any],
        graph_run: dict[str, Any] | None,
        checkpoint: dict[str, Any] | None,
        audit_events: list[dict[str, Any]],
        requirement: dict[str, Any] | None = None,
        knowledge_deposits: list[dict[str, Any]] | None = None,
        bugs: list[dict[str, Any]] | None = None,
        code_review_report: dict[str, Any] | None = None,
    ) -> None: ...

    def save_task_state_records(
        self,
        *,
        task: dict[str, Any],
        audit_events: list[dict[str, Any]],
        reviews: list[dict[str, Any]] | None = None,
        graph_run: dict[str, Any] | None = None,
        checkpoint: dict[str, Any] | None = None,
        model_log: dict[str, Any] | None = None,
    ) -> None: ...


class WorkflowRuntimeRepository(Protocol):
    def load_workflow_runtime(self) -> dict[str, Any] | None: ...

    def get_task_workflow_source_rows(self) -> dict[str, Any]: ...

    def count_requirement_summaries(
        self,
        *,
        priority: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        source: str | None = None,
        status: str | None = None,
        title: str | None = None,
        version: str | None = None,
        version_id: str | None = None,
    ) -> int: ...

    def list_requirement_summaries(
        self,
        *,
        priority: str | None = None,
        product: str | None = None,
        product_id: str | None = None,
        source: str | None = None,
        status: str | None = None,
        title: str | None = None,
        version: str | None = None,
        version_id: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[dict[str, Any]]: ...

    def save_workflow_runtime(self, payload: dict[str, Any]) -> None: ...


class KnowledgeRepository(Protocol):
    def load_knowledge(self) -> dict[str, Any] | None: ...

    def list_knowledge_documents(
        self,
        *,
        user_roles: list[str],
        keyword: str | None = None,
        doc_type: str | None = None,
        index_status: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def list_knowledge_deposits(
        self,
        *,
        status: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def get_knowledge_deposit(self, deposit_id: str) -> dict[str, Any] | None: ...

    def has_readable_vector_chunks(self, *, user_roles: list[str]) -> bool: ...

    def search_knowledge_chunks(
        self,
        *,
        user_roles: list[str],
        query: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def save_knowledge(self, payload: dict[str, Any]) -> None: ...

    def claim_knowledge_import_job(
        self,
        *,
        job_id: str,
        worker_id: str,
        lock_ttl_seconds: float,
    ) -> bool: ...

    def save_knowledge_document_records(
        self,
        *,
        document: dict[str, Any],
        chunks: list[dict[str, Any]],
        audit_event: dict[str, Any] | None = None,
        model_logs: list[dict[str, Any]] | None = None,
    ) -> None: ...

    def delete_knowledge_document_records(
        self,
        *,
        document_id: str,
        deposits: list[dict[str, Any]],
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...

    def save_knowledge_deposit_records(
        self,
        *,
        deposit: dict[str, Any],
        audit_event: dict[str, Any] | None = None,
        document: dict[str, Any] | None = None,
        chunks: list[dict[str, Any]] | None = None,
        model_logs: list[dict[str, Any]] | None = None,
    ) -> None: ...


class AuditRepository(Protocol):
    def load_audit_events(self) -> dict[str, Any] | None: ...

    def list_audit_events(
        self,
        *,
        ai_task_id: str | None = None,
        actor_id: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        event_type: str | None = None,
        created_from: Any | None = None,
        created_to: Any | None = None,
    ) -> list[dict[str, Any]]: ...

    def save_audit_events(self, payload: dict[str, Any]) -> None: ...

    def append_audit_event(self, audit_event: dict[str, Any]) -> None: ...


class BugRepository(Protocol):
    def load_bugs(self) -> dict[str, Any] | None: ...

    def list_bugs(
        self,
        *,
        product_id: str | None = None,
        version_id: str | None = None,
        status: str | None = None,
        severity: str | None = None,
        source: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def count_bug_summaries(
        self,
        *,
        module: str | None = None,
        product_id: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        status: str | None = None,
        title: str | None = None,
        version: str | None = None,
        version_id: str | None = None,
    ) -> int: ...

    def list_bug_summaries(
        self,
        *,
        module: str | None = None,
        product_id: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        status: str | None = None,
        title: str | None = None,
        version: str | None = None,
        version_id: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[dict[str, Any]]: ...

    def save_bugs(self, payload: dict[str, Any]) -> None: ...

    def save_bug_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...

    def delete_bug_record(
        self,
        record_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...


class GitlabDailyCodeMetricRepository(Protocol):
    def load_gitlab_daily_code_metrics(self) -> dict[str, Any] | None: ...

    def list_gitlab_daily_code_metrics(
        self,
        *,
        product_id: str | None = None,
        repository_id: str | None = None,
        metric_date: Any | None = None,
    ) -> list[dict[str, Any]]: ...

    def save_gitlab_daily_code_metrics(self, payload: dict[str, Any]) -> None: ...

    def save_gitlab_daily_code_metric_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...


class JenkinsReleaseRecordRepository(Protocol):
    def load_jenkins_release_records(self) -> dict[str, Any] | None: ...

    def list_jenkins_release_records(
        self,
        *,
        product_id: str | None = None,
        version_id: str | None = None,
        status: str | None = None,
        environment: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def save_jenkins_release_records(self, payload: dict[str, Any]) -> None: ...

    def save_jenkins_release_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...


class OnlineLogMetricRepository(Protocol):
    def load_online_log_metrics(self) -> dict[str, Any] | None: ...

    def list_online_log_metrics(
        self,
        *,
        product_id: str | None = None,
        module_code: str | None = None,
        environment: str | None = None,
        from_value: Any | None = None,
        to_value: Any | None = None,
    ) -> list[dict[str, Any]]: ...

    def save_online_log_metrics(self, payload: dict[str, Any]) -> None: ...

    def save_online_log_metric_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...


class OperationalMetricReadModelRepository(Protocol):
    def list_operational_metric_items(
        self,
        *,
        category: str | None = None,
        name: str | None = None,
        status: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        sort_by: str,
        sort_order: str,
    ) -> dict[str, Any]: ...


class UserUsageMetricRepository(Protocol):
    def load_user_usage_metrics(self) -> dict[str, Any] | None: ...

    def list_user_usage_metrics(
        self,
        *,
        product_id: str | None = None,
        module_code: str | None = None,
        feature_code: str | None = None,
        user_segment: str | None = None,
        from_value: Any | None = None,
        to_value: Any | None = None,
    ) -> list[dict[str, Any]]: ...

    def save_user_usage_metrics(self, payload: dict[str, Any]) -> None: ...

    def save_user_usage_metric_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...


class UserFeedbackRepository(Protocol):
    def load_user_feedback(self) -> dict[str, Any] | None: ...

    def list_user_feedback(
        self,
        *,
        product_id: str | None = None,
        module_code: str | None = None,
        feature_code: str | None = None,
        status: str | None = None,
        created_by: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def save_user_feedback(self, payload: dict[str, Any]) -> None: ...

    def save_user_feedback_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...

    def save_user_feedback_requirement_conversion(
        self,
        *,
        audit_events: list[dict[str, Any]],
        feedback: dict[str, Any],
        requirement: dict[str, Any],
    ) -> None: ...


class IterationPlanningRepository(Protocol):
    def load_iteration_planning(self) -> dict[str, Any] | None: ...

    def list_iteration_plan_suggestions(
        self,
        *,
        product_id: str | None = None,
        planning_cycle: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def save_iteration_planning(self, payload: dict[str, Any]) -> None: ...

    def save_iteration_suggestion_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...

    def save_iteration_decision_records(
        self,
        *,
        suggestion: dict[str, Any],
        decision: dict[str, Any],
        audit_events: list[dict[str, Any]],
        requirement: dict[str, Any] | None = None,
    ) -> None: ...

    def list_user_insight_items(
        self,
        *,
        category: str | None = None,
        summary: str | None = None,
        status: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        sort_by: str,
        sort_order: str,
    ) -> dict[str, Any]: ...


class LifecycleContextRepository(Protocol):
    def load_lifecycle_context(self) -> dict[str, Any] | None: ...

    def get_lifecycle_context_source_rows(
        self,
        *,
        product_id: str | None = None,
    ) -> dict[str, Any]: ...

    def save_lifecycle_context(self, payload: dict[str, Any]) -> None: ...


class DashboardRepository(Protocol):
    def load_dashboard_snapshots(self) -> dict[str, Any] | None: ...

    def get_dashboard_it_team_source_rows(
        self,
        *,
        user_roles: list[str],
        product_id: str | None = None,
    ) -> dict[str, Any]: ...

    def save_dashboard_snapshots(self, payload: dict[str, Any]) -> None: ...

    def save_dashboard_metric_snapshot_record(self, snapshot: dict[str, Any]) -> None: ...


class CollectorRunRepository(Protocol):
    def load_collector_runs(self) -> dict[str, Any] | None: ...

    def list_collector_runs(
        self,
        *,
        collector_type: str | None = None,
        product_id: str | None = None,
        status: str | None = None,
        source_system: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def save_collector_runs(self, payload: dict[str, Any]) -> None: ...

    def save_collector_run_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...


class PendingAttributionRepository(Protocol):
    def load_pending_attribution(self) -> dict[str, Any] | None: ...

    def list_pending_attribution_items(
        self,
        *,
        source_type: str | None = None,
        status: str | None = None,
        resolved_product_id: str | None = None,
        collector_run_id: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def save_pending_attribution(self, payload: dict[str, Any]) -> None: ...

    def save_pending_attribution_item_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...


class ModelGatewayRepository(Protocol):
    def load_model_gateway(self) -> dict[str, Any] | None: ...

    def list_model_gateway_configs(self) -> list[dict[str, Any]]: ...

    def list_model_gateway_logs(
        self,
        *,
        ai_task_id: str | None = None,
        purpose: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def save_model_gateway(self, payload: dict[str, Any]) -> None: ...

    def save_model_gateway_records(
        self,
        payload: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...


class AssistantChatRepository(Protocol):
    def load_assistant_chat(self) -> dict[str, Any] | None: ...

    def list_assistant_chat_runs(self, *, user_id: str) -> list[dict[str, Any]]: ...

    def get_assistant_chat_run(self, *, run_id: str) -> dict[str, Any] | None: ...

    def list_assistant_conversations(self, *, user_id: str) -> list[dict[str, Any]]: ...

    def list_assistant_conversation_messages(
        self,
        *,
        conversation_id: str,
        user_id: str,
    ) -> list[dict[str, Any]] | None: ...

    def list_assistant_action_drafts(self, *, user_id: str) -> list[dict[str, Any]]: ...

    def get_assistant_action_draft(self, *, draft_id: str) -> dict[str, Any] | None: ...

    def list_assistant_role_quick_tasks(self) -> list[dict[str, Any]]: ...

    def get_assistant_role_quick_task(
        self,
        *,
        config_id: str,
    ) -> dict[str, Any] | None: ...

    def save_assistant_role_quick_task_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...

    def delete_assistant_role_quick_task_record(
        self,
        config_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...

    def save_assistant_chat(self, payload: dict[str, Any]) -> None: ...

    def save_assistant_chat_records(
        self,
        *,
        chat_run: dict[str, Any] | None = None,
        conversation: dict[str, Any] | None,
        messages: list[dict[str, Any]],
        audit_events: list[dict[str, Any]],
        model_log: dict[str, Any] | None = None,
    ) -> None: ...

    def save_assistant_action_records(
        self,
        *,
        draft: dict[str, Any],
        audit_events: list[dict[str, Any]],
        run: dict[str, Any] | None = None,
    ) -> None: ...


class GitlabReviewRepository(Protocol):
    def load_gitlab_review(self) -> dict[str, Any] | None: ...

    def save_gitlab_review(self, payload: dict[str, Any]) -> None: ...

    def save_gitlab_review_snapshot_record(
        self,
        *,
        snapshot: dict[str, Any] | None,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...


class MockWritebackRepository(Protocol):
    def load_mock_writebacks(self) -> dict[str, Any] | None: ...

    def save_mock_writebacks(self, payload: dict[str, Any]) -> None: ...

    def save_mock_writeback_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...
