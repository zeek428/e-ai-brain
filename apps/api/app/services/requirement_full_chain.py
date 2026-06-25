from __future__ import annotations

from typing import Any

from app.api.deps import api_error
from app.services.bugs import bug_summary_projection
from app.services.requirements import requirement_summary_projection
from app.services.task_access import can_read_task
from app.services.task_listing import task_summary_projection
from app.services.task_workflow_context import task_workflow_read_store


def first_present_value(item: dict[str, Any], fields: tuple[str, ...]) -> str:
    for field in fields:
        value = item.get(field)
        if value is not None and str(value).strip():
            return str(value)
    return ""


def sort_by_lifecycle_time(items: list[dict[str, Any]], *fields: str) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (first_present_value(item, fields), str(item.get("id") or "")),
    )


def compact_lifecycle_title(prefix: str, subject_id: str, label: str | None = None) -> str:
    text = (label or "").strip()
    if not text or len(text) > 48:
        text = subject_id
    return f"{prefix}：{text}"


def full_chain_git_snapshot_ref(snapshot: dict[str, Any]) -> str:
    return str(snapshot.get("source_ref") or snapshot.get("mr_iid") or snapshot["id"])


def full_chain_event(
    *,
    event_type: str,
    occurred_at: str,
    subject_id: str,
    title: str,
    metadata: dict[str, Any] | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    return {
        "id": f"{event_type}:{subject_id}",
        "metadata": metadata or {},
        "occurred_at": occurred_at,
        "status": status,
        "subject_id": subject_id,
        "subject_type": event_type,
        "title": title,
        "type": event_type,
    }


def requirement_read_store(current_store: Any) -> Any:
    return task_workflow_read_store(current_store)


def _read_memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, dict) else {}


def get_requirement_response(*, current_store: Any, requirement_id: str) -> dict[str, Any]:
    read_store = requirement_read_store(current_store)
    requirement = read_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    return requirement


def get_requirement_full_chain_response(
    *,
    current_store: Any,
    requirement_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    read_store = requirement_read_store(current_store)
    requirement = read_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    return requirement_full_chain_payload(read_store, requirement, user=user)


def requirement_full_chain_payload(
    current_store: Any,
    requirement: dict[str, Any],
    *,
    user: dict[str, Any],
) -> dict[str, Any]:
    requirement_id = str(requirement["id"])
    product = _read_memory_dict(current_store, "products").get(
        str(requirement.get("product_id"))
    ) or {}
    version_id = requirement.get("version_id")
    iteration_version = (
        _read_memory_dict(current_store, "product_versions").get(str(version_id))
        if version_id is not None
        else None
    )
    tasks = sort_by_lifecycle_time(
        [
            task
            for task in _read_memory_dict(current_store, "ai_tasks").values()
            if str(task.get("requirement_id")) == requirement_id and can_read_task(user, task)
        ],
        "created_at",
        "updated_at",
    )
    task_ids = {str(task["id"]) for task in tasks}
    review_ids = {
        str(review_id)
        for task in tasks
        for review_id in task.get("review_ids", [])
    }
    reviews = sort_by_lifecycle_time(
        [
            review
            for review in _read_memory_dict(current_store, "human_reviews").values()
            if str(review.get("ai_task_id")) in task_ids or str(review.get("id")) in review_ids
        ],
        "created_at",
        "decided_at",
        "updated_at",
    )
    code_review_report_ids = {
        str(task.get("code_review_report_id"))
        for task in tasks
        if task.get("code_review_report_id")
    }
    code_review_reports = sort_by_lifecycle_time(
        [
            report
            for report in _read_memory_dict(current_store, "code_review_reports").values()
            if str(report.get("task_id")) in task_ids
            or str(report.get("id")) in code_review_report_ids
        ],
        "created_at",
        "archived_at",
        "updated_at",
    )
    git_snapshots = sort_by_lifecycle_time(
        [
            snapshot
            for snapshot in _read_memory_dict(current_store, "gitlab_mr_snapshots").values()
            if str(snapshot.get("requirement_id")) == requirement_id
            or str(snapshot.get("technical_solution_task_id")) in task_ids
        ],
        "created_at",
        "captured_at",
        "updated_at",
    )
    bugs = sort_by_lifecycle_time(
        [
            bug_summary_projection(bug, current_store)
            for bug in _read_memory_dict(current_store, "bugs").values()
            if str(bug.get("requirement_id")) == requirement_id
            or str(bug.get("related_task_id")) in task_ids
        ],
        "created_at",
        "updated_at",
    )
    knowledge_deposits = sort_by_lifecycle_time(
        [
            deposit
            for deposit in _read_memory_dict(current_store, "knowledge_deposits").values()
            if str(deposit.get("ai_task_id")) in task_ids
        ],
        "created_at",
        "updated_at",
    )
    jenkins_releases = sort_by_lifecycle_time(
        [
            release
            for release in _read_memory_dict(
                current_store,
                "jenkins_release_records",
            ).values()
            if release.get("product_id") == requirement.get("product_id")
            and (
                not requirement.get("version_id")
                or release.get("version_id") == requirement.get("version_id")
            )
        ],
        "started_at",
        "deployed_at",
        "created_at",
        "updated_at",
    )

    timeline = [
        full_chain_event(
            event_type="requirement",
            occurred_at=first_present_value(requirement, ("created_at", "updated_at")),
            subject_id=requirement_id,
            status=requirement.get("status"),
            title=f"需求：{requirement.get('title') or requirement_id}",
        )
    ]
    if iteration_version is not None:
        timeline.append(
            full_chain_event(
                event_type="iteration_version",
                occurred_at=first_present_value(
                    iteration_version,
                    ("start_date", "planned_release_at", "created_at", "updated_at"),
                )
                or first_present_value(requirement, ("created_at", "updated_at")),
                subject_id=str(iteration_version["id"]),
                status=iteration_version.get("status"),
                title=(
                    f"迭代版本：{iteration_version.get('name') or iteration_version.get('code')}"
                ),
            )
        )
    timeline.extend(
        full_chain_event(
            event_type="ai_task",
            occurred_at=first_present_value(task, ("created_at", "updated_at")),
            subject_id=str(task["id"]),
            status=task.get("status"),
            title=f"AI 任务：{task.get('title') or task['id']}",
            metadata={"task_type": task.get("task_type")},
        )
        for task in tasks
    )
    timeline.extend(
        full_chain_event(
            event_type="review",
            occurred_at=first_present_value(review, ("decided_at", "created_at", "updated_at")),
            subject_id=str(review["id"]),
            status=review.get("status"),
            title=f"人工确认：{review.get('review_type') or review['id']}",
            metadata={"ai_task_id": review.get("ai_task_id")},
        )
        for review in reviews
    )
    timeline.extend(
        full_chain_event(
            event_type="git_snapshot",
            occurred_at=first_present_value(snapshot, ("captured_at", "created_at", "updated_at")),
            subject_id=str(snapshot["id"]),
            status=snapshot.get("status"),
            title=f"PR/MR 快照：{full_chain_git_snapshot_ref(snapshot)}",
            metadata={"repository_id": snapshot.get("repository_id")},
        )
        for snapshot in git_snapshots
    )
    timeline.extend(
        full_chain_event(
            event_type="code_review_report",
            occurred_at=first_present_value(report, ("archived_at", "created_at", "updated_at")),
            subject_id=str(report["id"]),
            status=report.get("status"),
            title=compact_lifecycle_title(
                "代码评审",
                str(report["id"]),
                report.get("title"),
            ),
            metadata={
                "risk_level": report.get("risk_level"),
                "summary": report.get("summary"),
                "task_id": report.get("task_id"),
            },
        )
        for report in code_review_reports
    )
    timeline.extend(
        full_chain_event(
            event_type="bug",
            occurred_at=first_present_value(bug, ("created_at", "updated_at")),
            subject_id=str(bug["id"]),
            status=bug.get("status"),
            title=f"Bug：{bug.get('title') or bug['id']}",
            metadata={"severity": bug.get("severity"), "source": bug.get("source")},
        )
        for bug in bugs
    )
    timeline.extend(
        full_chain_event(
            event_type="jenkins_release",
            occurred_at=first_present_value(
                release,
                ("deployed_at", "started_at", "created_at", "updated_at"),
            ),
            subject_id=str(release["id"]),
            status=release.get("status"),
            title=f"发布：{release.get('job_name') or release.get('build_id') or release['id']}",
            metadata={"environment": release.get("environment")},
        )
        for release in jenkins_releases
    )
    timeline.extend(
        full_chain_event(
            event_type="knowledge_deposit",
            occurred_at=first_present_value(deposit, ("created_at", "updated_at")),
            subject_id=str(deposit["id"]),
            status=deposit.get("status"),
            title=f"知识沉淀：{deposit.get('title') or deposit['id']}",
            metadata={"ai_task_id": deposit.get("ai_task_id")},
        )
        for deposit in knowledge_deposits
    )
    timeline.sort(key=lambda item: (item["occurred_at"], item["type"], item["subject_id"]))

    return {
        "status": "available",
        "requirement": requirement_summary_projection(requirement, current_store),
        "product": current_store.snapshot(product) if product else None,
        "iteration_version": (
            current_store.snapshot(iteration_version)
            if iteration_version is not None
            else None
        ),
        "ai_tasks": [task_summary_projection(task, current_store) for task in tasks],
        "reviews": current_store.snapshot(reviews),
        "git_snapshots": current_store.snapshot(git_snapshots),
        "code_review_reports": current_store.snapshot(code_review_reports),
        "bugs": current_store.snapshot(bugs),
        "jenkins_releases": current_store.snapshot(jenkins_releases),
        "knowledge_deposits": current_store.snapshot(knowledge_deposits),
        "timeline": timeline,
        "summary": {
            "ai_tasks": len(tasks),
            "reviews": len(reviews),
            "git_snapshots": len(git_snapshots),
            "code_review_reports": len(code_review_reports),
            "bugs": len(bugs),
            "jenkins_releases": len(jenkins_releases),
            "knowledge_deposits": len(knowledge_deposits),
            "timeline_events": len(timeline),
        },
    }
