from __future__ import annotations

from collections.abc import Callable
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
    "DeploymentRepository",
    "ExecutionGovernanceRepository",
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
    "RdCollaborationRepository",
    "SnapshotRepository",
    "UserFeedbackRepository",
    "UserUsageMetricRepository",
    "WorkflowRuntimeRepository",
]


class SnapshotRepository(Protocol):
    def load(self) -> dict[str, Any] | None: ...

    def save(self, payload: dict[str, Any]) -> None: ...


class RdCollaborationRepository(Protocol):
    """Persistence boundary for requirement-driven R&D collaboration state."""

    def get_rd_role_definition(self, record_id: str) -> dict[str, Any] | None: ...
    def list_rd_role_definitions(
        self, *, brain_app_id: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]: ...
    def get_rd_ai_employee(self, record_id: str) -> dict[str, Any] | None: ...
    def list_rd_ai_employees(
        self, *, brain_app_id: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]: ...
    def get_rd_executor_profile(self, record_id: str) -> dict[str, Any] | None: ...
    def list_rd_executor_profiles(
        self, *, brain_app_id: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]: ...
    def get_rd_task_executor_policy(self, record_id: str) -> dict[str, Any] | None: ...
    def list_rd_task_executor_policies(
        self,
        *,
        product_id: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
    ) -> list[dict[str, Any]]: ...
    def list_rd_collaboration_task_executor_policies(
        self,
        *,
        brain_app_id: str | None = None,
        product_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]: ...
    def get_rd_policy_role_binding(self, record_id: str) -> dict[str, Any] | None: ...
    def list_rd_policy_role_bindings(self, policy_id: str) -> list[dict[str, Any]]: ...
    def get_rd_policy_snapshot(self, record_id: str) -> dict[str, Any] | None: ...
    def get_rd_task_executor_policy_snapshot(self, record_id: str) -> dict[str, Any] | None: ...
    def list_rd_policy_snapshots(self, policy_id: str) -> list[dict[str, Any]]: ...
    def get_rd_policy_snapshot_source(self, record_id: str) -> dict[str, Any] | None: ...
    def list_rd_policy_snapshot_sources(self, snapshot_id: str) -> list[dict[str, Any]]: ...
    def get_requirement_assessment(self, record_id: str) -> dict[str, Any] | None: ...
    def list_requirement_assessments(self, requirement_id: str) -> list[dict[str, Any]]: ...
    def get_requirement_assessment_opinion(self, record_id: str) -> dict[str, Any] | None: ...
    def list_requirement_assessment_opinions(self, assessment_id: str) -> list[dict[str, Any]]: ...
    def get_requirement_assessment_execution(self, record_id: str) -> dict[str, Any] | None: ...
    def complete_ai_assessment_execution(
        self, *, execution_id: str, opinion: dict[str, Any]
    ) -> dict[str, Any]: ...
    def get_rd_collaboration_run(self, record_id: str) -> dict[str, Any] | None: ...
    def list_rd_collaboration_runs(
        self,
        *,
        product_version_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]: ...
    def get_rd_collaboration_run_requirement(self, record_id: str) -> dict[str, Any] | None: ...
    def list_rd_collaboration_run_requirements(
        self, collaboration_run_id: str
    ) -> list[dict[str, Any]]: ...
    def get_rd_scope_change_request(self, record_id: str) -> dict[str, Any] | None: ...
    def list_rd_scope_change_requests(
        self,
        *,
        product_version_id: str | None = None,
        source_run_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]: ...
    def list_rd_scope_change_request_operations(
        self, scope_change_request_id: str
    ) -> list[dict[str, Any]]: ...
    def get_rd_scope_change_request_operation(self, record_id: str) -> dict[str, Any] | None: ...
    def get_rd_run_seat(self, record_id: str) -> dict[str, Any] | None: ...
    def list_rd_run_seats(self, collaboration_run_id: str) -> list[dict[str, Any]]: ...
    def get_rd_role_session(self, record_id: str) -> dict[str, Any] | None: ...
    def list_rd_role_sessions(self, collaboration_run_id: str) -> list[dict[str, Any]]: ...
    def get_rd_work_item(self, record_id: str) -> dict[str, Any] | None: ...
    def list_rd_work_items(self, collaboration_run_id: str) -> list[dict[str, Any]]: ...
    def get_rd_work_item_dependency(self, record_id: str) -> dict[str, Any] | None: ...
    def list_rd_work_item_dependencies(self, collaboration_run_id: str) -> list[dict[str, Any]]: ...
    def get_rd_work_item_attempt(self, record_id: str) -> dict[str, Any] | None: ...
    def list_rd_work_item_attempts(self, work_item_id: str) -> list[dict[str, Any]]: ...
    def get_decision_request(self, record_id: str) -> dict[str, Any] | None: ...
    def list_decision_requests(
        self, *, subject_type: str, subject_id: str
    ) -> list[dict[str, Any]]: ...
    def get_rd_collaboration_event(self, record_id: str) -> dict[str, Any] | None: ...
    def list_rd_collaboration_events(self, collaboration_run_id: str) -> list[dict[str, Any]]: ...
    def get_rd_command_idempotency_record(self, record_id: str) -> dict[str, Any] | None: ...
    def get_valid_claim_replay_secret(self, command_record_id: str) -> dict[str, Any] | None: ...
    def get_role_feedback_record(self, record_id: str) -> dict[str, Any] | None: ...
    def list_role_feedback_records(self, collaboration_run_id: str) -> list[dict[str, Any]]: ...
    def get_rd_role_experience_record(self, record_id: str) -> dict[str, Any] | None: ...
    def list_rd_role_experience_records(self, experience_key: str) -> list[dict[str, Any]]: ...
    def list_rd_role_experience_sources(self, experience_id: str) -> list[dict[str, Any]]: ...
    def get_rd_role_experience_source(self, record_id: str) -> dict[str, Any] | None: ...

    def save_rd_role_definition_record(self, record: dict[str, Any]) -> dict[str, Any]: ...
    def save_rd_ai_employee_record(self, record: dict[str, Any]) -> dict[str, Any]: ...
    def save_rd_executor_profile_record(self, record: dict[str, Any]) -> dict[str, Any]: ...
    def save_rd_task_executor_policy_record(
        self,
        record: dict[str, Any],
        *,
        expected_policy_version: int | None = None,
        audit_event: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...
    def save_rd_policy_role_binding_record(self, record: dict[str, Any]) -> dict[str, Any]: ...
    def save_rd_task_executor_policy_role_binding_record(
        self, record: dict[str, Any]
    ) -> dict[str, Any]: ...
    def freeze_base_policy_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]: ...
    def derive_assessment_policy_snapshot(
        self, *, base_snapshot_id: str, snapshot: dict[str, Any]
    ) -> dict[str, Any]: ...
    def save_assessment_bundle(
        self,
        *,
        assessment: dict[str, Any],
        opinions: list[dict[str, Any]],
        snapshots: list[dict[str, Any]] | None = None,
        executions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]: ...
    def merge_version_policy_snapshot_with_sources(
        self, *, snapshot: dict[str, Any], sources: list[dict[str, Any]]
    ) -> dict[str, Any]: ...
    def create_collaboration_run_with_exact_scope(
        self,
        *,
        run: dict[str, Any],
        scope_rows: list[dict[str, Any]],
        snapshot: dict[str, Any] | None = None,
        sources: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]: ...
    def restart_terminal_collaboration_run(
        self,
        *,
        terminal_run_id: str,
        run: dict[str, Any],
        scope_rows: list[dict[str, Any]],
    ) -> dict[str, Any]: ...
    def assign_requirement_to_version_and_increment_scope(
        self,
        *,
        requirement_id: str,
        product_version_id: str,
        expected_scope_version: int,
    ) -> dict[str, Any]: ...
    def create_scope_change_request(
        self,
        *,
        request: dict[str, Any],
        operations: list[dict[str, Any]],
        decision_request: dict[str, Any],
    ) -> dict[str, Any]: ...
    def apply_scope_change_bundle(
        self,
        *,
        scope_change_request_id: str,
        decision: str,
        decided_by: str,
        expected_decision_version: int,
        cancellation_outbox_events: list[dict[str, Any]] | None = None,
        failure_injection: Callable[[str], None] | None = None,
    ) -> dict[str, Any]: ...
    def claim_ready_work_item(
        self,
        work_item_id: str,
        *,
        lease_owner: str,
        lease_seconds: int = 900,
        expected_version: int | None = None,
        attempt: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None: ...
    def save_rd_run_seat_record(self, record: dict[str, Any]) -> dict[str, Any]: ...
    def save_rd_role_session_record(self, record: dict[str, Any]) -> dict[str, Any]: ...
    def save_rd_work_item_record(self, record: dict[str, Any]) -> dict[str, Any]: ...
    def save_rd_work_item_dependency_record(self, record: dict[str, Any]) -> dict[str, Any]: ...
    def save_rd_collaboration_event_record(self, record: dict[str, Any]) -> dict[str, Any]: ...
    def save_decision_request_record(self, record: dict[str, Any]) -> dict[str, Any]: ...
    def save_work_item_attempt_bundle(
        self,
        *,
        work_item_id: str,
        expected_statuses: list[str],
        next_status: str,
        attempt: dict[str, Any],
        expected_version: int | None = None,
        event: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...
    def cancel_work_item_bundle(
        self,
        *,
        work_item_id: str,
        expected_version: int,
        high_risk: bool,
        decision_request: dict[str, Any] | None = None,
        event: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...
    def execute_idempotent_rd_command(
        self,
        *,
        command_type: str,
        aggregate_type: str,
        aggregate_id: str,
        idempotency_key: str,
        request_hash: str,
        operation: Callable[[Any], dict[str, Any]],
        command_record_id: str | None = None,
        failure_injection: Callable[[str], None] | None = None,
    ) -> dict[str, Any]: ...
    def save_and_scrub_claim_replay_secret(
        self, *, secret: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...
    def suspend_collaboration_run(
        self,
        *,
        collaboration_run_id: str,
        decision_request_id: str,
        expected_version: int,
    ) -> dict[str, Any]: ...
    def apply_decision_bundle(
        self,
        *,
        decision_request_id: str,
        selected_option_code: str,
        input_json: Any,
        comment: str | None,
        decided_by: str,
        expected_version: int,
    ) -> dict[str, Any]: ...
    def answer_decision_request(
        self,
        *,
        decision_request_id: str,
        expected_version: int,
        actor_id: str,
        actor_role_codes: list[str],
        actor_seat_ids: list[str],
        answer_json: Any,
        evidence_json: list[Any],
        options_json: list[dict[str, Any]],
        options_hash: str,
    ) -> dict[str, Any]: ...
    def expire_and_escalate_decision_request(
        self,
        *,
        decision_request_id: str,
        successor_request: dict[str, Any],
        expiry_event: dict[str, Any],
    ) -> dict[str, Any] | None: ...
    def save_role_feedback_once(self, record: dict[str, Any]) -> dict[str, Any]: ...
    def save_rd_role_experience_record(
        self,
        record: dict[str, Any],
        *,
        sources: list[dict[str, Any]],
    ) -> dict[str, Any]: ...
    def decide_role_experience(
        self,
        *,
        experience_id: str,
        decision: str,
        expected_review_version: int,
        reviewer_subject_type: str,
        reviewer_subject_id: str,
        reviewer_role_code: str | None,
        reviewer_seat_id: str | None,
        require_independent_reviewer: bool,
    ) -> dict[str, Any]: ...


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
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
    ) -> int: ...

    def list_product_summaries(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        owner_team: str | None = None,
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort_by: str = "display_order",
        sort_order: str = "asc",
    ) -> list[dict[str, Any]]: ...

    def get_product(self, product_id: str) -> dict[str, Any] | None: ...

    def get_product_version(self, version_id: str) -> dict[str, Any] | None: ...

    def get_product_git_repository(self, repository_id: str) -> dict[str, Any] | None: ...

    def get_product_module(self, module_id: str) -> dict[str, Any] | None: ...

    def product_module_has_related_records(self, product_id: str, module_code: str) -> bool: ...

    def product_version_has_related_records(self, version_id: str) -> bool: ...

    def get_related_system(self, system_id: str) -> dict[str, Any] | None: ...

    def get_related_system_by_code(self, code: str) -> dict[str, Any] | None: ...

    def get_product_version_branch_config(
        self,
        branch_config_id: str,
    ) -> dict[str, Any] | None: ...

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
        product_scope_ids: list[str] | None = None,
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
        product_scope_ids: list[str] | None = None,
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
        product_scope_ids: list[str] | None = None,
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

    def save_bug_and_ai_task_records(
        self,
        *,
        bug: dict[str, Any],
        task: dict[str, Any],
        audit_events: list[dict[str, Any]],
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

    def get_product_version_dashboard_source_rows(self, version_id: str) -> dict[str, Any]: ...

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

    def list_knowledge_spaces(self, *, active_only: bool = False) -> list[dict[str, Any]]: ...

    def list_knowledge_documents(
        self,
        *,
        user_roles: list[str],
        user_id: str | None = None,
        global_knowledge_access: bool = False,
        knowledge_space_scope_ids: list[str] | None = None,
        keyword: str | None = None,
        doc_type: str | None = None,
        folder_id: str | None = None,
        index_status: str | None = None,
        knowledge_space_id: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def count_knowledge_document_summaries(
        self,
        *,
        user_roles: list[str],
        user_id: str | None = None,
        global_knowledge_access: bool = False,
        knowledge_space_scope_ids: list[str] | None = None,
        keyword: str | None = None,
        doc_type: str | None = None,
        folder_id: str | None = None,
        index_status: str | None = None,
        knowledge_space_id: str | None = None,
        permission_role: str | None = None,
    ) -> int: ...

    def list_knowledge_document_summaries_page(
        self,
        *,
        user_roles: list[str],
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
        user_id: str | None = None,
        global_knowledge_access: bool = False,
        knowledge_space_scope_ids: list[str] | None = None,
        keyword: str | None = None,
        doc_type: str | None = None,
        folder_id: str | None = None,
        index_status: str | None = None,
        knowledge_space_id: str | None = None,
        permission_role: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def knowledge_index_health(
        self,
        *,
        user_roles: list[str],
        user_id: str | None = None,
        global_knowledge_access: bool = False,
        knowledge_space_scope_ids: list[str] | None = None,
        keyword: str | None = None,
        doc_type: str | None = None,
        folder_id: str | None = None,
        index_status: str | None = None,
        knowledge_space_id: str | None = None,
        permission_role: str | None = None,
        issue_limit: int = 10,
    ) -> dict[str, Any]: ...

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
        user_id: str | None = None,
        global_knowledge_access: bool = False,
        knowledge_space_id: str | None = None,
        knowledge_space_scope_ids: list[str] | None = None,
        product_id: str | None = None,
        query: str | None = None,
        version_id: str | None = None,
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


class DeploymentRepository(Protocol):
    def load_deployment_requests(self) -> dict[str, Any] | None: ...

    def list_deployment_schemes(
        self,
        *,
        deployment_method: str | None = None,
        environment: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        scheme_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def list_deployment_requests(
        self,
        *,
        environment: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
        version_id: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def page_deployment_requests(
        self,
        *,
        environment: str | None,
        page: int,
        page_size: int,
        product_id: str | None,
        product_scope_ids: list[str] | None,
        sort_by: str,
        sort_order: str,
        status: str | None,
        title: str | None,
        version_id: str | None,
    ) -> dict[str, Any]: ...

    def list_deployment_runs(
        self,
        *,
        deployment_request_id: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def claim_due_deployment_runs(
        self,
        *,
        lease_seconds: int,
        limit: int,
        worker_id: str,
    ) -> list[dict[str, Any]]: ...

    def save_deployment_scheme_record(
        self,
        record: dict[str, Any],
        *,
        audit_events: list[dict[str, Any]] | None = None,
        expected_version: int | None = None,
    ) -> None: ...

    def delete_deployment_scheme_record(
        self,
        scheme_id: str,
        *,
        audit_events: list[dict[str, Any]] | None = None,
    ) -> None: ...

    def save_deployment_request_record(
        self,
        record: dict[str, Any],
        *,
        audit_events: list[dict[str, Any]] | None = None,
    ) -> None: ...

    def save_deployment_run_record(
        self,
        record: dict[str, Any],
        *,
        audit_events: list[dict[str, Any]] | None = None,
    ) -> None: ...


class ExecutionGovernanceRepository(Protocol):
    def list_quality_gate_policies(
        self,
        *,
        phase: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
        task_type: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def get_quality_gate_policy(self, policy_id: str) -> dict[str, Any] | None: ...

    def list_execution_context_manifests(
        self,
        *,
        product_scope_ids: list[str] | None = None,
        subject_id: str | None = None,
        subject_type: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def list_quality_gate_runs(
        self,
        *,
        phase: str | None = None,
        product_scope_ids: list[str] | None = None,
        subject_id: str | None = None,
        subject_type: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def list_quality_gate_checks(
        self,
        quality_gate_run_id: str,
    ) -> list[dict[str, Any]]: ...

    def list_execution_attestations(
        self,
        *,
        subject_id: str | None = None,
        runner_task_id: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def list_trusted_delivery_records(
        self,
        *,
        product_scope_ids: list[str] | None = None,
        record_type: str,
    ) -> list[dict[str, Any]]: ...

    def list_agent_loop_runs(
        self,
        *,
        ai_task_id: str | None = None,
        product_scope_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]: ...

    def list_agent_loop_iterations(
        self,
        loop_run_id: str,
    ) -> list[dict[str, Any]]: ...

    def list_execution_resource_grants(
        self,
        *,
        environment: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        resource_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def claim_execution_outbox_events(
        self,
        *,
        lease_seconds: int,
        limit: int,
        worker_id: str,
    ) -> list[dict[str, Any]]: ...

    def list_execution_outbox_events(
        self,
        *,
        aggregate_id: str | None = None,
        aggregate_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def list_deployment_run_steps(
        self,
        *,
        deployment_run_id: str,
    ) -> list[dict[str, Any]]: ...

    def claim_external_event_inbox(
        self,
        *,
        lease_seconds: int,
        limit: int,
        worker_id: str,
    ) -> list[dict[str, Any]]: ...

    def list_external_event_inbox(
        self,
        *,
        delivery_id: str | None = None,
        provider: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def save_quality_gate_policy_record(
        self,
        record: dict[str, Any],
        *,
        audit_events: list[dict[str, Any]] | None = None,
        expected_version: int | None = None,
    ) -> None: ...

    def save_execution_context_manifest_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def save_execution_attestation_record(self, record: dict[str, Any]) -> None: ...

    def save_trusted_delivery_record(
        self,
        *,
        record: dict[str, Any],
        record_type: str,
    ) -> None: ...

    def save_execution_resource_grant_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
        expected_version: int | None = None,
    ) -> None: ...

    def save_external_event_inbox_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...

    def save_quality_gate_bundle_record(
        self,
        *,
        audit_events: list[dict[str, Any]] | None,
        checks: list[dict[str, Any]],
        run: dict[str, Any],
    ) -> None: ...

    def save_agent_loop_bundle_record(
        self,
        *,
        audit_events: list[dict[str, Any]] | None,
        iterations: list[dict[str, Any]],
        run: dict[str, Any],
    ) -> None: ...

    def save_deployment_dispatch_result_transaction(
        self,
        *,
        audit_events: list[dict[str, Any]],
        outbox_event: dict[str, Any],
        run: dict[str, Any],
    ) -> None: ...

    def save_execution_outbox_event_record(
        self,
        event: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...

    def save_deployment_run_steps_records(
        self,
        steps: list[dict[str, Any]],
        *,
        audit_events: list[dict[str, Any]] | None = None,
    ) -> None: ...

    def create_deployment_dispatch_transaction(
        self,
        *,
        audit_events: list[dict[str, Any]],
        deployment: dict[str, Any],
        outbox_event: dict[str, Any],
        requirements: list[dict[str, Any]],
        run: dict[str, Any],
        steps: list[dict[str, Any]],
    ) -> None: ...

    def save_deployment_dispatch_failure_transaction(
        self,
        *,
        audit_events: list[dict[str, Any]],
        deployment: dict[str, Any],
        outbox_event: dict[str, Any],
        requirements: list[dict[str, Any]],
        run: dict[str, Any],
        steps: list[dict[str, Any]],
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
        exclude_category: str | None = None,
        name: str | None = None,
        product_scope_ids: list[str] | None = None,
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
        limit: int | None = None,
        offset: int | None = None,
        summary_only: bool = False,
    ) -> list[dict[str, Any]]: ...

    def count_user_feedback(
        self,
        *,
        product_id: str | None = None,
        module_code: str | None = None,
        feature_code: str | None = None,
        status: str | None = None,
        created_by: str | None = None,
    ) -> int: ...

    def get_user_feedback(self, feedback_id: str) -> dict[str, Any] | None: ...

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
        product_id: str | None = None,
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

    def count_model_gateway_configs(
        self,
        *,
        default_chat_model: str | None = None,
        default_embedding_model: str | None = None,
        embedding_connection_mode: str | None = None,
        is_default: bool | None = None,
        name: str | None = None,
        provider: str | None = None,
        status: str | None = None,
    ) -> int: ...

    def list_model_gateway_configs_page(
        self,
        *,
        default_chat_model: str | None = None,
        default_embedding_model: str | None = None,
        embedding_connection_mode: str | None = None,
        is_default: bool | None = None,
        limit: int,
        name: str | None = None,
        offset: int,
        provider: str | None = None,
        sort_by: str = "name",
        sort_order: str = "asc",
        status: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def get_model_gateway_config(self, config_id: str) -> dict[str, Any] | None: ...

    def list_model_gateway_logs(
        self,
        *,
        ai_task_id: str | None = None,
        purpose: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def count_model_gateway_logs(
        self,
        *,
        ai_task_id: str | None = None,
        purpose: str | None = None,
        status: str | None = None,
    ) -> int: ...

    def list_model_gateway_logs_page(
        self,
        *,
        ai_task_id: str | None = None,
        limit: int,
        offset: int,
        purpose: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        status: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def save_model_gateway(self, payload: dict[str, Any]) -> None: ...

    def save_model_gateway_records(
        self,
        payload: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...

    def upsert_model_gateway_config_record(
        self,
        config: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...

    def delete_model_gateway_config_record(
        self,
        config_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...


class AssistantChatRepository(Protocol):
    def load_assistant_chat(self) -> dict[str, Any] | None: ...

    def list_assistant_chat_runs(self, *, user_id: str) -> list[dict[str, Any]]: ...

    def list_execution_trace_assistant_chat_runs(self) -> list[dict[str, Any]]: ...

    def get_assistant_chat_run(self, *, run_id: str) -> dict[str, Any] | None: ...

    def list_assistant_conversations(
        self,
        *,
        cursor: str | None = None,
        limit: int | None = None,
        user_id: str,
    ) -> list[dict[str, Any]]: ...

    def find_reusable_assistant_conversation(
        self,
        *,
        command_signature: str,
        context_scope: str,
        user_id: str,
    ) -> dict[str, Any] | None: ...

    def list_assistant_conversation_messages(
        self,
        *,
        conversation_id: str,
        user_id: str,
    ) -> list[dict[str, Any]] | None: ...

    def delete_assistant_conversations(
        self,
        *,
        audit_event: dict[str, Any] | None = None,
        conversation_ids: list[str],
        user_id: str,
    ) -> dict[str, Any]: ...

    def list_assistant_action_drafts(self, *, user_id: str) -> list[dict[str, Any]]: ...

    def list_assistant_action_draft_workbench_page(
        self,
        *,
        action: str | None,
        created_from: str | None,
        created_to: str | None,
        keyword: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
        status: str | None,
        user_id: str,
        validation_status: str | None,
    ) -> dict[str, Any]: ...

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

    def list_assistant_action_reference_configs(self) -> list[dict[str, Any]]: ...

    def get_assistant_action_reference_config(
        self,
        *,
        config_id: str,
    ) -> dict[str, Any] | None: ...

    def save_assistant_action_reference_config_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None: ...

    def delete_assistant_action_reference_config_record(
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
