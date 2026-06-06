from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any


def sync_dashboard_metric_snapshot(
    current_store: Any,
    *,
    data: dict[str, Any],
    cutoff: datetime | None,
    product_id: str | None,
    stable_record_id: Callable[[str, dict[str, Any]], str],
    time_range: str | None,
) -> None:
    now = datetime.now(UTC).isoformat()
    snapshot_id = stable_record_id(
        "dashboard_snapshot",
        {
            "product_id": product_id or "all",
            "time_range": time_range or "all",
        },
    )
    existing = current_store.dashboard_metric_snapshots.get(snapshot_id, {})
    current_store.dashboard_metric_snapshots[snapshot_id] = {
        "created_at": existing.get("created_at") or now,
        "id": snapshot_id,
        "metrics": current_store.snapshot(data),
        "product_id": product_id,
        "time_range": time_range or "all",
        "updated_at": now,
        "window_end": now,
        "window_start": cutoff.isoformat() if cutoff else None,
    }


def dashboard_metric_snapshot_record(
    *,
    data: dict[str, Any],
    cutoff: datetime | None,
    product_id: str | None,
    stable_record_id: Callable[[str, dict[str, Any]], str],
    time_range: str | None,
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    snapshot_id = stable_record_id(
        "dashboard_snapshot",
        {
            "product_id": product_id or "all",
            "time_range": time_range or "all",
        },
    )
    return {
        "created_at": now,
        "id": snapshot_id,
        "metrics": json.loads(json.dumps(data, ensure_ascii=False)),
        "product_id": product_id,
        "time_range": time_range or "all",
        "updated_at": now,
        "window_end": now,
        "window_start": cutoff.isoformat() if cutoff else None,
    }


def dashboard_source_rows_from_store(
    current_store: Any,
    *,
    can_read_roles: Callable[[dict[str, Any], list[str]], bool],
    user: dict[str, Any],
) -> dict[str, Any]:
    return {
        "audit_events": list(current_store.audit_events),
        "bugs": list(current_store.bugs.values()),
        "code_review_reports": list(current_store.code_review_reports.values()),
        "gitlab_daily_code_metrics": list(current_store.gitlab_daily_code_metrics.values()),
        "gitlab_mr_snapshots": list(current_store.gitlab_mr_snapshots.values()),
        "human_reviews": list(current_store.human_reviews.values()),
        "iteration_plan_suggestions": list(current_store.iteration_plan_suggestions.values()),
        "jenkins_release_records": list(current_store.jenkins_release_records.values()),
        "knowledge_deposits": list(current_store.knowledge_deposits.values()),
        "knowledge_documents": [
            document
            for document in current_store.knowledge_documents.values()
            if can_read_roles(user, document["permission_roles"])
        ],
        "mock_writebacks": list(current_store.mock_writebacks.values()),
        "online_log_metrics": list(current_store.online_log_metrics.values()),
        "product_git_repositories": list(current_store.product_git_repositories.values()),
        "product_modules": list(current_store.product_modules.values()),
        "product_versions": list(current_store.product_versions.values()),
        "products": [
            product
            for product in current_store.products.values()
            if product.get("status") == "active"
        ],
        "requirements": list(current_store.requirements.values()),
        "tasks": list(current_store.ai_tasks.values()),
        "user_feedback": list(current_store.user_feedback.values()),
        "user_usage_metrics": list(current_store.user_usage_metrics.values()),
    }


def build_dashboard_metrics_data(
    rows: dict[str, Any],
    *,
    can_read_task: Callable[[dict[str, Any], dict[str, Any]], bool],
    cutoff: datetime | None,
    product_id: str | None,
    time_range: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    products = [
        product
        for product in rows.get("products", [])
        if product.get("status") == "active" and (product_id is None or product["id"] == product_id)
    ]
    requirements = [
        requirement
        for requirement in rows.get("requirements", [])
        if product_id is None or requirement["product_id"] == product_id
    ]
    tasks = [
        task
        for task in rows.get("tasks", [])
        if (product_id is None or task["product_id"] == product_id) and can_read_task(user, task)
    ]
    task_ids = {task["id"] for task in tasks}
    pending_reviews = [
        review
        for review in rows.get("human_reviews", [])
        if review["status"] == "pending" and review["ai_task_id"] in task_ids
    ]
    knowledge_documents = [
        document
        for document in rows.get("knowledge_documents", [])
        if product_id is None
        or _dashboard_knowledge_document_product_id(rows, document) == product_id
    ]
    knowledge_deposits = [
        deposit
        for deposit in rows.get("knowledge_deposits", [])
        if deposit["ai_task_id"] in task_ids
    ]
    audit_events = [
        event
        for event in rows.get("audit_events", [])
        if _dashboard_audit_event_matches_product(rows, event, product_id)
    ]
    bugs = [
        bug
        for bug in rows.get("bugs", [])
        if (product_id is None or bug.get("product_id") == product_id)
        and _dashboard_matches_time_range(bug, cutoff, ("updated_at", "created_at"))
    ]
    gitlab_metrics = [
        metric
        for metric in rows.get("gitlab_daily_code_metrics", [])
        if (product_id is None or metric.get("product_id") == product_id)
        and _dashboard_matches_time_range(
            metric,
            cutoff,
            ("metric_date", "updated_at", "created_at"),
        )
    ]
    jenkins_releases = [
        release
        for release in rows.get("jenkins_release_records", [])
        if (product_id is None or release.get("product_id") == product_id)
        and _dashboard_matches_time_range(
            release,
            cutoff,
            ("deployed_at", "started_at", "updated_at", "created_at"),
        )
    ]
    online_log_metrics = [
        metric
        for metric in rows.get("online_log_metrics", [])
        if (product_id is None or metric.get("product_id") == product_id)
        and _dashboard_matches_time_range(
            metric,
            cutoff,
            ("window_end", "window_start", "updated_at", "created_at"),
        )
    ]
    usage_metrics = [
        metric
        for metric in rows.get("user_usage_metrics", [])
        if (product_id is None or metric.get("product_id") == product_id)
        and _dashboard_matches_time_range(
            metric,
            cutoff,
            ("window_end", "window_start", "updated_at", "created_at"),
        )
    ]
    feedback_items = [
        feedback
        for feedback in rows.get("user_feedback", [])
        if (product_id is None or feedback.get("product_id") == product_id)
        and _dashboard_matches_time_range(feedback, cutoff, ("updated_at", "created_at"))
    ]
    iteration_suggestions = [
        suggestion
        for suggestion in rows.get("iteration_plan_suggestions", [])
        if (product_id is None or suggestion.get("product_id") == product_id)
        and _dashboard_matches_time_range(suggestion, cutoff, ("updated_at", "created_at"))
    ]
    open_bugs = [bug for bug in bugs if bug.get("status") != "closed"]
    high_severity_bugs = [
        bug for bug in open_bugs if bug.get("severity") in {"blocker", "critical", "major"}
    ]
    latest_high_severity_bugs = sorted(
        high_severity_bugs,
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
        reverse=True,
    )[:5]
    online_request_count = int(_dashboard_number_total(online_log_metrics, "request_count"))
    online_error_count = int(_dashboard_number_total(online_log_metrics, "error_count"))
    online_error_rate = (
        round(online_error_count / online_request_count, 6)
        if online_request_count
        else 0
    )
    latest_tasks = sorted(tasks, key=lambda item: item["id"], reverse=True)[:5]
    recent_audit_events = sorted(
        audit_events,
        key=lambda item: item["sequence"],
        reverse=True,
    )[:8]
    recent_knowledge_documents = sorted(
        knowledge_documents,
        key=lambda item: item["id"],
        reverse=True,
    )[:5]
    return {
        "summary": {
            "active_products": len(products),
            "ai_tasks": len(tasks),
            "audit_events": len(audit_events),
            "knowledge_deposits": len(knowledge_deposits),
            "knowledge_documents": len(knowledge_documents),
            "pending_reviews": len(pending_reviews),
            "requirements": len(requirements),
            "bugs": len(bugs),
            "open_bugs": len(open_bugs),
            "high_severity_bugs": len(high_severity_bugs),
            "gitlab_commits": int(_dashboard_number_total(gitlab_metrics, "commit_count")),
            "jenkins_releases": len(jenkins_releases),
            "online_errors": online_error_count,
            "user_feedback": len(feedback_items),
            "usage_events": int(_dashboard_number_total(usage_metrics, "event_count")),
            "iteration_suggestions": len(iteration_suggestions),
        },
        "bug_status_counts": _status_counts(bugs),
        "latest_high_severity_bugs": json.loads(
            json.dumps(latest_high_severity_bugs, ensure_ascii=False)
        ),
        "gitlab_daily_summary": {
            "metric_count": len(gitlab_metrics),
            "commit_count": int(_dashboard_number_total(gitlab_metrics, "commit_count")),
            "merge_request_count": int(
                _dashboard_number_total(gitlab_metrics, "merge_request_count")
            ),
            "changed_files": int(_dashboard_number_total(gitlab_metrics, "changed_files")),
            "risk_count": int(_dashboard_number_total(gitlab_metrics, "risk_count")),
            "average_quality_score": _dashboard_average_number(
                gitlab_metrics,
                "quality_score",
            ),
        },
        "jenkins_release_status_counts": _status_counts(jenkins_releases),
        "online_log_summary": {
            "metric_count": len(online_log_metrics),
            "request_count": online_request_count,
            "error_count": online_error_count,
            "error_rate": online_error_rate,
            "max_p95_latency_ms": _dashboard_max_number(online_log_metrics, "p95_latency_ms"),
            "max_p99_latency_ms": _dashboard_max_number(online_log_metrics, "p99_latency_ms"),
        },
        "usage_metric_summary": {
            "metric_count": len(usage_metrics),
            "active_users": int(_dashboard_number_total(usage_metrics, "active_users")),
            "event_count": int(_dashboard_number_total(usage_metrics, "event_count")),
            "conversion_count": int(_dashboard_number_total(usage_metrics, "conversion_count")),
            "error_count": int(_dashboard_number_total(usage_metrics, "error_count")),
        },
        "user_feedback_status_counts": _status_counts(feedback_items),
        "iteration_suggestion_status_counts": _status_counts(iteration_suggestions),
        "requirement_status_counts": _status_counts(requirements),
        "task_status_counts": _status_counts(tasks),
        "latest_tasks": json.loads(json.dumps(latest_tasks, ensure_ascii=False)),
        "pending_reviews": json.loads(json.dumps(pending_reviews, ensure_ascii=False)),
        "recent_knowledge_documents": json.loads(
            json.dumps(recent_knowledge_documents, ensure_ascii=False)
        ),
        "recent_audit_events": json.loads(json.dumps(recent_audit_events, ensure_ascii=False)),
        "requirement_titles": [requirement["title"] for requirement in requirements[:10]],
        "time_range": time_range or "all",
    }


def dashboard_time_cutoff(time_range: str | None) -> datetime | None:
    normalized = (time_range or "all").strip().lower()
    if normalized in {"", "all"}:
        return None
    if normalized.endswith("d") and normalized[:-1].isdigit():
        days = int(normalized[:-1])
        if days > 0:
            return datetime.now(UTC) - timedelta(days=days)
    return None


def _dashboard_items_by_id(rows: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in rows.get(key, []) if item.get("id") is not None}


def _dashboard_task_product_id(rows: dict[str, Any], task_id: str | None) -> str | None:
    if not task_id:
        return None
    task = _dashboard_items_by_id(rows, "tasks").get(str(task_id))
    return str(task["product_id"]) if task is not None and task.get("product_id") else None


def _dashboard_mock_issue(rows: dict[str, Any], subject_id: str) -> dict[str, Any] | None:
    for result in rows.get("mock_writebacks", []):
        for issue in result.get("issues", []):
            if str(issue.get("id")) == subject_id:
                return issue
    return None


def _dashboard_knowledge_document_product_id(
    rows: dict[str, Any],
    document: dict[str, Any],
) -> str | None:
    if document.get("product_id"):
        return str(document["product_id"])
    document_id = document.get("id")
    for deposit in rows.get("knowledge_deposits", []):
        if deposit.get("knowledge_document_id") == document_id:
            return _dashboard_task_product_id(rows, deposit.get("ai_task_id"))
    return None


def _dashboard_subject_product_id(
    rows: dict[str, Any],
    subject_type: str | None,
    subject_id: str | None,
) -> str | None:
    if not subject_type or not subject_id:
        return None
    normalized_id = str(subject_id)
    if subject_type == "product":
        return normalized_id
    product_scoped_maps = {
        "product_version": "product_versions",
        "product_module": "product_modules",
        "product_git_repository": "product_git_repositories",
        "requirement": "requirements",
        "bug": "bugs",
        "gitlab_daily_code_metric": "gitlab_daily_code_metrics",
        "jenkins_release": "jenkins_release_records",
        "online_log_metric": "online_log_metrics",
        "user_feedback": "user_feedback",
        "user_usage_metric": "user_usage_metrics",
        "iteration_plan_suggestion": "iteration_plan_suggestions",
    }
    collection_key = product_scoped_maps.get(subject_type)
    if collection_key is not None:
        item = _dashboard_items_by_id(rows, collection_key).get(normalized_id)
        return str(item["product_id"]) if item is not None and item.get("product_id") else None
    if subject_type == "ai_task":
        return _dashboard_task_product_id(rows, normalized_id)
    if subject_type == "human_review":
        review = _dashboard_items_by_id(rows, "human_reviews").get(normalized_id)
        return _dashboard_task_product_id(rows, review.get("ai_task_id") if review else None)
    if subject_type == "code_review_report":
        report = _dashboard_items_by_id(rows, "code_review_reports").get(normalized_id)
        return _dashboard_task_product_id(rows, report.get("task_id") if report else None)
    if subject_type == "gitlab_mr_snapshot":
        snapshot = _dashboard_items_by_id(rows, "gitlab_mr_snapshots").get(normalized_id)
        if snapshot is not None and snapshot.get("product_id"):
            return str(snapshot["product_id"])
        return None
    if subject_type == "mock_issue":
        issue = _dashboard_mock_issue(rows, normalized_id)
        return _dashboard_task_product_id(rows, issue.get("source_task_id") if issue else None)
    if subject_type == "knowledge_document":
        document = _dashboard_items_by_id(rows, "knowledge_documents").get(normalized_id)
        return _dashboard_knowledge_document_product_id(rows, document) if document else None
    if subject_type == "knowledge_deposit":
        deposit = _dashboard_items_by_id(rows, "knowledge_deposits").get(normalized_id)
        return _dashboard_task_product_id(rows, deposit.get("ai_task_id") if deposit else None)
    return None


def _dashboard_audit_event_matches_product(
    rows: dict[str, Any],
    event: dict[str, Any],
    product_id: str | None,
) -> bool:
    if product_id is None:
        return True
    if _dashboard_task_product_id(rows, event.get("ai_task_id")) == product_id:
        return True
    return (
        _dashboard_subject_product_id(
            rows,
            event.get("subject_type"),
            event.get("subject_id"),
        )
        == product_id
    )


def _status_counts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in items:
        status = str(item.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return [
        {"status": status, "count": count}
        for status, count in sorted(counts.items(), key=lambda item: item[0])
    ]


def _dashboard_item_datetime(
    item: dict[str, Any],
    fields: tuple[str, ...],
) -> datetime | None:
    for field in fields:
        value = item.get(field)
        if value is None:
            continue
        text = str(value)
        try:
            if len(text) == 10 and text[4] == "-" and text[7] == "-":
                parsed = datetime.fromisoformat(text).replace(tzinfo=UTC)
            else:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                parsed = parsed.astimezone(UTC)
        except ValueError:
            continue
        return parsed
    return None


def _dashboard_matches_time_range(
    item: dict[str, Any],
    cutoff: datetime | None,
    fields: tuple[str, ...],
) -> bool:
    if cutoff is None:
        return True
    item_time = _dashboard_item_datetime(item, fields)
    return item_time is None or item_time >= cutoff


def _dashboard_number_total(items: list[dict[str, Any]], field: str) -> float:
    total = 0.0
    for item in items:
        value = item.get(field)
        if isinstance(value, int | float):
            total += float(value)
    return total


def _dashboard_max_number(items: list[dict[str, Any]], field: str) -> float | None:
    values = [float(item[field]) for item in items if isinstance(item.get(field), int | float)]
    return max(values) if values else None


def _dashboard_average_number(items: list[dict[str, Any]], field: str) -> float | None:
    values = [float(item[field]) for item in items if isinstance(item.get(field), int | float)]
    return round(sum(values) / len(values), 2) if values else None
