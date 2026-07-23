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
    build_audit_event,
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

_WORK_ITEM_TASK_TYPES = {
    "automated_testing",
    "code_review",
    "development_planning",
    "post_release_analysis",
    "product_detail_design",
    "release_readiness",
    "technical_solution",
}


def _collaboration_record(
    current_store: Any,
    collection_name: str,
    record_id: str,
) -> dict[str, Any] | None:
    """Read one frozen collaboration record without falling back to mutable policy rows."""
    repository = getattr(current_store, "repository", None)
    method_name = {
        "rd_collaboration_runs": "get_rd_collaboration_run",
        "rd_executor_profiles": "get_rd_executor_profile",
        "rd_run_seats": "get_rd_run_seat",
        "rd_task_executor_policy_snapshots": "get_rd_policy_snapshot",
        "rd_work_items": "get_rd_work_item",
    }.get(collection_name)
    loader = getattr(repository, method_name, None) if method_name else None
    loaded = loader(record_id) if callable(loader) else None
    if isinstance(loaded, dict):
        return dict(loaded)
    records = getattr(current_store, collection_name, {})
    record = records.get(record_id) if isinstance(records, dict) else None
    return dict(record) if isinstance(record, dict) else None


def _work_item_task_type(work_item: dict[str, Any]) -> str:
    task_type = str(work_item.get("task_type") or work_item.get("work_item_type") or "").strip()
    if task_type in _WORK_ITEM_TASK_TYPES:
        return task_type
    # Plans that predate explicit task types use implementation as their
    # canonical coding work item.  It remains governed by the frozen strategy.
    if task_type in {"", "implementation", "coding"}:
        return "development_planning"
    raise api_error(409, "RD_WORK_ITEM_NOT_READY", "Work item has no supported AI task type")


def create_ai_task_for_work_item(
    current_store: Any,
    *,
    collaboration_run_id: str,
    work_item_id: str,
    persist: bool = True,
) -> dict[str, Any]:
    """Create the one AI task owned by a ready AI collaboration work item.

    This is intentionally a domain-only entry point: public task creation can
    never supply these foreign keys or choose a different employee/executor.
    The task stores an immutable execution provenance copied from the frozen
    run seat and strategy snapshot, rather than resolving current policy data.
    """
    run = _collaboration_record(current_store, "rd_collaboration_runs", collaboration_run_id)
    work_item = _collaboration_record(current_store, "rd_work_items", work_item_id)
    if run is None or work_item is None or work_item.get("collaboration_run_id") != run.get("id"):
        raise api_error(404, "NOT_FOUND", "Collaboration work item was not found")
    if run.get("status") not in {"running", "integrating", "verifying"}:
        raise api_error(409, "RD_WORK_ITEM_NOT_READY", "Collaboration run is not dispatchable")
    if work_item.get("status") not in {"ready", "rework_required"}:
        raise api_error(
            409,
            "RD_WORK_ITEM_NOT_READY",
            "Work item is not ready for AI task creation",
        )

    owner = _collaboration_record(
        current_store,
        "rd_run_seats",
        str(work_item.get("owner_seat_id") or ""),
    )
    if (
        owner is None
        or owner.get("collaboration_run_id") != run["id"]
        or owner.get("status") != "active"
        or owner.get("subject_type") != "ai_employee"
        or not owner.get("ai_employee_id")
        or not owner.get("executor_profile_id")
    ):
        raise api_error(
            409,
            "RD_ROLE_ASSIGNMENT_REQUIRED",
            "AI work item requires an active frozen AI employee and executor seat",
        )
    executor_profile = _collaboration_record(
        current_store,
        "rd_executor_profiles",
        str(owner["executor_profile_id"]),
    )
    strategy_snapshot = _collaboration_record(
        current_store,
        "rd_task_executor_policy_snapshots",
        str(run.get("strategy_snapshot_id") or ""),
    )
    if executor_profile is None or executor_profile.get("status") != "active":
        raise api_error(409, "RD_EXECUTOR_UNAVAILABLE", "Frozen executor profile is unavailable")
    if strategy_snapshot is None or not isinstance(strategy_snapshot.get("payload_json"), dict):
        raise api_error(
            409,
            "RD_EXECUTION_POLICY_REQUIRED",
            "Frozen strategy snapshot is unavailable",
        )

    write_store = task_workflow_write_store(current_store)
    existing = next(
        (
            task
            for task in write_store.ai_tasks.values()
            if task.get("collaboration_run_id") == run["id"]
            and task.get("work_item_id") == work_item["id"]
            and task.get("status") != "cancelled"
        ),
        None,
    )
    if existing is not None:
        requirement_id = str(work_item.get("requirement_id") or "").strip()
        requirement = write_store.requirements.get(requirement_id)
        if requirement is None:
            raise api_error(
                409,
                "RD_WORK_ITEM_NOT_READY",
                "Work item does not reference an active requirement",
            )
        return {
            "task": write_store.snapshot(existing),
            "requirement": write_store.snapshot(requirement),
            "idempotent_replay": True,
        }

    requirement_id = str(work_item.get("requirement_id") or "").strip()
    requirement = write_store.requirements.get(requirement_id)
    if requirement is None:
        raise api_error(
            409,
            "RD_WORK_ITEM_NOT_READY",
            "Work item does not reference an active requirement",
        )
    if requirement.get("product_id") != run.get("product_id") or requirement.get(
        "version_id"
    ) != run.get("product_version_id"):
        raise api_error(
            409,
            "RD_WORK_ITEM_NOT_READY",
            "Work item requirement scope is no longer valid",
        )

    now = datetime.now(UTC).isoformat()
    task_id = write_store.new_id("task")
    task_type = _work_item_task_type(work_item)
    frozen_context = {
        "collaboration_run_id": run["id"],
        "work_item_id": work_item["id"],
        "owner_seat_id": owner["id"],
        "reviewer_seat_id": work_item.get("reviewer_seat_id"),
        "ai_employee_id": owner["ai_employee_id"],
        "executor_profile_id": owner["executor_profile_id"],
        "executor_type": executor_profile.get("executor_type"),
        "runner_id": executor_profile.get("runner_id"),
        "strategy_snapshot_id": strategy_snapshot["id"],
        "strategy_policy_id": strategy_snapshot.get("policy_id"),
        "strategy_policy_version": strategy_snapshot.get("policy_version"),
        "strategy_schema_version": strategy_snapshot.get("schema_version"),
        "strategy_content_hash": strategy_snapshot.get("content_hash"),
        "work_item_version": int(work_item.get("version") or 1),
    }
    task = {
        "id": task_id,
        "brain_app_id": run.get("brain_app_id", DEFAULT_BRAIN_APP_ID),
        "task_type": task_type,
        "title": str(work_item.get("title") or work_item["id"]),
        "status": "draft",
        "requirement_id": requirement["id"],
        "product_id": run["product_id"],
        "version_id": run["product_version_id"],
        "collaboration_run_id": run["id"],
        "work_item_id": work_item["id"],
        "module_code": requirement.get("module_code"),
        "requirement_snapshot": write_store.snapshot(requirement),
        "product_context": product_context(write_store, requirement),
        "input_json": {
            "work_item_input_contract": write_store.snapshot(work_item.get("input_contract") or {}),
            "work_item_output_contract": write_store.snapshot(
                work_item.get("output_contract") or {}
            ),
            "acceptance_criteria": write_store.snapshot(work_item.get("acceptance_criteria") or []),
            "rd_collaboration": frozen_context,
        },
        "output_json": None,
        "review_ids": [],
        "graph_run_ids": [],
        "current_step": "draft",
        "created_by": str(run.get("created_by") or "system"),
        "created_at": now,
        "updated_at": now,
    }
    requirement = {
        **requirement,
        "task_ids": [*list(requirement.get("task_ids") or []), task_id],
    }
    if getattr(write_store, "repository", None) is None:
        write_store.ai_tasks[task_id] = task
        write_store.requirements[requirement["id"]] = requirement
    audit_event_factory = (
        build_audit_event if uses_repository_context(write_store) else record_audit_event
    )
    audit_event = audit_event_factory(
        write_store,
        event_type="rd_work_item.ai_task_created",
        actor_id="system",
        ai_task_id=task_id,
        subject_type="rd_work_item",
        subject_id=work_item["id"],
        payload={
            "ai_employee_id": owner["ai_employee_id"],
            "executor_profile_id": owner["executor_profile_id"],
            "strategy_snapshot_id": strategy_snapshot["id"],
        },
    )
    if persist:
        save_requirement_and_ai_task_records(
            write_store,
            requirement=requirement,
            task=task,
            audit_event=audit_event,
        )
    return {
        "task": task,
        "requirement": requirement,
        "creation_audit_event": audit_event,
        "idempotent_replay": False,
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
