from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from app.services.dashboard_metrics import (
    build_dashboard_metrics_data,
    dashboard_metric_snapshot_record,
    dashboard_source_rows_from_store,
    sync_dashboard_metric_snapshot,
)


def test_dashboard_metrics_filter_product_time_range_and_task_permissions():
    cutoff = datetime(2026, 6, 1, tzinfo=UTC)
    rows = {
        "audit_events": [
            {
                "ai_task_id": "task_001",
                "id": "audit_001",
                "sequence": 3,
                "subject_id": "task_001",
                "subject_type": "ai_task",
            },
            {
                "ai_task_id": "task_hidden",
                "id": "audit_002",
                "sequence": 4,
                "subject_id": "task_hidden",
                "subject_type": "ai_task",
            },
        ],
        "bugs": [
            {
                "created_at": "2026-06-02T10:00:00+00:00",
                "id": "bug_001",
                "product_id": "product_001",
                "severity": "critical",
                "status": "open",
            },
            {
                "created_at": "2026-05-01T10:00:00+00:00",
                "id": "bug_old",
                "product_id": "product_001",
                "severity": "major",
                "status": "open",
            },
        ],
        "gitlab_daily_code_metrics": [
            {
                "commit_count": 3,
                "id": "gitlab_metric_001",
                "metric_date": "2026-06-03",
                "product_id": "product_001",
            }
        ],
        "human_reviews": [
            {"ai_task_id": "task_001", "id": "review_001", "status": "pending"}
        ],
        "iteration_plan_suggestions": [
            {
                "created_at": "2026-06-03T10:00:00+00:00",
                "id": "suggestion_001",
                "product_id": "product_001",
                "status": "open",
            }
        ],
        "jenkins_release_records": [],
        "knowledge_deposits": [],
        "knowledge_documents": [],
        "mock_writebacks": [],
        "online_log_metrics": [
            {
                "error_count": 1,
                "id": "online_metric_001",
                "product_id": "product_001",
                "request_count": 10,
                "window_end": "2026-06-03T10:00:00+00:00",
            }
        ],
        "products": [
            {"id": "product_001", "name": "Enterprise AI Brain", "status": "active"},
            {"id": "product_002", "name": "Other", "status": "active"},
        ],
        "requirements": [
            {
                "created_at": "2026-06-02T10:00:00+00:00",
                "id": "requirement_001",
                "product_id": "product_001",
                "status": "approved",
                "title": "A",
            },
            {
                "created_at": "2026-06-03T10:00:00+00:00",
                "id": "requirement_002",
                "product_id": "product_002",
                "status": "approved",
                "title": "B",
            },
        ],
        "tasks": [
            {
                "created_at": "2026-06-02T11:00:00+00:00",
                "id": "task_001",
                "product_id": "product_001",
                "status": "running",
            },
            {
                "created_at": "2026-06-03T11:00:00+00:00",
                "id": "task_done",
                "product_id": "product_001",
                "status": "completed",
                "updated_at": "2026-06-03T12:00:00+00:00",
            },
            {
                "created_at": "2026-06-03T11:00:00+00:00",
                "hidden": True,
                "id": "task_hidden",
                "product_id": "product_001",
                "status": "running",
            },
        ],
        "user_feedback": [
            {
                "created_at": "2026-06-03T10:00:00+00:00",
                "id": "feedback_001",
                "product_id": "product_001",
                "status": "open",
            }
        ],
        "user_usage_metrics": [
            {
                "active_users": 5,
                "event_count": 12,
                "id": "usage_001",
                "product_id": "product_001",
                "window_end": "2026-06-03T10:00:00+00:00",
            }
        ],
    }

    metrics = build_dashboard_metrics_data(
        rows,
        can_read_task=lambda _user, task: not task.get("hidden"),
        cutoff=cutoff,
        product_id="product_001",
        time_range="7d",
        user={"roles": ["admin"]},
    )

    assert metrics["summary"]["active_products"] == 1
    assert metrics["summary"]["requirements"] == 1
    assert metrics["summary"]["ai_tasks"] == 2
    assert metrics["summary"]["pending_reviews"] == 1
    assert metrics["summary"]["bugs"] == 1
    assert metrics["summary"]["high_severity_bugs"] == 1
    assert metrics["summary"]["gitlab_commits"] == 3
    assert metrics["online_log_summary"]["error_rate"] == 0.1
    assert [event["id"] for event in metrics["recent_audit_events"]] == [
        "audit_002",
        "audit_001",
    ]
    trend = {point["period"]: point for point in metrics["trend"]["points"]}
    assert metrics["trend"]["grain"] == "day"
    assert metrics["trend"]["window_start"] == "2026-06-01"
    assert metrics["trend"]["window_end"] == "2026-06-08"
    assert trend["2026-06-02"]["requirements_created"] == 1
    assert trend["2026-06-02"]["ai_tasks_created"] == 1
    assert trend["2026-06-03"]["ai_tasks_created"] == 1
    assert trend["2026-06-03"]["completed_tasks"] == 1
    assert trend["2026-06-03"]["gitlab_commits"] == 3
    assert trend["2026-06-03"]["online_errors"] == 1
    assert trend["2026-06-03"]["usage_events"] == 12
    assert trend["2026-06-03"]["user_feedback"] == 1
    assert trend["2026-06-03"]["iteration_suggestions"] == 1
    assert trend["2026-06-08"]["requirements_created"] == 0


def test_dashboard_source_rows_from_store_filters_knowledge_documents_by_roles():
    store = SimpleNamespace(
        ai_tasks={},
        audit_events=[],
        bugs={},
        code_review_reports={},
        gitlab_daily_code_metrics={},
        gitlab_mr_snapshots={},
        human_reviews={},
        iteration_plan_suggestions={},
        jenkins_release_records={},
        knowledge_deposits={},
        knowledge_documents={
            "doc_allowed": {"id": "doc_allowed", "permission_roles": ["admin"]},
            "doc_denied": {"id": "doc_denied", "permission_roles": ["viewer"]},
        },
        mock_writebacks={},
        online_log_metrics={},
        product_git_repositories={},
        product_modules={},
        product_versions={},
        products={},
        requirements={},
        user_feedback={},
        user_usage_metrics={},
    )

    rows = dashboard_source_rows_from_store(
        store,
        can_read_roles=lambda user, roles: bool(set(user["roles"]) & set(roles)),
        user={"roles": ["admin"]},
    )

    assert [document["id"] for document in rows["knowledge_documents"]] == ["doc_allowed"]


def test_dashboard_snapshot_record_and_store_sync_use_stable_id():
    def stable_id(prefix: str, payload: dict[str, str]) -> str:
        return f"{prefix}_{payload['product_id']}_{payload['time_range']}"

    store = SimpleNamespace(
        dashboard_metric_snapshots={
            "dashboard_snapshot_all_7d": {
                "created_at": "2026-06-01T00:00:00+00:00",
                "id": "dashboard_snapshot_all_7d",
            }
        },
        snapshot=lambda value: dict(value),
    )

    sync_dashboard_metric_snapshot(
        store,
        data={"summary": {"requirements": 2}},
        cutoff=None,
        product_id=None,
        stable_record_id=stable_id,
        time_range="7d",
    )
    record = dashboard_metric_snapshot_record(
        data={"summary": {"requirements": 2}},
        cutoff=None,
        product_id=None,
        stable_record_id=stable_id,
        time_range="7d",
    )

    assert store.dashboard_metric_snapshots["dashboard_snapshot_all_7d"]["created_at"] == (
        "2026-06-01T00:00:00+00:00"
    )
    assert store.dashboard_metric_snapshots["dashboard_snapshot_all_7d"]["metrics"] == {
        "summary": {"requirements": 2}
    }
    assert record["id"] == "dashboard_snapshot_all_7d"
    assert record["metrics"] == {"summary": {"requirements": 2}}


def test_dashboard_snapshot_sync_uses_repository_when_available():
    def stable_id(prefix: str, payload: dict[str, str]) -> str:
        return f"{prefix}_{payload['product_id']}_{payload['time_range']}"

    saved_snapshots: list[dict] = []

    class Repository:
        def save_dashboard_metric_snapshot_record(self, snapshot: dict) -> None:
            saved_snapshots.append(snapshot)

    store = SimpleNamespace(
        dashboard_metric_snapshots={},
        repository=Repository(),
        snapshot=lambda value: dict(value),
    )

    sync_dashboard_metric_snapshot(
        store,
        data={"summary": {"requirements": 3}},
        cutoff=None,
        product_id="product_001",
        stable_record_id=stable_id,
        time_range="7d",
    )

    assert store.dashboard_metric_snapshots == {}
    assert saved_snapshots == [
        {
            "created_at": saved_snapshots[0]["created_at"],
            "id": "dashboard_snapshot_product_001_7d",
            "metrics": {"summary": {"requirements": 3}},
            "product_id": "product_001",
            "time_range": "7d",
            "updated_at": saved_snapshots[0]["updated_at"],
            "window_end": saved_snapshots[0]["window_end"],
            "window_start": None,
        }
    ]
