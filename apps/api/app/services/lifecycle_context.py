from __future__ import annotations

from typing import Any

from app.api.deps import api_error
from app.services.lifecycle_evidence import (
    lifecycle_matching_evidence,
    lifecycle_missing_context,
)
from app.services.lifecycle_risks import (
    lifecycle_risk_signals,
    sync_lifecycle_context_records,
)
from app.services.lifecycle_source import (
    lifecycle_query_repository,
    lifecycle_source_store,
    save_lifecycle_context_records,
)
from app.services.lifecycle_subjects import (
    lifecycle_subject,
    tasks_for_lifecycle_subject,
)
from app.services.task_access import can_read_task


def lifecycle_relation(
    *,
    subject_type: str,
    subject_id: str,
    relation_type: str,
    summary: str,
    product_id: str | None = None,
    version_id: str | None = None,
    module_code: str | None = None,
    source_module: str = "lifecycle_context",
    observed_at: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "subject_type": subject_type,
        "subject_id": subject_id,
        "relation_type": relation_type,
        "summary": summary,
        "confidence": 1.0,
        "product_id": product_id,
        "version_id": version_id,
        "module_code": module_code,
        "source_module": source_module,
        "observed_at": observed_at,
        "metadata": metadata or {},
    }


def lifecycle_upstream(
    current_store: Any,
    *,
    subject_type: str | None,
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if subject_type in {None, "product", "requirement"}:
        return []
    relations: list[dict[str, Any]] = []
    seen_requirement_ids: set[str] = set()
    for task in tasks:
        requirement_id = task.get("requirement_id")
        if not requirement_id or requirement_id in seen_requirement_ids:
            continue
        requirement = current_store.requirements.get(requirement_id)
        if requirement is None:
            continue
        seen_requirement_ids.add(requirement_id)
        relations.append(
            lifecycle_relation(
                subject_type="requirement",
                subject_id=requirement["id"],
                relation_type="derived_from_requirement",
                summary=requirement["title"],
                product_id=requirement["product_id"],
                version_id=requirement["version_id"],
                module_code=requirement.get("module_code"),
                source_module="requirement",
                observed_at=requirement.get("created_at"),
                metadata={"status": requirement["status"]},
            )
        )
    return relations


def lifecycle_downstream(
    current_store: Any,
    *,
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    task_ids = {task["id"] for task in tasks}
    for task in tasks:
        relations.append(
            lifecycle_relation(
                subject_type="ai_task",
                subject_id=task["id"],
                relation_type=f"generates_{task['task_type']}",
                summary=task["title"],
                product_id=task["product_id"],
                version_id=task["version_id"],
                module_code=task.get("module_code"),
                source_module="ai_task",
                observed_at=task.get("created_at"),
                metadata={"task_type": task["task_type"], "status": task["status"]},
            )
        )
        for review_id in task.get("review_ids", []):
            review = current_store.human_reviews.get(review_id)
            if review is None:
                continue
            relations.append(
                lifecycle_relation(
                    subject_type="human_review",
                    subject_id=review_id,
                    relation_type="creates_human_review",
                    summary=f"{review['stage']} review {review['status']}",
                    product_id=task["product_id"],
                    version_id=task["version_id"],
                    module_code=task.get("module_code"),
                    source_module="review",
                    metadata={"status": review["status"], "stage": review["stage"]},
                )
            )
        report_id = task.get("code_review_report_id")
        if report_id and report_id in current_store.code_review_reports:
            report = current_store.code_review_reports[report_id]
            relations.append(
                lifecycle_relation(
                    subject_type="code_review_report",
                    subject_id=report_id,
                    relation_type="creates_code_review_report",
                    summary=report["summary"],
                    product_id=task["product_id"],
                    version_id=task["version_id"],
                    module_code=task.get("module_code"),
                    source_module="code_review_executor",
                    metadata={"status": report["status"], "risk_level": report["risk_level"]},
                )
            )
    for snapshot in current_store.gitlab_mr_snapshots.values():
        if snapshot.get("technical_solution_task_id") not in task_ids:
            continue
        relations.append(
            lifecycle_relation(
                subject_type="gitlab_mr_snapshot",
                subject_id=snapshot["id"],
                relation_type="captures_gitlab_mr_snapshot",
                summary=snapshot["title"],
                product_id=next(
                    task["product_id"]
                    for task in tasks
                    if task["id"] == snapshot["technical_solution_task_id"]
                ),
                source_module="gitlab_review",
                observed_at=snapshot.get("created_at"),
                metadata={"mr_iid": snapshot["mr_iid"], "writeback_allowed": False},
            )
        )
    for result in current_store.mock_writebacks.values():
        for issue in result["issues"]:
            if issue["source_task_id"] not in task_ids:
                continue
            task = current_store.ai_tasks[issue["source_task_id"]]
            relations.append(
                lifecycle_relation(
                    subject_type="mock_issue",
                    subject_id=issue["id"],
                    relation_type="creates_mock_issue",
                    summary=issue["title"],
                    product_id=task["product_id"],
                    version_id=task["version_id"],
                    module_code=task.get("module_code"),
                    source_module="integration",
                    metadata={
                        "status": issue["status"],
                        "idempotency_key": result["idempotency_key"],
                    },
                )
            )
    for deposit in current_store.knowledge_deposits.values():
        if deposit["ai_task_id"] not in task_ids:
            continue
        task = current_store.ai_tasks[deposit["ai_task_id"]]
        relations.append(
            lifecycle_relation(
                subject_type="knowledge_deposit",
                subject_id=deposit["id"],
                relation_type="creates_knowledge_deposit",
                summary=deposit["title"],
                product_id=task["product_id"],
                version_id=task["version_id"],
                module_code=task.get("module_code"),
                source_module="knowledge",
                metadata={"status": deposit["status"]},
            )
        )
    for event in current_store.audit_events:
        task_match = event.get("ai_task_id") in task_ids
        subject_task_match = event.get("subject_type") == "ai_task" and event.get(
            "subject_id"
        ) in task_ids
        requirement_match = any(
            event.get("subject_type") == "requirement"
            and event.get("subject_id") == task.get("requirement_id")
            for task in tasks
        )
        if not (task_match or subject_task_match or requirement_match):
            continue
        relations.append(
            lifecycle_relation(
                subject_type="audit_event",
                subject_id=event["id"],
                relation_type="creates_audit_event",
                summary=event["event_type"],
                product_id=None,
                source_module="audit",
                observed_at=event.get("created_at"),
                metadata={"event_type": event["event_type"]},
            )
        )
    matching_evidence = lifecycle_matching_evidence(current_store, tasks)
    for bug in matching_evidence["bug"]:
        relations.append(
            lifecycle_relation(
                subject_type="bug",
                subject_id=bug["id"],
                relation_type="observes_bug",
                summary=bug["title"],
                product_id=bug["product_id"],
                version_id=bug.get("version_id"),
                module_code=bug.get("module_code"),
                source_module="bug",
                observed_at=bug.get("updated_at") or bug.get("created_at"),
                metadata={
                    "severity": bug["severity"],
                    "source": bug["source"],
                    "status": bug["status"],
                },
            )
        )
    for metric in matching_evidence["gitlab_daily_code_metric"]:
        relations.append(
            lifecycle_relation(
                subject_type="gitlab_daily_code_metric",
                subject_id=metric["id"],
                relation_type="observes_gitlab_code_metric",
                summary=f"{metric.get('metric_date')} commit_count={metric.get('commit_count', 0)}",
                product_id=metric["product_id"],
                source_module="devops_metrics",
                observed_at=metric.get("metric_date") or metric.get("updated_at"),
                metadata={
                    "changed_files": metric.get("changed_files", 0),
                    "commit_count": metric.get("commit_count", 0),
                    "quality_score": metric.get("quality_score"),
                    "risk_count": metric.get("risk_count", 0),
                },
            )
        )
    for release in matching_evidence["jenkins_release"]:
        relations.append(
            lifecycle_relation(
                subject_type="jenkins_release",
                subject_id=release["id"],
                relation_type="observes_jenkins_release",
                summary=f"{release['job_name']} {release['status']}",
                product_id=release["product_id"],
                version_id=release.get("version_id"),
                source_module="devops_metrics",
                observed_at=release.get("deployed_at") or release.get("updated_at"),
                metadata={
                    "build_id": release["build_id"],
                    "environment": release.get("environment"),
                    "failure_reason": release.get("failure_reason"),
                    "status": release["status"],
                },
            )
        )
    for metric in matching_evidence["online_log_metric"]:
        relations.append(
            lifecycle_relation(
                subject_type="online_log_metric",
                subject_id=metric["id"],
                relation_type="observes_online_log_metric",
                summary=f"{metric['environment']} error_rate={metric.get('error_rate', 0)}",
                product_id=metric["product_id"],
                module_code=metric.get("module_code"),
                source_module="devops_metrics",
                observed_at=metric.get("window_end") or metric.get("updated_at"),
                metadata={
                    "environment": metric["environment"],
                    "error_count": metric.get("error_count", 0),
                    "error_rate": metric.get("error_rate", 0),
                    "request_count": metric.get("request_count", 0),
                },
            )
        )
    for metric in matching_evidence["user_usage_metric"]:
        relations.append(
            lifecycle_relation(
                subject_type="user_usage_metric",
                subject_id=metric["id"],
                relation_type="observes_user_usage_metric",
                summary=f"{metric['feature_code']} events={metric.get('event_count', 0)}",
                product_id=metric["product_id"],
                module_code=metric.get("module_code"),
                source_module="user_insights",
                observed_at=metric.get("window_end") or metric.get("updated_at"),
                metadata={
                    "active_users": metric.get("active_users", 0),
                    "event_count": metric.get("event_count", 0),
                    "feature_code": metric["feature_code"],
                    "user_segment": metric.get("user_segment"),
                },
            )
        )
    for feedback in matching_evidence["user_feedback"]:
        relations.append(
            lifecycle_relation(
                subject_type="user_feedback",
                subject_id=feedback["id"],
                relation_type="observes_user_feedback",
                summary=feedback["content"],
                product_id=feedback["product_id"],
                module_code=feedback.get("module_code"),
                source_module="user_insights",
                observed_at=feedback.get("updated_at") or feedback.get("created_at"),
                metadata={
                    "feedback_type": feedback["feedback_type"],
                    "sentiment": feedback.get("sentiment"),
                    "status": feedback["status"],
                },
            )
        )
    for suggestion in matching_evidence["iteration_plan_suggestion"]:
        relations.append(
            lifecycle_relation(
                subject_type="iteration_plan_suggestion",
                subject_id=suggestion["id"],
                relation_type="observes_iteration_suggestion",
                summary=suggestion["title"],
                product_id=suggestion["product_id"],
                version_id=suggestion.get("version_id"),
                module_code=",".join(suggestion.get("module_codes", [])) or None,
                source_module="iteration_planning",
                observed_at=suggestion.get("updated_at") or suggestion.get("created_at"),
                metadata={
                    "confidence_level": suggestion.get("confidence_level"),
                    "priority": suggestion.get("priority"),
                    "status": suggestion["status"],
                },
            )
        )
    return relations


def lifecycle_context_response(
    *,
    current_store: Any,
    direction: str,
    include_risks: bool,
    module_code: str | None,
    product_id: str | None,
    subject_id: str | None,
    subject_type: str | None,
    user: dict[str, Any],
    version_id: str | None,
) -> dict[str, Any]:
    repository = lifecycle_query_repository(current_store)
    if repository is not None:
        source_product_id = (
            product_id
            or (str(subject_id) if subject_type == "product" and subject_id else None)
        )
        current_store = lifecycle_source_store(
            repository.get_lifecycle_context_source_rows(product_id=source_product_id)
        )
    if not ((subject_type and subject_id) or product_id):
        raise api_error(
            400,
            "LIFECYCLE_SUBJECT_REQUIRED",
            "subject_type/subject_id or product_id is required",
        )
    if direction not in {"upstream", "downstream", "both"}:
        raise api_error(400, "VALIDATION_ERROR", "direction must be upstream, downstream, or both")

    tasks = tasks_for_lifecycle_subject(
        current_store,
        subject_type=subject_type,
        subject_id=subject_id,
        product_id=product_id,
        version_id=version_id,
        module_code=module_code,
    )
    if subject_type == "ai_task":
        subject_task = current_store.ai_tasks.get(str(subject_id))
        if subject_task is None:
            raise api_error(404, "NOT_FOUND", "AI task not found")
        if not can_read_task(user, subject_task):
            raise api_error(403, "FORBIDDEN", "Insufficient task role")
    tasks = [task for task in tasks if can_read_task(user, task)]
    upstream = (
        lifecycle_upstream(current_store, subject_type=subject_type, tasks=tasks)
        if direction in {"upstream", "both"}
        else []
    )
    downstream = (
        lifecycle_downstream(current_store, tasks=tasks)
        if direction in {"downstream", "both"}
        else []
    )
    risk_signals = lifecycle_risk_signals(current_store, tasks=tasks) if include_risks else []
    missing_context = lifecycle_missing_context(current_store, tasks=tasks)
    subject = lifecycle_subject(
        current_store,
        subject_type=subject_type,
        subject_id=subject_id,
        product_id=product_id,
    )
    sync_lifecycle_context_records(
        current_store,
        subject=subject,
        upstream=upstream,
        downstream=downstream,
        risk_signals=risk_signals,
        tasks=tasks,
    )
    if repository is not None:
        repository.save_lifecycle_context(
            {
                "lifecycle_context_edges": current_store.lifecycle_context_edges,
                "lifecycle_risk_signals": current_store.lifecycle_risk_signals,
            }
        )
    else:
        save_lifecycle_context_records(current_store)
    return {
        "status": "available",
        "subject": subject,
        "upstream": upstream,
        "downstream": downstream,
        "risk_signals": risk_signals,
        "missing_context": missing_context,
        "summary": {
            "upstream_count": len(upstream),
            "downstream_count": len(downstream),
            "risk_count": len(risk_signals),
            "missing_context_count": len(missing_context),
        },
    }
