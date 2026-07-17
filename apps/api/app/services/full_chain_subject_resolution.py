from __future__ import annotations

from typing import Any

from app.api.deps import api_error
from app.services.lifecycle_subjects import lifecycle_subject_tasks


def _first_present_value(item: dict[str, Any], fields: tuple[str, ...]) -> str:
    for field in fields:
        value = item.get(field)
        if value is not None and str(value).strip():
            return str(value)
    return ""


def _sort_by_lifecycle_time(items: list[dict[str, Any]], *fields: str) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (_first_present_value(item, fields), str(item.get("id") or "")),
    )


def read_memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, dict) else {}


def latest_requirement_id_for_version(current_store: Any, version_id: Any) -> str | None:
    if version_id is None:
        return None
    version_requirements = _sort_by_lifecycle_time(
        [
            requirement
            for requirement in read_memory_dict(current_store, "requirements").values()
            if str(requirement.get("version_id")) == str(version_id)
        ],
        "updated_at",
        "created_at",
    )
    if not version_requirements:
        return None
    return str(version_requirements[-1]["id"])


def _requirement_id_from_task(task: dict[str, Any] | None) -> str | None:
    if task is not None and task.get("requirement_id"):
        return str(task["requirement_id"])
    return None


def _code_inspection_report_tasks(
    current_store: Any,
    report: dict[str, Any],
) -> list[dict[str, Any]]:
    tasks = [
        task
        for task_id in report.get("created_task_ids", [])
        if (task := read_memory_dict(current_store, "ai_tasks").get(str(task_id))) is not None
    ]
    for bug_id in report.get("created_bug_ids", []):
        bug = read_memory_dict(current_store, "bugs").get(str(bug_id))
        if bug is None:
            continue
        if bug.get("related_task_id"):
            task = read_memory_dict(current_store, "ai_tasks").get(str(bug["related_task_id"]))
            if task is not None:
                tasks.append(task)
        elif bug.get("requirement_id"):
            tasks.extend(
                task
                for task in read_memory_dict(current_store, "ai_tasks").values()
                if str(task.get("requirement_id")) == str(bug["requirement_id"])
            )
    if tasks:
        return list({str(task["id"]): task for task in tasks if task.get("id")}.values())
    return [
        task
        for task in read_memory_dict(current_store, "ai_tasks").values()
        if task.get("product_id") == report.get("product_id")
    ]


def resolve_code_inspection_report_requirement_id(
    current_store: Any,
    report: dict[str, Any],
) -> str | None:
    requirements = read_memory_dict(current_store, "requirements")
    for requirement_id in report.get("created_requirement_ids") or []:
        if str(requirement_id) in requirements:
            return str(requirement_id)
    for bug_id in report.get("created_bug_ids") or []:
        bug = read_memory_dict(current_store, "bugs").get(str(bug_id))
        if bug is not None and bug.get("requirement_id"):
            return str(bug["requirement_id"])
    for task_id in report.get("created_task_ids") or []:
        task_requirement_id = _requirement_id_from_task(
            read_memory_dict(current_store, "ai_tasks").get(str(task_id)),
        )
        if task_requirement_id is not None:
            return task_requirement_id
    report_key = (str(report.get("repository_id") or ""), str(report.get("branch") or ""))
    if all(report_key):
        for branch_config in read_memory_dict(
            current_store,
            "product_version_branch_configs",
        ).values():
            if str(branch_config.get("product_id") or "") != str(report.get("product_id") or ""):
                continue
            branch_key = (
                str(branch_config.get("repository_id") or ""),
                str(branch_config.get("working_branch") or ""),
            )
            if branch_key != report_key:
                continue
            requirement_id = latest_requirement_id_for_version(
                current_store,
                branch_config.get("version_id"),
            )
            if requirement_id is not None:
                return requirement_id
    for task in _code_inspection_report_tasks(current_store, report):
        task_requirement_id = _requirement_id_from_task(task)
        if task_requirement_id is not None:
            return task_requirement_id
    return None


def resolve_requirement_id_from_full_chain_subject(
    current_store: Any,
    *,
    subject_type: str,
    subject_id: str,
) -> str:
    normalized_type = subject_type.strip()
    normalized_id = subject_id.strip()
    if not normalized_type or not normalized_id:
        raise api_error(400, "VALIDATION_ERROR", "subject_type and subject_id are required")
    if normalized_type == "requirement":
        if read_memory_dict(current_store, "requirements").get(normalized_id) is None:
            raise api_error(404, "NOT_FOUND", "Requirement not found")
        return normalized_id
    if normalized_type in {"product_version", "iteration_version"}:
        if read_memory_dict(current_store, "product_versions").get(normalized_id) is None:
            raise api_error(404, "NOT_FOUND", "Iteration version not found")
        requirement_id = latest_requirement_id_for_version(current_store, normalized_id)
        if requirement_id is None:
            raise api_error(
                404,
                "NO_REQUIREMENT_CONTEXT",
                "Iteration version has no requirements to display in full chain",
            )
        return requirement_id
    if normalized_type in {"branch_config", "product_version_branch_config"}:
        branch_config = read_memory_dict(
            current_store,
            "product_version_branch_configs",
        ).get(normalized_id)
        if branch_config is None:
            raise api_error(404, "NOT_FOUND", "Branch config not found")
        requirement_id = latest_requirement_id_for_version(
            current_store,
            branch_config.get("version_id"),
        )
        if requirement_id is None:
            raise api_error(
                404,
                "NO_REQUIREMENT_CONTEXT",
                "Branch config version has no requirements to display in full chain",
            )
        return requirement_id
    if normalized_type == "code_inspection_report":
        report = read_memory_dict(current_store, "code_inspection_reports").get(normalized_id)
        if report is None:
            raise api_error(404, "NOT_FOUND", "Code inspection report not found")
        requirement_id = resolve_code_inspection_report_requirement_id(current_store, report)
        if requirement_id is not None:
            return requirement_id
    if normalized_type in {"deployment", "deployment_request"}:
        deployment = read_memory_dict(current_store, "deployment_requests").get(normalized_id)
        if deployment is None:
            raise api_error(404, "NOT_FOUND", "Deployment request not found")
        requirement_ids = [str(item) for item in deployment.get("requirement_ids", []) if item]
        if requirement_ids:
            requirement_id = requirement_ids[0]
            if read_memory_dict(current_store, "requirements").get(requirement_id) is None:
                raise api_error(404, "NOT_FOUND", "Requirement not found")
            return requirement_id
        requirement_id = latest_requirement_id_for_version(
            current_store, deployment.get("version_id")
        )
        if requirement_id is not None:
            return requirement_id
    tasks = lifecycle_subject_tasks(
        current_store,
        subject_type=normalized_type,
        subject_id=normalized_id,
    )
    for task in tasks:
        task_requirement_id = _requirement_id_from_task(task)
        if task_requirement_id is not None:
            return task_requirement_id
    raise api_error(
        404,
        "NO_REQUIREMENT_CONTEXT",
        "Subject is not linked to a requirement full chain",
    )
