from __future__ import annotations

from typing import Any


class RepositoryCallbackHub:
    def __init__(self, table_maintenance_repository: Any) -> None:
        self._table_maintenance_repository = table_maintenance_repository
        self._assistant_chat_read_repository: Any | None = None
        self._audit_read_repository: Any | None = None
        self._bug_read_repository: Any | None = None
        self._devops_read_repository: Any | None = None
        self._git_review_read_repository: Any | None = None
        self._knowledge_read_repository: Any | None = None
        self._lifecycle_dashboard_read_repository: Any | None = None
        self._mock_writeback_read_repository: Any | None = None
        self._model_gateway_read_repository: Any | None = None
        self._operational_collection_read_repository: Any | None = None
        self._user_insight_read_repository: Any | None = None

    def bind(
        self,
        *,
        assistant_chat_read_repository: Any,
        audit_read_repository: Any,
        bug_read_repository: Any,
        devops_read_repository: Any,
        git_review_read_repository: Any,
        knowledge_read_repository: Any,
        lifecycle_dashboard_read_repository: Any,
        mock_writeback_read_repository: Any,
        model_gateway_read_repository: Any,
        operational_collection_read_repository: Any,
        user_insight_read_repository: Any,
    ) -> None:
        self._assistant_chat_read_repository = assistant_chat_read_repository
        self._audit_read_repository = audit_read_repository
        self._bug_read_repository = bug_read_repository
        self._devops_read_repository = devops_read_repository
        self._git_review_read_repository = git_review_read_repository
        self._knowledge_read_repository = knowledge_read_repository
        self._lifecycle_dashboard_read_repository = lifecycle_dashboard_read_repository
        self._mock_writeback_read_repository = mock_writeback_read_repository
        self._model_gateway_read_repository = model_gateway_read_repository
        self._operational_collection_read_repository = operational_collection_read_repository
        self._user_insight_read_repository = user_insight_read_repository

    def delete_missing(
        self,
        cursor,
        table_name: str,
        items: dict[str, dict[str, Any]],
    ) -> None:
        self._table_maintenance_repository.delete_missing(cursor, table_name, items)

    def delete_missing_ids(self, cursor, table_name: str, item_ids: list[str]) -> None:
        self._table_maintenance_repository.delete_missing_ids(cursor, table_name, item_ids)

    def clean_knowledge_deposit_references(
        self,
        documents: dict[str, dict[str, Any]],
        deposits: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        return self._knowledge_read_repository.clean_knowledge_deposit_references(
            documents,
            deposits,
        )

    def clean_knowledge_chunk_references(
        self,
        documents: dict[str, dict[str, Any]],
        chunks: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        return self._knowledge_read_repository.clean_knowledge_chunk_references(
            documents,
            chunks,
        )

    def clear_dangling_knowledge_chunk_documents(
        self,
        cursor,
        documents: dict[str, dict[str, Any]],
    ) -> None:
        self._knowledge_read_repository.clear_dangling_knowledge_chunk_documents(
            cursor,
            documents,
        )

    def clear_dangling_knowledge_deposit_documents(
        self,
        cursor,
        documents: dict[str, dict[str, Any]],
    ) -> None:
        self._knowledge_read_repository.clear_dangling_knowledge_deposit_documents(
            cursor,
            documents,
        )

    def upsert_knowledge_documents(
        self,
        cursor,
        documents: dict[str, dict[str, Any]],
    ) -> None:
        self._knowledge_read_repository.upsert_knowledge_documents(cursor, documents)

    def upsert_knowledge_chunks(
        self,
        cursor,
        chunks: dict[str, dict[str, Any]],
    ) -> None:
        self._knowledge_read_repository.upsert_knowledge_chunks(cursor, chunks)

    def upsert_knowledge_deposits(
        self,
        cursor,
        deposits: dict[str, dict[str, Any]],
    ) -> None:
        self._knowledge_read_repository.upsert_knowledge_deposits(cursor, deposits)

    def upsert_audit_events(self, cursor, audit_events: list[dict[str, Any]]) -> None:
        self._audit_read_repository.upsert_audit_events(cursor, audit_events)

    def clean_bug_references(
        self,
        bugs: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        return self._bug_read_repository.clean_bug_references(bugs)

    def clear_dangling_bug_duplicates(
        self,
        cursor,
        bugs: dict[str, dict[str, Any]],
    ) -> None:
        self._bug_read_repository.clear_dangling_bug_duplicates(cursor, bugs)

    def upsert_bugs(self, cursor, bugs: dict[str, dict[str, Any]]) -> None:
        self._bug_read_repository.upsert_bugs(cursor, bugs)

    def upsert_user_feedback(
        self,
        cursor,
        feedback_items: dict[str, dict[str, Any]],
    ) -> None:
        self._user_insight_read_repository.upsert_user_feedback(cursor, feedback_items)

    def upsert_user_usage_metrics(
        self,
        cursor,
        metrics: dict[str, dict[str, Any]],
    ) -> None:
        self._user_insight_read_repository.upsert_user_usage_metrics(cursor, metrics)

    def upsert_gitlab_daily_code_metrics(
        self,
        cursor,
        metrics: dict[str, dict[str, Any]],
    ) -> None:
        self._devops_read_repository.upsert_gitlab_daily_code_metrics(cursor, metrics)

    def upsert_jenkins_release_records(
        self,
        cursor,
        releases: dict[str, dict[str, Any]],
    ) -> None:
        self._devops_read_repository.upsert_jenkins_release_records(cursor, releases)

    def upsert_online_log_metrics(
        self,
        cursor,
        metrics: dict[str, dict[str, Any]],
    ) -> None:
        self._devops_read_repository.upsert_online_log_metrics(cursor, metrics)

    def upsert_collector_runs(
        self,
        cursor,
        runs: dict[str, dict[str, Any]],
    ) -> None:
        self._operational_collection_read_repository.upsert_collector_runs(cursor, runs)

    def upsert_pending_attribution_items(
        self,
        cursor,
        items: dict[str, dict[str, Any]],
    ) -> None:
        self._operational_collection_read_repository.upsert_pending_attribution_items(
            cursor,
            items,
        )

    def upsert_iteration_plan_suggestions(
        self,
        cursor,
        suggestions: dict[str, dict[str, Any]],
    ) -> None:
        self._user_insight_read_repository.upsert_iteration_plan_suggestions(
            cursor,
            suggestions,
        )

    def upsert_iteration_plan_decisions(
        self,
        cursor,
        decisions: dict[str, dict[str, Any]],
    ) -> None:
        self._user_insight_read_repository.upsert_iteration_plan_decisions(cursor, decisions)

    def upsert_lifecycle_context_edges(
        self,
        cursor,
        edges: dict[str, dict[str, Any]],
    ) -> None:
        self._lifecycle_dashboard_read_repository.upsert_lifecycle_context_edges(cursor, edges)

    def upsert_lifecycle_risk_signals(
        self,
        cursor,
        risks: dict[str, dict[str, Any]],
    ) -> None:
        self._lifecycle_dashboard_read_repository.upsert_lifecycle_risk_signals(
            cursor,
            risks,
        )

    def upsert_dashboard_metric_snapshots(
        self,
        cursor,
        snapshots: dict[str, dict[str, Any]],
    ) -> None:
        self._lifecycle_dashboard_read_repository.upsert_dashboard_metric_snapshots(
            cursor,
            snapshots,
        )

    def upsert_model_gateway_logs(self, cursor, logs: list[dict[str, Any]]) -> None:
        self._model_gateway_read_repository.upsert_model_gateway_logs(cursor, logs)

    def upsert_assistant_conversations(
        self,
        cursor,
        conversations: dict[str, dict[str, Any]],
    ) -> None:
        self._assistant_chat_read_repository.upsert_assistant_conversations(
            cursor,
            conversations,
        )

    def upsert_assistant_messages(
        self,
        cursor,
        messages: dict[str, dict[str, Any]],
    ) -> None:
        self._assistant_chat_read_repository.upsert_assistant_messages(cursor, messages)

    def upsert_assistant_chat_runs(
        self,
        cursor,
        runs: dict[str, dict[str, Any]],
    ) -> None:
        self._assistant_chat_read_repository.upsert_assistant_chat_runs(cursor, runs)

    def upsert_assistant_action_drafts(
        self,
        cursor,
        drafts: dict[str, dict[str, Any]],
    ) -> None:
        self._assistant_chat_read_repository.upsert_assistant_action_drafts(cursor, drafts)

    def upsert_assistant_action_runs(
        self,
        cursor,
        runs: dict[str, dict[str, Any]],
    ) -> None:
        self._assistant_chat_read_repository.upsert_assistant_action_runs(cursor, runs)

    def mock_issue_rows(
        self,
        writebacks: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        return self._mock_writeback_read_repository.mock_issue_rows(writebacks)

    def upsert_mock_issues(
        self,
        cursor,
        issues: dict[str, dict[str, Any]],
    ) -> None:
        self._mock_writeback_read_repository.upsert_mock_issues(cursor, issues)

    def upsert_gitlab_mr_snapshots(
        self,
        cursor,
        snapshots: dict[str, dict[str, Any]],
    ) -> None:
        self._git_review_read_repository.upsert_gitlab_mr_snapshots(cursor, snapshots)

    def upsert_code_review_reports(
        self,
        cursor,
        reports: dict[str, dict[str, Any]],
    ) -> None:
        self._git_review_read_repository.upsert_code_review_reports(cursor, reports)
