from __future__ import annotations

from typing import Any

from app.api.deps import api_error


def _collection(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, {})
    return collection if isinstance(collection, dict) else {}


def _record(
    current_store: Any,
    collection_name: str,
    record_id: str | None,
) -> dict[str, Any] | None:
    if record_id is None:
        return None
    item = _collection(current_store, collection_name).get(str(record_id))
    return item if isinstance(item, dict) else None


def _records(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    return list(_collection(current_store, collection_name).values())


def _task(current_store: Any, task_id: str | None) -> dict[str, Any] | None:
    return _record(current_store, "ai_tasks", task_id)


def _tasks(current_store: Any) -> list[dict[str, Any]]:
    return _records(current_store, "ai_tasks")


def _audit_events(current_store: Any) -> list[dict[str, Any]]:
    events = getattr(current_store, "audit_events", [])
    return events if isinstance(events, list) else []


def lifecycle_mock_issue(current_store: Any, subject_id: str) -> dict[str, Any] | None:
    for result in _records(current_store, "mock_writebacks"):
        for issue in result.get("issues", []):
            if issue["id"] == subject_id:
                return issue
    return None


def lifecycle_audit_event(current_store: Any, subject_id: str) -> dict[str, Any] | None:
    return next(
        (event for event in _audit_events(current_store) if event["id"] == subject_id),
        None,
    )


def lifecycle_require_tasks_by_requirement(
    current_store: Any,
    requirement_id: str,
) -> list[dict[str, Any]]:
    requirement = _record(current_store, "requirements", requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    return [task for task in _tasks(current_store) if task.get("requirement_id") == requirement_id]


def lifecycle_require_task(current_store: Any, task_id: str | None) -> dict[str, Any]:
    task = _task(current_store, task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    return task


def task_product_id(current_store: Any, task_id: str | None) -> str | None:
    if task_id is None:
        return None
    task = _task(current_store, task_id)
    return str(task["product_id"]) if task is not None and task.get("product_id") else None


def subject_product_id(
    current_store: Any,
    subject_type: str | None,
    subject_id: str | None,
) -> str | None:
    if not subject_type or not subject_id:
        return None
    normalized_id = str(subject_id)
    if subject_type == "product":
        return normalized_id if _record(current_store, "products", normalized_id) else None
    if subject_type in {"product_version", "iteration_version"}:
        version = _record(current_store, "product_versions", normalized_id)
        return str(version["product_id"]) if version is not None else None
    if subject_type == "product_module":
        module = _record(current_store, "product_modules", normalized_id)
        return str(module["product_id"]) if module is not None else None
    if subject_type == "product_git_repository":
        repository = _record(current_store, "product_git_repositories", normalized_id)
        return str(repository["product_id"]) if repository is not None else None
    if subject_type == "requirement":
        requirement = _record(current_store, "requirements", normalized_id)
        return str(requirement["product_id"]) if requirement is not None else None
    if subject_type == "ai_task":
        return task_product_id(current_store, normalized_id)
    if subject_type == "human_review":
        review = _record(current_store, "human_reviews", normalized_id)
        return task_product_id(current_store, review.get("ai_task_id") if review else None)
    if subject_type == "code_review_report":
        report = _record(current_store, "code_review_reports", normalized_id)
        return task_product_id(current_store, report.get("task_id") if report else None)
    if subject_type == "code_inspection_report":
        report = _record(current_store, "code_inspection_reports", normalized_id)
        return str(report["product_id"]) if report is not None and report.get("product_id") else None
    if subject_type == "gitlab_mr_snapshot":
        snapshot = _record(current_store, "gitlab_mr_snapshots", normalized_id)
        return str(snapshot["product_id"]) if snapshot is not None else None
    if subject_type == "mock_issue":
        issue = lifecycle_mock_issue(current_store, normalized_id)
        return task_product_id(current_store, issue.get("source_task_id") if issue else None)
    if subject_type == "knowledge_deposit":
        deposit = _record(current_store, "knowledge_deposits", normalized_id)
        return task_product_id(current_store, deposit.get("ai_task_id") if deposit else None)
    product_scoped_collections = {
        "bug": "bugs",
        "gitlab_daily_code_metric": "gitlab_daily_code_metrics",
        "jenkins_release": "jenkins_release_records",
        "online_log_metric": "online_log_metrics",
        "user_feedback": "user_feedback",
        "user_usage_metric": "user_usage_metrics",
        "iteration_plan_suggestion": "iteration_plan_suggestions",
    }
    collection_name = product_scoped_collections.get(subject_type)
    if collection_name is None:
        return None
    item = _record(current_store, collection_name, normalized_id)
    return str(item["product_id"]) if item is not None and item.get("product_id") else None


def lifecycle_subject_tasks(
    current_store: Any,
    *,
    subject_type: str,
    subject_id: str,
    resolving_audit_subject: bool = False,
) -> list[dict[str, Any]]:
    if subject_type == "requirement":
        return lifecycle_require_tasks_by_requirement(current_store, subject_id)
    if subject_type == "ai_task":
        return [lifecycle_require_task(current_store, subject_id)]
    if subject_type == "product":
        if _record(current_store, "products", subject_id) is None:
            raise api_error(404, "NOT_FOUND", "Product not found")
        return [task for task in _tasks(current_store) if task.get("product_id") == subject_id]
    if subject_type == "human_review":
        review = _record(current_store, "human_reviews", subject_id)
        if review is None:
            raise api_error(404, "NOT_FOUND", "Review not found")
        return [lifecycle_require_task(current_store, review.get("ai_task_id"))]
    if subject_type == "code_review_report":
        report = _record(current_store, "code_review_reports", subject_id)
        if report is None:
            raise api_error(404, "NOT_FOUND", "Code review report not found")
        return [lifecycle_require_task(current_store, report.get("task_id"))]
    if subject_type == "code_inspection_report":
        report = _record(current_store, "code_inspection_reports", subject_id)
        if report is None:
            raise api_error(404, "NOT_FOUND", "Code inspection report not found")
        tasks = [
            task
            for task_id in report.get("created_task_ids", [])
            if (task := _task(current_store, str(task_id))) is not None
        ]
        for bug_id in report.get("created_bug_ids", []):
            bug = _record(current_store, "bugs", str(bug_id))
            if bug is None:
                continue
            if bug.get("related_task_id"):
                task = _task(current_store, bug.get("related_task_id"))
                if task is not None:
                    tasks.append(task)
            elif bug.get("requirement_id"):
                tasks.extend(
                    lifecycle_require_tasks_by_requirement(current_store, bug["requirement_id"])
                )
        if tasks:
            unique_tasks = {str(task["id"]): task for task in tasks}
            return list(unique_tasks.values())
        return [
            task
            for task in _tasks(current_store)
            if task.get("product_id") == report.get("product_id")
        ]
    if subject_type == "gitlab_mr_snapshot":
        snapshot = _record(current_store, "gitlab_mr_snapshots", subject_id)
        if snapshot is None:
            raise api_error(404, "NOT_FOUND", "GitLab MR snapshot not found")
        return [lifecycle_require_task(current_store, snapshot.get("technical_solution_task_id"))]
    if subject_type == "mock_issue":
        issue = lifecycle_mock_issue(current_store, subject_id)
        if issue is None:
            raise api_error(404, "NOT_FOUND", "Mock issue not found")
        return [lifecycle_require_task(current_store, issue.get("source_task_id"))]
    if subject_type == "knowledge_deposit":
        deposit = _record(current_store, "knowledge_deposits", subject_id)
        if deposit is None:
            raise api_error(404, "NOT_FOUND", "Knowledge deposit not found")
        return [lifecycle_require_task(current_store, deposit.get("ai_task_id"))]
    if subject_type == "audit_event":
        event = lifecycle_audit_event(current_store, subject_id)
        if event is None:
            raise api_error(404, "NOT_FOUND", "Audit event not found")
        if event.get("ai_task_id"):
            return [lifecycle_require_task(current_store, event.get("ai_task_id"))]
        nested_type = event.get("subject_type")
        nested_id = event.get("subject_id")
        if nested_type and nested_id and not resolving_audit_subject:
            return lifecycle_subject_tasks(
                current_store,
                subject_type=nested_type,
                subject_id=nested_id,
                resolving_audit_subject=True,
            )
        return []
    if subject_type == "bug":
        bug = _record(current_store, "bugs", subject_id)
        if bug is None:
            raise api_error(404, "NOT_FOUND", "Bug not found")
        if bug.get("related_task_id"):
            return [lifecycle_require_task(current_store, bug.get("related_task_id"))]
        if bug.get("requirement_id"):
            return lifecycle_require_tasks_by_requirement(current_store, bug["requirement_id"])
        return [
            task
            for task in _tasks(current_store)
            if task.get("product_id") == bug.get("product_id")
        ]
    evidence_collections = {
        "gitlab_daily_code_metric": (
            "gitlab_daily_code_metrics",
            "GitLab daily code metric",
        ),
        "jenkins_release": ("jenkins_release_records", "Jenkins release"),
        "online_log_metric": ("online_log_metrics", "Online log metric"),
        "user_usage_metric": ("user_usage_metrics", "User usage metric"),
        "user_feedback": ("user_feedback", "User feedback"),
        "iteration_plan_suggestion": (
            "iteration_plan_suggestions",
            "Iteration plan suggestion",
        ),
    }
    if subject_type in evidence_collections:
        collection_name, label = evidence_collections[subject_type]
        evidence = _record(current_store, collection_name, subject_id)
        if evidence is None:
            raise api_error(404, "NOT_FOUND", f"{label} not found")
        return [
            task
            for task in _tasks(current_store)
            if task.get("product_id") == evidence.get("product_id")
            and (
                not evidence.get("version_id")
                or not task.get("version_id")
                or task.get("version_id") == evidence.get("version_id")
            )
            and (
                not evidence.get("module_code")
                or not task.get("module_code")
                or task.get("module_code") == evidence.get("module_code")
            )
        ]
    raise api_error(400, "VALIDATION_ERROR", "Unsupported lifecycle subject_type")


def tasks_for_lifecycle_subject(
    current_store: Any,
    *,
    subject_type: str | None,
    subject_id: str | None,
    product_id: str | None,
    version_id: str | None,
    module_code: str | None,
) -> list[dict[str, Any]]:
    if subject_type:
        if not subject_id:
            raise api_error(400, "VALIDATION_ERROR", "subject_id is required")
        tasks = lifecycle_subject_tasks(
            current_store,
            subject_type=subject_type,
            subject_id=str(subject_id),
        )
    else:
        tasks = [
            task
            for task in _tasks(current_store)
            if not product_id or task.get("product_id") == product_id
        ]
    if product_id:
        tasks = [task for task in tasks if task.get("product_id") == product_id]
    if version_id:
        tasks = [task for task in tasks if task.get("version_id") == version_id]
    if module_code:
        tasks = [task for task in tasks if task.get("module_code") == module_code]
    tasks.sort(key=lambda task: task["id"])
    return tasks


def lifecycle_subject(
    current_store: Any,
    *,
    subject_type: str | None,
    subject_id: str | None,
    product_id: str | None,
) -> dict[str, Any]:
    if subject_type and subject_id:
        normalized_subject_id = str(subject_id)
        tasks = lifecycle_subject_tasks(
            current_store,
            subject_type=subject_type,
            subject_id=normalized_subject_id,
        )
        resolved_product_id = tasks[0]["product_id"] if tasks else None
        if subject_type == "requirement":
            requirement = _record(current_store, "requirements", normalized_subject_id)
            resolved_product_id = requirement["product_id"] if requirement is not None else None
        elif subject_type == "product":
            resolved_product_id = normalized_subject_id
        elif subject_type == "gitlab_mr_snapshot":
            snapshot = _record(current_store, "gitlab_mr_snapshots", normalized_subject_id)
            resolved_product_id = snapshot["product_id"] if snapshot is not None else None
        elif subject_type == "code_inspection_report":
            report = _record(current_store, "code_inspection_reports", normalized_subject_id)
            resolved_product_id = report["product_id"] if report is not None else None
        elif subject_type == "bug":
            bug = _record(current_store, "bugs", normalized_subject_id)
            resolved_product_id = bug["product_id"] if bug is not None else None
        elif subject_type in {
            "gitlab_daily_code_metric",
            "jenkins_release",
            "online_log_metric",
            "user_usage_metric",
            "user_feedback",
            "iteration_plan_suggestion",
        }:
            resolved_product_id = subject_product_id(
                current_store,
                subject_type,
                normalized_subject_id,
            )
        return {
            "type": subject_type,
            "id": normalized_subject_id,
            "product_id": resolved_product_id,
        }
    return {"type": "product", "id": product_id, "product_id": product_id}
