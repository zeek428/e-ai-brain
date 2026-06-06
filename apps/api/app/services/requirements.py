from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_roles
from app.core.store import DEFAULT_BRAIN_APP_ID
from app.services.requirement_listing import (
    list_requirements_response,
    requirement_summary_projection,
)
from app.services.task_workflow_context import task_workflow_write_store
from app.services.version_status import (
    canonical_requirement_status,
    validate_requirement_version,
)

REQUIREMENT_CLOSABLE_STATUSES = {
    "approved",
    "planned",
    "rejected",
    "ready_for_dev",
    "designing",
    "developing",
    "code_reviewing",
    "testing",
    "released",
    "task_created",
    "closed",
    "cancelled",
}
REQUIREMENT_BATCH_SCHEDULABLE_STATUSES = {"approved", "planned"}
REQUIREMENT_STATUS_AFTER_TASK_CREATED = {
    "automated_testing": "testing",
    "code_review": "code_reviewing",
    "development_planning": "developing",
    "post_release_analysis": "released",
    "product_detail_design": "designing",
    "release_readiness": "ready_for_release",
    "technical_solution": "ready_for_dev",
}

__all__ = [
    "REQUIREMENT_BATCH_SCHEDULABLE_STATUSES",
    "REQUIREMENT_CLOSABLE_STATUSES",
    "REQUIREMENT_STATUS_AFTER_TASK_CREATED",
    "create_requirement_result",
    "delete_requirement_result",
    "generate_product_detail_design_task",
    "generate_requirement_task_result",
    "list_requirements_response",
    "patch_requirement_result",
    "public_git_repository",
    "record_audit_event",
    "requirement_product_context",
    "requirement_summary_projection",
    "requirement_write_store",
    "save_audit_event",
    "save_requirement_and_ai_task_records",
    "save_requirement_record",
    "set_requirement_status",
    "uses_repository_context",
]


def uses_repository_context(current_store: Any) -> bool:
    return getattr(current_store, "repository", None) is not None


def ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def record_audit_event(
    current_store: Any,
    *,
    actor_id: str,
    event_type: str,
    ai_task_id: str | None = None,
    payload: dict[str, Any] | None = None,
    subject_id: str | None = None,
    subject_type: str | None = None,
) -> dict[str, Any]:
    if not uses_repository_context(current_store):
        return current_store.audit(
            event_type=event_type,
            actor_id=actor_id,
            ai_task_id=ai_task_id,
            subject_type=subject_type,
            subject_id=subject_id,
            payload=payload,
        )
    return {
        "actor_id": actor_id,
        "ai_task_id": ai_task_id,
        "created_at": datetime.now(UTC).isoformat(),
        "event_type": event_type,
        "id": current_store.new_id("audit"),
        "payload": payload or {},
        "sequence": len(getattr(current_store, "audit_events", [])) + 1,
        "subject_id": subject_id,
        "subject_type": subject_type,
    }


def save_requirement_record(
    current_store: Any,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_requirement_record", None)
    if callable(save_record):
        save_record(record, audit_event=audit_event)


def save_requirement_and_ai_task_records(
    current_store: Any,
    *,
    audit_event: dict[str, Any] | None = None,
    requirement: dict[str, Any],
    task: dict[str, Any],
) -> None:
    repository = getattr(current_store, "repository", None)
    save_records = getattr(repository, "save_requirement_and_ai_task_records", None)
    if callable(save_records):
        save_records(requirement=requirement, task=task, audit_event=audit_event)


def delete_requirement_record(
    current_store: Any,
    record_id: str,
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    delete_record = getattr(repository, "delete_requirement_record", None)
    if callable(delete_record):
        delete_record(record_id, audit_event=audit_event)


def save_audit_event(current_store: Any, audit_event: dict[str, Any]) -> None:
    repository = getattr(current_store, "repository", None)
    append_event = getattr(repository, "append_audit_event", None)
    if callable(append_event):
        append_event(audit_event)
        return
    save_events = getattr(repository, "save_audit_events", None)
    if callable(save_events):
        save_events({"audit_events": [audit_event]})


def requirement_write_store(current_store: Any) -> Any:
    return task_workflow_write_store(current_store)


def set_requirement_status(requirement: dict[str, Any], status: str) -> None:
    requirement["status"] = status
    requirement["updated_at"] = datetime.now(UTC).isoformat()


def public_git_repository(repository: dict[str, Any]) -> dict[str, Any]:
    public_repository = {
        key: value
        for key, value in repository.items()
        if key != "credential_ref"
    }
    public_repository["credential_ref_configured"] = bool(
        repository.get("credential_ref") or repository.get("credential_ref_configured")
    )
    return public_repository


def requirement_product_context(current_store: Any, requirement: dict[str, Any]) -> dict[str, Any]:
    product = current_store.products[requirement["product_id"]]
    version = (
        current_store.product_versions.get(requirement["version_id"])
        if requirement.get("version_id")
        else None
    )
    module = next(
        (
            item
            for item in current_store.product_modules.values()
            if item["product_id"] == product["id"]
            and item["code"] == requirement.get("module_code")
        ),
        None,
    )
    repositories = [
        public_git_repository(repository)
        for repository in current_store.product_git_repositories.values()
        if repository["product_id"] == product["id"] and repository.get("status") == "active"
    ]
    related_systems = [
        related_system
        for related_system in current_store.related_systems.values()
        if related_system.get("product_id") == product["id"]
        and related_system.get("status") == "active"
    ]
    return {
        "product": current_store.snapshot(product),
        "version": current_store.snapshot(version) if version else None,
        "module": current_store.snapshot(module) if module else None,
        "repositories": current_store.snapshot({"items": repositories, "total": len(repositories)}),
        "related_systems": current_store.snapshot(
            {"items": related_systems, "total": len(related_systems)}
        ),
    }


def create_requirement_result(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_roles(user, {"product_owner", "rd_owner"})
    title = ensure_non_blank(payload.title, "title")
    content = ensure_non_blank(payload.content, "content")
    product = current_store.products.get(payload.product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    validate_requirement_version(
        current_store,
        product_id=payload.product_id,
        version_id=payload.version_id,
    )
    if payload.module_code is not None and not any(
        module["product_id"] == payload.product_id and module["code"] == payload.module_code
        for module in current_store.product_modules.values()
    ):
        raise api_error(404, "NOT_FOUND", "Product module not found")

    requirement_id = current_store.new_id("requirement")
    requirement = {
        "assignee": user["id"],
        "brain_app_id": DEFAULT_BRAIN_APP_ID,
        "content": content,
        "created_at": datetime.now(UTC).isoformat(),
        "created_by": user["id"],
        "id": requirement_id,
        "module_code": payload.module_code,
        "priority": payload.priority,
        "product_id": payload.product_id,
        "status": "submitted",
        "task_ids": [],
        "title": title,
        "version_id": payload.version_id,
    }
    if not uses_repository_context(current_store):
        current_store.requirements[requirement_id] = requirement
    audit_event = record_audit_event(
        current_store,
        event_type="requirement.created",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    save_requirement_record(current_store, requirement, audit_event=audit_event)
    return requirement


def patch_requirement_result(
    *,
    current_store: Any,
    payload: Any,
    requirement_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_roles(user, {"product_owner", "rd_owner"})
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    current_status = canonical_requirement_status(requirement.get("status"))
    if current_status not in {"approved", "planned", "rejected", "submitted"}:
        raise api_error(409, "REQUIREMENT_STATE_INVALID", "Requirement cannot be edited")

    updates = payload.model_dump(exclude_unset=True)
    if "title" in updates:
        updates["title"] = ensure_non_blank(updates["title"], "title")
    if "content" in updates:
        updates["content"] = ensure_non_blank(updates["content"], "content")

    next_product_id = updates.get("product_id", requirement["product_id"])
    next_version_id = updates.get("version_id", requirement["version_id"])
    product = current_store.products.get(next_product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    validate_requirement_version(
        current_store,
        product_id=next_product_id,
        version_id=next_version_id,
    )

    next_module_code = updates.get("module_code", requirement.get("module_code"))
    if next_module_code is not None and not any(
        module["product_id"] == next_product_id and module["code"] == next_module_code
        for module in current_store.product_modules.values()
    ):
        raise api_error(404, "NOT_FOUND", "Product module not found")

    requirement = {**requirement, **updates}
    if current_status in {"approved", "planned"} and "version_id" in updates:
        requirement["status"] = "planned" if updates["version_id"] else "approved"
    requirement["updated_at"] = datetime.now(UTC).isoformat()
    if not uses_repository_context(current_store):
        current_store.requirements[requirement_id] = requirement
    audit_event = record_audit_event(
        current_store,
        event_type="requirement.updated",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    save_requirement_record(current_store, requirement, audit_event=audit_event)
    return requirement


def delete_requirement_result(
    *,
    current_store: Any,
    requirement_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_roles(user, {"product_owner", "rd_owner"})
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    if requirement.get("task_ids"):
        raise api_error(409, "RESOURCE_IN_USE", "Requirement already has tasks")
    if not uses_repository_context(current_store):
        del current_store.requirements[requirement_id]
    audit_event = record_audit_event(
        current_store,
        event_type="requirement.deleted",
        actor_id=user["id"],
        subject_type="requirement",
        subject_id=requirement_id,
    )
    delete_requirement_record(current_store, requirement_id, audit_event=audit_event)
    return {"deleted": True, "id": requirement_id}


def generate_product_detail_design_task(
    current_store: Any,
    *,
    audit_payload: dict[str, Any] | None = None,
    now: str,
    requirement: dict[str, Any],
    requirement_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    task_id = current_store.new_id("task")
    task = {
        "brain_app_id": requirement.get("brain_app_id", DEFAULT_BRAIN_APP_ID),
        "created_at": now,
        "created_by": user["id"],
        "current_step": "draft",
        "graph_run_ids": [],
        "id": task_id,
        "input_json": {},
        "module_code": requirement.get("module_code"),
        "output_json": None,
        "product_context": requirement_product_context(current_store, requirement),
        "product_id": requirement["product_id"],
        "requirement_id": requirement_id,
        "requirement_snapshot": current_store.snapshot(requirement),
        "review_ids": [],
        "status": "draft",
        "task_type": "product_detail_design",
        "title": f"产品详细设计：{requirement['title']}",
        "updated_at": now,
        "version_id": requirement["version_id"],
    }
    updated_requirement = {
        **requirement,
        "task_ids": [*requirement.get("task_ids", []), task_id],
    }
    next_status = REQUIREMENT_STATUS_AFTER_TASK_CREATED.get(task["task_type"])
    if next_status:
        set_requirement_status(updated_requirement, next_status)
    if not uses_repository_context(current_store):
        current_store.ai_tasks[task_id] = task
        current_store.requirements[requirement_id] = updated_requirement
    audit_payload_value = {
        "brain_app_code": task["brain_app_id"],
        "task_type": "product_detail_design",
    }
    if audit_payload:
        audit_payload_value.update(audit_payload)
    audit_event = record_audit_event(
        current_store,
        event_type="ai_task.created",
        actor_id=user["id"],
        ai_task_id=task_id,
        subject_type="ai_task",
        subject_id=task_id,
        payload=audit_payload_value,
    )
    save_requirement_and_ai_task_records(
        current_store,
        requirement=updated_requirement,
        task=task,
        audit_event=audit_event,
    )
    return {
        "requirement_id": requirement_id,
        "task_id": task_id,
        "task_status": task["status"],
        "task_type": task["task_type"],
    }


def generate_requirement_task_result(
    *,
    current_store: Any,
    requirement_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_roles(user, {"product_owner", "rd_owner"})
    requirement = current_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")
    if canonical_requirement_status(requirement.get("status")) != "planned":
        raise api_error(
            409,
            "REQUIREMENT_STATE_INVALID",
            "Only planned requirements can generate tasks",
        )
    generated = generate_product_detail_design_task(
        current_store,
        now=datetime.now(UTC).isoformat(),
        requirement=requirement,
        requirement_id=requirement_id,
        user=user,
    )
    return {
        "task_id": generated["task_id"],
        "task_type": generated["task_type"],
        "task_status": generated["task_status"],
    }
