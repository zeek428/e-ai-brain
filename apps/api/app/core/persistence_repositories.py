from __future__ import annotations

from typing import Any

from app.core.repositories.assistant_chat import AssistantChatReadRepository
from app.core.repositories.audit import AuditReadRepository
from app.core.repositories.brain_apps import BrainAppReadRepository
from app.core.repositories.bugs import BugReadRepository
from app.core.repositories.devops import DevopsReadRepository
from app.core.repositories.git_review import GitReviewReadRepository
from app.core.repositories.knowledge import KnowledgeReadRepository
from app.core.repositories.lifecycle_dashboard import LifecycleDashboardReadRepository
from app.core.repositories.mock_writeback import MockWritebackReadRepository
from app.core.repositories.model_gateway import ModelGatewayReadRepository
from app.core.repositories.operational_collection import OperationalCollectionReadRepository
from app.core.repositories.product_config import ProductConfigReadRepository
from app.core.repositories.requirements import RequirementReadRepository
from app.core.repositories.scheduled_ai_jobs import ScheduledAiJobReadRepository
from app.core.repositories.system_state import SystemStateRepository
from app.core.repositories.table_maintenance import TableMaintenanceRepository
from app.core.repositories.tasks import TaskReadRepository
from app.core.repositories.user_insights import UserInsightReadRepository
from app.core.repository_callbacks import RepositoryCallbackHub


def install_snapshot_repositories(repository: Any) -> None:
    repository._system_state_repository = SystemStateRepository(repository._connect)
    repository._table_maintenance_repository = TableMaintenanceRepository()
    repository._repository_callbacks = RepositoryCallbackHub(
        repository._table_maintenance_repository,
    )
    callbacks = repository._repository_callbacks

    repository._brain_app_read_repository = BrainAppReadRepository(repository._connect)
    repository._product_config_read_repository = ProductConfigReadRepository(
        repository._connect,
        delete_missing=callbacks.delete_missing,
        upsert_audit_events=callbacks.upsert_audit_events,
    )
    repository._requirement_read_repository = RequirementReadRepository(
        repository._connect,
        delete_missing=callbacks.delete_missing,
        upsert_audit_events=callbacks.upsert_audit_events,
    )
    repository._audit_read_repository = AuditReadRepository(
        repository._connect,
        delete_missing_ids=callbacks.delete_missing_ids,
    )
    repository._bug_read_repository = BugReadRepository(
        repository._connect,
        delete_missing=callbacks.delete_missing,
        upsert_audit_events=callbacks.upsert_audit_events,
    )
    repository._user_insight_read_repository = UserInsightReadRepository(
        repository._connect,
        delete_missing=callbacks.delete_missing,
        upsert_audit_events=callbacks.upsert_audit_events,
        upsert_requirements=repository._requirement_read_repository.upsert_requirements,
    )
    repository._devops_read_repository = DevopsReadRepository(
        repository._connect,
        delete_missing=callbacks.delete_missing,
        upsert_audit_events=callbacks.upsert_audit_events,
    )
    repository._git_review_read_repository = GitReviewReadRepository(
        repository._connect,
        delete_missing=callbacks.delete_missing,
        upsert_audit_events=callbacks.upsert_audit_events,
    )
    repository._knowledge_read_repository = KnowledgeReadRepository(
        repository._connect,
        delete_missing=callbacks.delete_missing,
        upsert_audit_events=callbacks.upsert_audit_events,
        upsert_model_gateway_logs=callbacks.upsert_model_gateway_logs,
    )
    repository._task_read_repository = TaskReadRepository(
        repository._connect,
        delete_missing=callbacks.delete_missing,
        upsert_requirements=repository._requirement_read_repository.upsert_requirements,
        upsert_audit_events=callbacks.upsert_audit_events,
        upsert_model_gateway_logs=callbacks.upsert_model_gateway_logs,
        upsert_code_review_reports=(
            repository._git_review_read_repository.upsert_code_review_reports
        ),
        upsert_bugs=repository._bug_read_repository.upsert_bugs,
        upsert_knowledge_deposits=repository._knowledge_read_repository.upsert_knowledge_deposits,
    )
    repository._model_gateway_read_repository = ModelGatewayReadRepository(
        repository._connect,
        delete_missing=callbacks.delete_missing,
        delete_missing_ids=callbacks.delete_missing_ids,
        upsert_audit_events=callbacks.upsert_audit_events,
    )
    repository._mock_writeback_read_repository = MockWritebackReadRepository(
        repository._connect,
        delete_missing=callbacks.delete_missing,
        upsert_audit_events=callbacks.upsert_audit_events,
    )
    repository._operational_collection_read_repository = OperationalCollectionReadRepository(
        repository._connect,
        delete_missing=callbacks.delete_missing,
        upsert_audit_events=callbacks.upsert_audit_events,
    )
    repository._scheduled_ai_job_read_repository = ScheduledAiJobReadRepository(
        repository._connect,
        upsert_audit_events=callbacks.upsert_audit_events,
    )
    repository._assistant_chat_read_repository = AssistantChatReadRepository(
        repository._connect,
        delete_missing=callbacks.delete_missing,
        upsert_audit_events=callbacks.upsert_audit_events,
        upsert_model_gateway_logs=callbacks.upsert_model_gateway_logs,
    )
    repository._lifecycle_dashboard_read_repository = LifecycleDashboardReadRepository(
        repository._connect,
        list_ai_task_summaries=repository.list_ai_task_summaries,
        list_audit_events=repository.list_audit_events,
        list_bugs=repository.list_bugs,
        list_gitlab_daily_code_metrics=repository.list_gitlab_daily_code_metrics,
        list_iteration_plan_suggestions=repository.list_iteration_plan_suggestions,
        list_jenkins_release_records=repository.list_jenkins_release_records,
        list_online_log_metrics=repository.list_online_log_metrics,
        list_products=repository.list_products,
        list_requirement_summaries=repository.list_requirement_summaries,
        list_user_feedback=repository.list_user_feedback,
        list_user_usage_metrics=repository.list_user_usage_metrics,
        load_gitlab_review=repository.load_gitlab_review,
        load_knowledge=repository.load_knowledge,
        load_mock_writebacks=repository.load_mock_writebacks,
        load_product_config=repository.load_product_config,
        load_workflow_runtime=repository.load_workflow_runtime,
        delete_missing=callbacks.delete_missing,
    )
    callbacks.bind(
        assistant_chat_read_repository=repository._assistant_chat_read_repository,
        audit_read_repository=repository._audit_read_repository,
        bug_read_repository=repository._bug_read_repository,
        devops_read_repository=repository._devops_read_repository,
        git_review_read_repository=repository._git_review_read_repository,
        knowledge_read_repository=repository._knowledge_read_repository,
        lifecycle_dashboard_read_repository=repository._lifecycle_dashboard_read_repository,
        mock_writeback_read_repository=repository._mock_writeback_read_repository,
        model_gateway_read_repository=repository._model_gateway_read_repository,
        operational_collection_read_repository=repository._operational_collection_read_repository,
        user_insight_read_repository=repository._user_insight_read_repository,
    )
    install_callback_aliases(repository)


def install_callback_aliases(repository: Any) -> None:
    callbacks = repository._repository_callbacks
    repository._delete_missing = callbacks.delete_missing
    repository._delete_missing_ids = callbacks.delete_missing_ids
    repository._clean_knowledge_deposit_references = callbacks.clean_knowledge_deposit_references
    repository._clean_knowledge_chunk_references = callbacks.clean_knowledge_chunk_references
    repository._clear_dangling_knowledge_chunk_documents = (
        callbacks.clear_dangling_knowledge_chunk_documents
    )
    repository._clear_dangling_knowledge_deposit_documents = (
        callbacks.clear_dangling_knowledge_deposit_documents
    )
    repository._upsert_knowledge_documents = callbacks.upsert_knowledge_documents
    repository._upsert_knowledge_chunks = callbacks.upsert_knowledge_chunks
    repository._upsert_knowledge_deposits = callbacks.upsert_knowledge_deposits
    repository._upsert_audit_events = callbacks.upsert_audit_events
    repository._clean_bug_references = callbacks.clean_bug_references
    repository._clear_dangling_bug_duplicates = callbacks.clear_dangling_bug_duplicates
    repository._upsert_bugs = callbacks.upsert_bugs
    repository._upsert_user_feedback = callbacks.upsert_user_feedback
    repository._upsert_user_usage_metrics = callbacks.upsert_user_usage_metrics
    repository._upsert_gitlab_daily_code_metrics = callbacks.upsert_gitlab_daily_code_metrics
    repository._upsert_jenkins_release_records = callbacks.upsert_jenkins_release_records
    repository._upsert_online_log_metrics = callbacks.upsert_online_log_metrics
    repository._upsert_collector_runs = callbacks.upsert_collector_runs
    repository._upsert_pending_attribution_items = callbacks.upsert_pending_attribution_items
    repository._upsert_iteration_plan_suggestions = callbacks.upsert_iteration_plan_suggestions
    repository._upsert_iteration_plan_decisions = callbacks.upsert_iteration_plan_decisions
    repository._upsert_lifecycle_context_edges = callbacks.upsert_lifecycle_context_edges
    repository._upsert_lifecycle_risk_signals = callbacks.upsert_lifecycle_risk_signals
    repository._upsert_dashboard_metric_snapshots = callbacks.upsert_dashboard_metric_snapshots
    repository._upsert_model_gateway_logs = callbacks.upsert_model_gateway_logs
    repository._upsert_assistant_conversations = callbacks.upsert_assistant_conversations
    repository._upsert_assistant_messages = callbacks.upsert_assistant_messages
    repository._mock_issue_rows = callbacks.mock_issue_rows
    repository._upsert_mock_issues = callbacks.upsert_mock_issues
    repository._upsert_gitlab_mr_snapshots = callbacks.upsert_gitlab_mr_snapshots
    repository._upsert_code_review_reports = callbacks.upsert_code_review_reports
