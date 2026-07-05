from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_any_permission_or_roles
from app.core.store import DEFAULT_BRAIN_APP_ID
from app.services.task_contexts import (
    ensure_confirmed_release_readiness_task,
    ensure_confirmed_technical_solution_task,
    ensure_git_snapshot_context,
    ensure_task_matches_requirement,
    post_release_analysis_context,
    product_context,
    raise_git_context_mismatch,
    release_readiness_context,
)
from app.services.task_persistence_helpers import (
    record_audit_event,
    save_requirement_and_ai_task_records,
    uses_repository_context,
)
from app.services.task_review_artifacts import set_requirement_status
from app.services.task_workflow_context import task_workflow_write_store
from app.services.version_status import canonical_requirement_status

TECHNICAL_SOLUTION_FOLLOWUP_TASK_TYPES = {
    "development_planning",
    "automated_testing",
    "release_readiness",
}
RELEASE_READINESS_FOLLOWUP_TASK_TYPES = {"post_release_analysis"}
REQUIREMENT_TASK_CREATABLE_STATUSES = {
    "code_reviewing",
    "designing",
    "developing",
    "planned",
    "ready_for_dev",
    "ready_for_release",
    "released",
    "testing",
}
REQUIREMENT_STATUS_AFTER_TASK_CREATED = {
    "automated_testing": "testing",
    "code_review": "code_reviewing",
    "development_planning": "developing",
    "post_release_analysis": "released",
    "product_detail_design": "designing",
    "release_readiness": "ready_for_release",
    "technical_solution": "ready_for_dev",
}


def create_ai_task_response(
    *,
    current_store: Any,
    input_payload: dict[str, Any],
    requirement_id: str,
    task_type: str,
    title: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    write_store = task_workflow_write_store(current_store)
    requirement = write_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(404, "NOT_FOUND", "Requirement not found")

    input_json = write_store.snapshot(input_payload)
    if task_type == "technical_solution":
        require_any_permission_or_roles(user, {"task.create"}, {"product_owner", "rd_owner"})
        design_task_id = input_payload.get("product_detail_design_task_id")
        design_task = write_store.ai_tasks.get(str(design_task_id))
        if (
            design_task is None
            or design_task["task_type"] != "product_detail_design"
            or design_task["status"] != "completed"
        ):
            raise api_error(
                400,
                "PRODUCT_DETAIL_DESIGN_NOT_CONFIRMED",
                "technical_solution requires a confirmed product detail design task",
            )
        ensure_task_matches_requirement(
            design_task,
            requirement,
            source_label="Product detail design",
        )
    elif task_type in TECHNICAL_SOLUTION_FOLLOWUP_TASK_TYPES:
        require_any_permission_or_roles(user, {"task.create"}, {"product_owner", "rd_owner"})
        technical_solution = ensure_confirmed_technical_solution_task(
            write_store,
            requirement=requirement,
            technical_solution_task_id=input_payload.get("technical_solution_task_id"),
        )
        if task_type == "release_readiness":
            input_json.update(
                release_readiness_context(
                    write_store,
                    requirement=requirement,
                    technical_solution=technical_solution,
                )
            )
    elif task_type in RELEASE_READINESS_FOLLOWUP_TASK_TYPES:
        require_any_permission_or_roles(user, {"task.create"}, {"product_owner", "rd_owner"})
        release_readiness = ensure_confirmed_release_readiness_task(
            write_store,
            requirement=requirement,
            release_readiness_task_id=input_payload.get("release_readiness_task_id"),
        )
        input_json.update(
            post_release_analysis_context(
                write_store,
                requirement=requirement,
                release_readiness=release_readiness,
            )
        )
    elif task_type == "code_review":
        require_any_permission_or_roles(
            user,
            {"gitlab.review", "task.create"},
            {"reviewer", "rd_owner"},
        )
        snapshot_id = input_payload.get("gitlab_mr_snapshot_id")
        snapshot = write_store.gitlab_mr_snapshots.get(str(snapshot_id))
        if snapshot is None:
            raise api_error(400, "GITLAB_MR_SNAPSHOT_REQUIRED", "code_review requires MR snapshot")
        if snapshot["requirement_id"] != requirement["id"]:
            raise_git_context_mismatch(
                "code_review requirement must match the GitLab MR snapshot requirement"
            )
        if snapshot["product_id"] != requirement["product_id"]:
            raise_git_context_mismatch(
                "code_review product must match the GitLab MR snapshot product"
            )
        technical_solution = write_store.ai_tasks.get(snapshot["technical_solution_task_id"])
        if (
            technical_solution is None
            or technical_solution["task_type"] != "technical_solution"
            or technical_solution["status"] != "completed"
        ):
            raise api_error(
                400,
                "TECHNICAL_SOLUTION_NOT_CONFIRMED",
                "code_review requires a confirmed technical solution",
            )
        ensure_git_snapshot_context(
            repository=write_store.product_git_repositories[snapshot["repository_id"]],
            requirement=requirement,
            technical_solution=technical_solution,
        )
    else:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported task_type")

    if canonical_requirement_status(requirement.get("status")) not in (
        REQUIREMENT_TASK_CREATABLE_STATUSES
    ):
        raise api_error(
            409,
            "REQUIREMENT_STATE_INVALID",
            "Requirement must be in delivery before creating AI tasks",
        )

    now = datetime.now(UTC).isoformat()
    task_id = write_store.new_id("task")
    task = {
        "id": task_id,
        "brain_app_id": requirement.get("brain_app_id", DEFAULT_BRAIN_APP_ID),
        "task_type": task_type,
        "title": title,
        "status": "draft",
        "requirement_id": requirement["id"],
        "product_id": requirement["product_id"],
        "version_id": requirement["version_id"],
        "module_code": requirement.get("module_code"),
        "requirement_snapshot": write_store.snapshot(requirement),
        "product_context": product_context(write_store, requirement),
        "input_json": input_json,
        "output_json": None,
        "review_ids": [],
        "graph_run_ids": [],
        "current_step": "draft",
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now,
    }
    updated_task_ids = list(requirement.get("task_ids", []))
    if task_id not in updated_task_ids:
        updated_task_ids.append(task_id)
    updated_requirement = {
        **requirement,
        "task_ids": updated_task_ids,
    }
    next_status = REQUIREMENT_STATUS_AFTER_TASK_CREATED.get(task["task_type"])
    if next_status:
        set_requirement_status(updated_requirement, next_status)
    if not uses_repository_context(write_store):
        write_store.ai_tasks[task_id] = task
        write_store.requirements[requirement["id"]] = updated_requirement
    audit_event = record_audit_event(
        write_store,
        event_type="ai_task.created",
        actor_id=user["id"],
        ai_task_id=task_id,
        subject_type="ai_task",
        subject_id=task_id,
        payload={
            "brain_app_code": task["brain_app_id"],
            "task_type": task_type,
        },
    )
    save_requirement_and_ai_task_records(
        write_store,
        requirement=updated_requirement,
        task=task,
        audit_event=audit_event,
    )
    return task
