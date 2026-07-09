from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_any_permission_or_roles
from app.services.bugs import save_bug_record
from app.services.operational_records import (
    ensure_enum,
    ensure_non_blank,
    parse_optional_time,
    read_memory_dict,
    read_memory_records,
    record_audit_event,
)
from app.services.product_scope import product_scope_filter, require_product_scope
from app.services.requirements import save_requirement_record, set_requirement_status
from app.services.task_workflow_context import task_workflow_write_store

DEPLOYMENT_REQUEST_STATUSES = {
    "approved",
    "cancelled",
    "deploying",
    "draft",
    "failed",
    "pending_ops",
    "rolled_back",
    "succeeded",
}
DEPLOYMENT_RUN_STATUSES = {"canceled", "failed", "rolled_back", "running", "success"}
DEPLOYMENT_RESULT_STATUSES = {"failed", "rolled_back", "success"}
DEPLOYMENT_RISK_LEVELS = {"critical", "high", "low", "medium"}
DEPLOYMENT_STARTABLE_STATUSES = {"approved", "failed", "pending_ops"}
DEPLOYMENT_TERMINAL_STATUSES = {"cancelled", "rolled_back", "succeeded"}
DEPLOYMENT_ELIGIBLE_REQUIREMENT_STATUSES = {"ready_for_release", "testing"}
DEPLOYMENT_OPEN_BUG_STATUSES = {"assigned", "fixed", "needs_info", "open", "reopened", "triaged"}
DEPLOYMENT_BLOCKING_BUG_SEVERITIES = {"blocker", "critical"}


def _save_deployment_request_record(
    current_store: Any,
    record: dict[str, Any],
    *,
    audit_events: list[dict[str, Any]] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_deployment_request_record", None)
    if callable(save_record):
        save_record(record, audit_events=audit_events)
        return
    read_memory_dict(current_store, "deployment_requests")[str(record["id"])] = record


def _save_deployment_run_record(
    current_store: Any,
    record: dict[str, Any],
    *,
    audit_events: list[dict[str, Any]] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_deployment_run_record", None)
    if callable(save_record):
        save_record(record, audit_events=audit_events)
        return
    read_memory_dict(current_store, "deployment_runs")[str(record["id"])] = record


def _deployment_runs_for_request(current_store: Any, deployment_request_id: str) -> list[dict[str, Any]]:
    return [
        run
        for run in read_memory_records(current_store, "deployment_runs")
        if str(run.get("deployment_request_id")) == deployment_request_id
    ]


def _deployment_with_runs(current_store: Any, deployment: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(deployment)
    enriched["runs"] = sorted(
        _deployment_runs_for_request(current_store, str(deployment["id"])),
        key=lambda item: item.get("started_at") or item.get("created_at") or "",
        reverse=True,
    )
    return enriched


def _requirement_ids_from_payload(requirement_ids: list[str]) -> list[str]:
    normalized: list[str] = []
    for requirement_id in requirement_ids:
        normalized_id = ensure_non_blank(str(requirement_id), "requirement_ids")
        if normalized_id not in normalized:
            normalized.append(normalized_id)
    if not normalized:
        raise api_error(400, "VALIDATION_ERROR", "requirement_ids is required")
    return normalized


def _validate_deployment_context(
    current_store: Any,
    *,
    product_id: str,
    release_readiness_task_id: str | None,
    requirement_ids: list[str],
    user: dict[str, Any],
    version_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    require_product_scope(user, product_id)
    product = read_memory_dict(current_store, "products").get(product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product.get("status") != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")
    version = read_memory_dict(current_store, "product_versions").get(version_id)
    if version is None or version.get("product_id") != product_id:
        raise api_error(404, "NOT_FOUND", "Product version not found")
    if version.get("status") == "archived":
        raise api_error(400, "PRODUCT_VERSION_ARCHIVED", "Archived version cannot be used")

    requirements: list[dict[str, Any]] = []
    for requirement_id in requirement_ids:
        requirement = read_memory_dict(current_store, "requirements").get(requirement_id)
        if (
            requirement is None
            or requirement.get("product_id") != product_id
            or requirement.get("version_id") != version_id
        ):
            raise api_error(404, "NOT_FOUND", "Requirement not found")
        if requirement.get("status") not in DEPLOYMENT_ELIGIBLE_REQUIREMENT_STATUSES:
            raise api_error(
                409,
                "REQUIREMENT_NOT_READY_FOR_DEPLOYMENT",
                "Requirement is not ready for deployment",
                {"requirement_id": requirement_id, "status": requirement.get("status")},
            )
        requirements.append(requirement)

    if release_readiness_task_id:
        task = read_memory_dict(current_store, "ai_tasks").get(release_readiness_task_id)
        if (
            task is None
            or task.get("task_type") != "release_readiness"
            or task.get("status") != "completed"
            or task.get("product_id") != product_id
            or task.get("version_id") != version_id
        ):
            raise api_error(
                409,
                "RELEASE_READINESS_NOT_CONFIRMED",
                "Release readiness task is not confirmed for this product version",
            )

    blocking_bugs = [
        bug
        for bug in read_memory_records(current_store, "bugs")
        if bug.get("product_id") == product_id
        and bug.get("version_id") == version_id
        and (
            bug.get("requirement_id") in requirement_ids
            or not bug.get("requirement_id")
        )
        and bug.get("severity") in DEPLOYMENT_BLOCKING_BUG_SEVERITIES
        and bug.get("status") in DEPLOYMENT_OPEN_BUG_STATUSES
    ]
    if blocking_bugs:
        raise api_error(
            409,
            "DEPLOYMENT_BLOCKED",
            "Deployment has blocking bugs",
            {"blocking_bug_ids": [bug["id"] for bug in blocking_bugs]},
        )
    return requirements, blocking_bugs


def _deployment_gate_summary(
    *,
    requirement_count: int,
    blocking_bug_count: int,
    release_readiness_task_id: str | None,
) -> dict[str, Any]:
    return {
        "blocking_bug_count": blocking_bug_count,
        "release_readiness_task_id": release_readiness_task_id,
        "requirement_count": requirement_count,
        "status": "ready" if blocking_bug_count == 0 else "blocked",
    }


def _deployment_by_id(current_store: Any, deployment_request_id: str) -> dict[str, Any]:
    deployment = read_memory_dict(current_store, "deployment_requests").get(deployment_request_id)
    if deployment is None:
        raise api_error(404, "NOT_FOUND", "Deployment request not found")
    return deployment


def _latest_deployment_run(current_store: Any, deployment_request_id: str) -> dict[str, Any] | None:
    runs = _deployment_runs_for_request(current_store, deployment_request_id)
    if not runs:
        return None
    return sorted(
        runs,
        key=lambda item: item.get("started_at") or item.get("created_at") or "",
        reverse=True,
    )[0]


def _deployment_public_response(current_store: Any, deployment: dict[str, Any]) -> dict[str, Any]:
    return _deployment_with_runs(current_store, deployment)


def list_deployment_requests_response(
    *,
    current_store: Any,
    environment: str | None,
    product_id: str | None,
    status: str | None,
    user: dict[str, Any],
    version_id: str | None,
) -> dict[str, Any]:
    require_any_permission_or_roles(
        user,
        {"deployment.read", "devops.read"},
        {"product_owner", "rd_owner", "release_owner", "test_owner", "tester"},
    )
    ensure_enum(status, DEPLOYMENT_REQUEST_STATUSES, "status")
    write_store = task_workflow_write_store(current_store)
    scoped_product_ids = product_scope_filter(user)
    repository = getattr(current_store, "repository", None)
    list_requests = getattr(repository, "list_deployment_requests", None)
    if callable(list_requests):
        deployments = list_requests(
            environment=environment,
            product_id=product_id,
            product_scope_ids=scoped_product_ids,
            status=status,
            version_id=version_id,
        )
        run_records = {
            str(run["id"]): dict(run)
            for deployment in deployments
            for run in (
                repository.list_deployment_runs(deployment_request_id=str(deployment["id"]))
                if callable(getattr(repository, "list_deployment_runs", None))
                else []
            )
            if run.get("id") is not None
        }
        setattr(write_store, "deployment_runs", run_records)
    else:
        deployments = read_memory_records(write_store, "deployment_requests")
        if scoped_product_ids is not None:
            scoped_set = set(scoped_product_ids)
            deployments = [
                deployment
                for deployment in deployments
                if deployment.get("product_id") is not None
                and str(deployment.get("product_id")) in scoped_set
            ]
        if product_id is not None:
            deployments = [
                deployment for deployment in deployments if deployment.get("product_id") == product_id
            ]
        if version_id is not None:
            deployments = [
                deployment for deployment in deployments if deployment.get("version_id") == version_id
            ]
        if status is not None:
            deployments = [
                deployment for deployment in deployments if deployment.get("status") == status
            ]
        if environment is not None:
            deployments = [
                deployment
                for deployment in deployments
                if deployment.get("environment") == environment
            ]
    items = [
        _deployment_public_response(write_store, deployment)
        for deployment in sorted(
            deployments,
            key=lambda item: item.get("updated_at") or item.get("created_at") or "",
            reverse=True,
        )
    ]
    return {"items": items, "total": len(items)}


def create_deployment_request_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(
        user,
        {"deployment.create"},
        {"product_owner", "rd_owner", "release_owner", "test_owner"},
    )
    write_store = task_workflow_write_store(current_store)
    requirement_ids = _requirement_ids_from_payload(payload.requirement_ids)
    ensure_enum(payload.risk_level, DEPLOYMENT_RISK_LEVELS, "risk_level")
    deploy_window_start = parse_optional_time(payload.deploy_window_start, "deploy_window_start")
    deploy_window_end = parse_optional_time(payload.deploy_window_end, "deploy_window_end")
    if deploy_window_start is not None and deploy_window_end is not None:
        if deploy_window_end < deploy_window_start:
            raise api_error(400, "VALIDATION_ERROR", "deploy_window_end must be after deploy_window_start")
    release_readiness_task_id = (
        ensure_non_blank(payload.release_readiness_task_id, "release_readiness_task_id")
        if payload.release_readiness_task_id
        else None
    )
    requirements, blocking_bugs = _validate_deployment_context(
        write_store,
        product_id=payload.product_id,
        release_readiness_task_id=release_readiness_task_id,
        requirement_ids=requirement_ids,
        user=user,
        version_id=payload.version_id,
    )
    now = datetime.now(UTC).isoformat()
    deployment_id = write_store.new_id("deployment_request")
    deployment = {
        "artifact_version": payload.artifact_version,
        "assigned_ops_user": payload.assigned_ops_user,
        "commit_sha": payload.commit_sha,
        "created_at": now,
        "created_by": user["id"],
        "deploy_window_end": deploy_window_end,
        "deploy_window_start": deploy_window_start,
        "environment": ensure_non_blank(payload.environment, "environment"),
        "failure_reason": None,
        "gate_summary": _deployment_gate_summary(
            requirement_count=len(requirements),
            blocking_bug_count=len(blocking_bugs),
            release_readiness_task_id=release_readiness_task_id,
        ),
        "id": deployment_id,
        "product_id": payload.product_id,
        "release_branch": payload.release_branch,
        "release_readiness_task_id": release_readiness_task_id,
        "requirement_ids": requirement_ids,
        "risk_level": payload.risk_level,
        "rollback_plan": payload.rollback_plan,
        "status": "pending_ops",
        "title": ensure_non_blank(payload.title, "title"),
        "updated_at": now,
        "version_id": payload.version_id,
    }
    for optional_key in (
        "artifact_version",
        "assigned_ops_user",
        "commit_sha",
        "deploy_window_end",
        "deploy_window_start",
        "failure_reason",
        "release_branch",
        "release_readiness_task_id",
        "rollback_plan",
    ):
        if deployment[optional_key] is None:
            deployment.pop(optional_key)
    audit_event = record_audit_event(
        write_store,
        event_type="deployment.request.created",
        actor_id=user["id"],
        subject_type="deployment_request",
        subject_id=deployment_id,
        payload={
            "product_id": payload.product_id,
            "requirement_ids": requirement_ids,
            "version_id": payload.version_id,
        },
    )
    _save_deployment_request_record(write_store, deployment, audit_events=[audit_event])
    return _deployment_public_response(write_store, deployment)


def start_deployment_request_response(
    *,
    current_store: Any,
    deployment_request_id: str,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"deployment.execute"}, {"release_owner"})
    write_store = task_workflow_write_store(current_store)
    deployment = dict(_deployment_by_id(write_store, deployment_request_id))
    require_product_scope(user, deployment.get("product_id"))
    if deployment.get("status") not in DEPLOYMENT_STARTABLE_STATUSES:
        raise api_error(409, "DEPLOYMENT_STATE_INVALID", "Deployment cannot be started")
    now = datetime.now(UTC).isoformat()
    deployment.update(
        {
            "approved_by": user["id"],
            "failure_reason": None,
            "started_at": now,
            "status": "deploying",
            "updated_at": now,
        }
    )
    run_id = write_store.new_id("deployment_run")
    run = {
        "created_at": now,
        "created_by": user["id"],
        "deployment_request_id": deployment_request_id,
        "executor_type": payload.executor_type or "manual",
        "external_build_id": payload.external_build_id,
        "external_job_name": payload.external_job_name,
        "id": run_id,
        "log_url": payload.log_url,
        "started_at": now,
        "status": "running",
        "updated_at": now,
    }
    for optional_key in ("external_build_id", "external_job_name", "log_url"):
        if run[optional_key] is None:
            run.pop(optional_key)

    deployment_event = record_audit_event(
        write_store,
        event_type="deployment.request.started",
        actor_id=user["id"],
        subject_type="deployment_request",
        subject_id=deployment_request_id,
        payload={"deployment_run_id": run_id, "product_id": deployment.get("product_id")},
    )
    run_event = record_audit_event(
        write_store,
        event_type="deployment.run.started",
        actor_id=user["id"],
        subject_type="deployment_run",
        subject_id=run_id,
        payload={"deployment_request_id": deployment_request_id},
    )
    _save_deployment_request_record(write_store, deployment, audit_events=[deployment_event])
    _save_deployment_run_record(write_store, run, audit_events=[run_event])

    for requirement_id in deployment.get("requirement_ids", []):
        requirement = read_memory_dict(write_store, "requirements").get(str(requirement_id))
        if requirement is None:
            continue
        if requirement.get("status") in DEPLOYMENT_ELIGIBLE_REQUIREMENT_STATUSES:
            updated_requirement = dict(requirement)
            set_requirement_status(updated_requirement, "deploying")
            requirement_event = record_audit_event(
                write_store,
                event_type="requirement.status.updated",
                actor_id=user["id"],
                subject_type="requirement",
                subject_id=str(requirement_id),
                payload={
                    "deployment_request_id": deployment_request_id,
                    "next_status": "deploying",
                    "previous_status": requirement.get("status"),
                },
            )
            save_requirement_record(write_store, updated_requirement, audit_event=requirement_event)
    return _deployment_public_response(write_store, deployment)


def complete_deployment_request_response(
    *,
    current_store: Any,
    deployment_request_id: str,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"deployment.execute"}, {"release_owner"})
    ensure_enum(payload.status, DEPLOYMENT_RESULT_STATUSES, "status")
    write_store = task_workflow_write_store(current_store)
    deployment = dict(_deployment_by_id(write_store, deployment_request_id))
    require_product_scope(user, deployment.get("product_id"))
    if deployment.get("status") != "deploying":
        raise api_error(409, "DEPLOYMENT_STATE_INVALID", "Deployment is not running")
    failure_reason = payload.failure_reason
    if payload.status in {"failed", "rolled_back"}:
        failure_reason = ensure_non_blank(failure_reason, "failure_reason")
    finished_at = parse_optional_time(payload.finished_at, "finished_at") or datetime.now(UTC).isoformat()
    now = datetime.now(UTC).isoformat()
    next_status = "succeeded" if payload.status == "success" else payload.status
    deployment.update(
        {
            "failure_reason": failure_reason,
            "finished_at": finished_at,
            "status": next_status,
            "updated_at": now,
        }
    )
    run = _latest_deployment_run(write_store, deployment_request_id)
    if run is None:
        run = {
            "created_at": now,
            "created_by": user["id"],
            "deployment_request_id": deployment_request_id,
            "executor_type": payload.executor_type or "manual",
            "id": write_store.new_id("deployment_run"),
            "started_at": deployment.get("started_at") or now,
        }
    else:
        run = dict(run)
    run.update(
        {
            "external_build_id": payload.external_build_id or run.get("external_build_id"),
            "external_job_name": payload.external_job_name or run.get("external_job_name"),
            "failure_reason": failure_reason,
            "finished_at": finished_at,
            "log_url": payload.log_url or run.get("log_url"),
            "status": payload.status,
            "updated_at": now,
        }
    )
    for optional_key in ("external_build_id", "external_job_name", "failure_reason", "log_url"):
        if run.get(optional_key) is None:
            run.pop(optional_key, None)

    deployment_event = record_audit_event(
        write_store,
        event_type=(
            "deployment.request.completed"
            if payload.status == "success"
            else "deployment.request.failed"
        ),
        actor_id=user["id"],
        subject_type="deployment_request",
        subject_id=deployment_request_id,
        payload={"result_status": payload.status},
    )
    run_event = record_audit_event(
        write_store,
        event_type="deployment.run.finished",
        actor_id=user["id"],
        subject_type="deployment_run",
        subject_id=str(run["id"]),
        payload={"deployment_request_id": deployment_request_id, "result_status": payload.status},
    )
    _save_deployment_request_record(write_store, deployment, audit_events=[deployment_event])
    _save_deployment_run_record(write_store, run, audit_events=[run_event])

    target_requirement_status = "released" if payload.status == "success" else "ready_for_release"
    for requirement_id in deployment.get("requirement_ids", []):
        requirement = read_memory_dict(write_store, "requirements").get(str(requirement_id))
        if requirement is None:
            continue
        if requirement.get("status") in {"deploying", "ready_for_release", "testing"}:
            updated_requirement = dict(requirement)
            set_requirement_status(updated_requirement, target_requirement_status)
            requirement_event = record_audit_event(
                write_store,
                event_type="requirement.status.updated",
                actor_id=user["id"],
                subject_type="requirement",
                subject_id=str(requirement_id),
                payload={
                    "deployment_request_id": deployment_request_id,
                    "next_status": target_requirement_status,
                    "previous_status": requirement.get("status"),
                },
            )
            save_requirement_record(write_store, updated_requirement, audit_event=requirement_event)
        if payload.status in {"failed", "rolled_back"}:
            _create_deployment_failure_bug(
                write_store,
                deployment=deployment,
                failure_reason=str(failure_reason),
                requirement=requirement,
                run=run,
                user=user,
            )
    return _deployment_public_response(write_store, deployment)


def cancel_deployment_request_response(
    *,
    current_store: Any,
    deployment_request_id: str,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(
        user,
        {"deployment.cancel"},
        {"product_owner", "rd_owner", "release_owner"},
    )
    write_store = task_workflow_write_store(current_store)
    deployment = dict(_deployment_by_id(write_store, deployment_request_id))
    require_product_scope(user, deployment.get("product_id"))
    if deployment.get("status") in DEPLOYMENT_TERMINAL_STATUSES:
        raise api_error(409, "DEPLOYMENT_STATE_INVALID", "Terminal deployment cannot be cancelled")
    now = datetime.now(UTC).isoformat()
    reason = payload.reason or "部署取消"
    deployment.update(
        {
            "failure_reason": reason,
            "finished_at": now,
            "status": "cancelled",
            "updated_at": now,
        }
    )
    deployment_event = record_audit_event(
        write_store,
        event_type="deployment.request.cancelled",
        actor_id=user["id"],
        subject_type="deployment_request",
        subject_id=deployment_request_id,
        payload={"reason": reason},
    )
    _save_deployment_request_record(write_store, deployment, audit_events=[deployment_event])

    for run in _deployment_runs_for_request(write_store, deployment_request_id):
        if run.get("status") != "running":
            continue
        updated_run = dict(run)
        updated_run.update({"finished_at": now, "status": "canceled", "updated_at": now})
        run_event = record_audit_event(
            write_store,
            event_type="deployment.run.cancelled",
            actor_id=user["id"],
            subject_type="deployment_run",
            subject_id=str(run["id"]),
            payload={"deployment_request_id": deployment_request_id},
        )
        _save_deployment_run_record(write_store, updated_run, audit_events=[run_event])

    for requirement_id in deployment.get("requirement_ids", []):
        requirement = read_memory_dict(write_store, "requirements").get(str(requirement_id))
        if requirement is None or requirement.get("status") != "deploying":
            continue
        updated_requirement = dict(requirement)
        set_requirement_status(updated_requirement, "ready_for_release")
        requirement_event = record_audit_event(
            write_store,
            event_type="requirement.status.updated",
            actor_id=user["id"],
            subject_type="requirement",
            subject_id=str(requirement_id),
            payload={
                "deployment_request_id": deployment_request_id,
                "next_status": "ready_for_release",
                "previous_status": "deploying",
            },
        )
        save_requirement_record(write_store, updated_requirement, audit_event=requirement_event)
    return _deployment_public_response(write_store, deployment)


def _create_deployment_failure_bug(
    current_store: Any,
    *,
    deployment: dict[str, Any],
    failure_reason: str,
    requirement: dict[str, Any] | None,
    run: dict[str, Any],
    user: dict[str, Any],
) -> None:
    if requirement is None:
        return
    now = datetime.now(UTC).isoformat()
    bug_id = current_store.new_id("bug")
    bug = {
        "assignee": deployment.get("assigned_ops_user"),
        "created_at": now,
        "created_by": user["id"],
        "description": (
            f"运维部署单 {deployment['id']} 在 {deployment.get('environment', 'prod')} 环境执行失败："
            f"{failure_reason}"
        ),
        "duplicate_of_bug_id": None,
        "evidence": {
            "deployment_request_id": deployment["id"],
            "deployment_run_id": run["id"],
            "environment": deployment.get("environment"),
            "failure_reason": failure_reason,
        },
        "id": bug_id,
        "module_code": requirement.get("module_code"),
        "product_id": deployment["product_id"],
        "related_task_id": deployment.get("release_readiness_task_id"),
        "requirement_id": requirement["id"],
        "reproduce_steps": [
            f"查看部署单 {deployment['id']}",
            "检查部署执行日志和回滚记录",
        ],
        "severity": "major",
        "source": "deployment_failure",
        "status": "open",
        "title": f"部署失败：{requirement.get('title') or deployment.get('title')}",
        "updated_at": now,
        "version_id": deployment["version_id"],
    }
    for optional_key in ("assignee", "duplicate_of_bug_id", "module_code", "related_task_id"):
        if bug[optional_key] is None:
            bug.pop(optional_key)
    bug_event = record_audit_event(
        current_store,
        event_type="bug.created",
        actor_id=user["id"],
        subject_type="bug",
        subject_id=bug_id,
        payload={
            "deployment_request_id": deployment["id"],
            "source": "deployment_failure",
        },
    )
    save_bug_record(current_store, bug, audit_event=bug_event)
