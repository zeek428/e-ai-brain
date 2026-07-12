from __future__ import annotations

from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any
from urllib.error import URLError

from app.api.deps import api_error, require_any_permission_or_roles
from app.core.repositories.devops_writes import DeploymentSchemeVersionConflictError
from app.services.ai_executor_runner_health import runner_is_online
from app.services.bugs import save_bug_record
from app.services.deployment_health import health_evidence_passed
from app.services.deployment_preflight import (
    deployment_release_identity_checks,
    require_deployment_release_identity,
    validate_deployment_window,
)
from app.services.deployment_rollback import auto_rollback_allowed
from app.services.deployment_rollouts import build_rollout_wave_plan
from app.services.operational_records import (
    ensure_enum,
    ensure_non_blank,
    parse_optional_time,
    payload_updates,
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
    "cancelling",
    "deploying",
    "draft",
    "failed",
    "pending_ops",
    "preflight",
    "rolled_back",
    "rolling_back",
    "succeeded",
    "verifying",
    "waiting_takeover",
}
DEPLOYMENT_RUN_STATUSES = {
    "canceled",
    "cancelled",
    "cancelling",
    "failed",
    "queued",
    "rolled_back",
    "running",
    "success",
    "verifying",
}
DEPLOYMENT_RESULT_STATUSES = {"failed", "rolled_back", "success"}
DEPLOYMENT_RISK_LEVELS = {"critical", "high", "low", "medium"}
DEPLOYMENT_STARTABLE_STATUSES = {"approved", "failed", "pending_ops"}
DEPLOYMENT_TERMINAL_STATUSES = {"cancelled", "rolled_back", "succeeded"}
DEPLOYMENT_ELIGIBLE_REQUIREMENT_STATUSES = {"ready_for_release", "testing"}
DEPLOYMENT_OPEN_BUG_STATUSES = {"assigned", "fixed", "needs_info", "open", "reopened", "triaged"}
DEPLOYMENT_BLOCKING_BUG_SEVERITIES = {"blocker", "critical"}
DEPLOYMENT_METHOD_CHANNELS = {
    "manual": "manual",
    "ssh": "runner",
    "docker": "runner",
    "jenkins": "integration",
}
DEPLOYMENT_SCHEME_STATUSES = {"active", "disabled"}
DEPLOYMENT_ROLLOUT_STRATEGIES = {"all_at_once", "batch", "blue_green", "canary"}
DEPLOYMENT_WINDOW_ENFORCEMENTS = {"disabled", "strict", "warn"}
EXECUTION_OUTBOX_MAX_ATTEMPTS = 5
EXECUTION_OUTBOX_NON_RETRYABLE_CODES = {
    "GIT_WRITEBACK_PERMISSION_DENIED",
    "JENKINS_CONNECTION_UNAVAILABLE",
    "JENKINS_JOB_NOT_CONFIGURED",
    "JENKINS_QUEUE_LOCATION_MISSING",
    "JENKINS_RESOURCE_URL_INVALID",
    "JENKINS_ROLLBACK_NOT_CONFIGURED",
}


def _should_process_execution_outbox_inline(current_store: Any) -> bool:
    return getattr(current_store, "repository", None) is None


def _rollout_wave_total(scheme_snapshot: dict[str, Any]) -> int:
    return len(build_rollout_wave_plan(scheme_snapshot))


def _parse_utc_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _deployment_window_evidence(
    deployment: dict[str, Any],
    *,
    now: datetime,
) -> dict[str, Any]:
    return validate_deployment_window(deployment, now=now)


def _quality_gate_run_by_id(
    current_store: Any,
    quality_gate_run_id: str | None,
) -> dict[str, Any] | None:
    if not quality_gate_run_id:
        return None
    repository = getattr(current_store, "repository", None)
    list_runs = getattr(repository, "list_quality_gate_runs", None)
    if callable(list_runs):
        return next(
            (
                dict(item)
                for item in list_runs(subject_id=None, subject_type=None)
                if str(item.get("id")) == quality_gate_run_id
            ),
            None,
        )
    record = read_memory_dict(current_store, "quality_gate_runs").get(quality_gate_run_id)
    return dict(record) if record is not None else None


def _deployment_preflight_evidence(
    current_store: Any,
    deployment: dict[str, Any],
    *,
    runner_binding: dict[str, Any] | None,
) -> dict[str, Any]:
    scheme = deployment.get("scheme_snapshot") or {}
    config = scheme.get("preflight_config") or {}
    strict_production = (
        deployment.get("environment") == "prod" and deployment.get("window_enforcement") == "strict"
    )
    quality_gate = _quality_gate_run_by_id(
        current_store,
        str(deployment.get("quality_gate_run_id") or "") or None,
    )
    checks = [
        {
            "code": "environment_match",
            "passed": scheme.get("environment") == deployment.get("environment"),
        },
        {
            "code": "version_present",
            "passed": bool(deployment.get("version_id")),
        },
        {
            "code": "execution_resource_ready",
            "passed": (deployment.get("executor_channel") != "runner")
            or runner_binding is not None,
        },
        {
            "code": "quality_gate_passed",
            "passed": quality_gate is not None and quality_gate.get("status") == "passed",
        },
    ]
    if strict_production or bool(config.get("require_artifact", False)):
        checks.extend(require_deployment_release_identity(deployment))
    if bool(config.get("require_rollback", deployment.get("environment") == "prod")):
        rollback_config = scheme.get("rollback_config") or {}
        checks.append(
            {
                "code": "rollback_ready",
                "passed": bool(
                    deployment.get("rollback_plan")
                    or rollback_config.get("enabled")
                    or rollback_config.get("strategy")
                    or rollback_config.get("command")
                    or rollback_config.get("job_name")
                ),
            }
        )
    health_config = (
        scheme.get("health_check_config")
        if isinstance(scheme.get("health_check_config"), dict)
        else {}
    )
    executor_channel = str(deployment.get("executor_channel") or "manual")
    rollout_health_required = str(scheme.get("rollout_strategy") or "all_at_once") != "all_at_once"
    target_capabilities: dict[str, Any] = {}
    if runner_binding is not None:
        metadata = (
            runner_binding.get("metadata")
            if isinstance(runner_binding.get("metadata"), dict)
            else {}
        )
        target_code = str(scheme.get("target_code") or "")
        target_capabilities = next(
            (
                item
                for item in metadata.get("deployment_targets") or []
                if isinstance(item, dict) and str(item.get("code") or "") == target_code
            ),
            {},
        )
    if strict_production or rollout_health_required:
        health_ready = executor_channel == "manual"
        if executor_channel == "runner":
            health_ready = bool(
                health_config.get("required") and target_capabilities.get("health_check_configured")
            )
        elif executor_channel == "integration":
            health_ready = bool(health_config.get("job_name"))
        checks.append({"code": "post_deploy_health_ready", "passed": health_ready})
        if strict_production and executor_channel == "runner":
            checks.append(
                {
                    "code": "target_rollback_ready",
                    "passed": bool(target_capabilities.get("rollback_configured")),
                }
            )
            if scheme.get("rollout_strategy") == "blue_green":
                checks.append(
                    {
                        "code": "target_blue_green_ready",
                        "passed": bool(target_capabilities.get("supports_blue_green")),
                    }
                )
    failed = [check["code"] for check in checks if not check["passed"]]
    if failed:
        raise api_error(
            409,
            "DEPLOYMENT_PREFLIGHT_FAILED",
            "Deployment preflight checks failed",
            {"failed_checks": failed},
        )
    return {"checks": checks, "status": "passed"}


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


def _save_deployment_scheme_record(
    current_store: Any,
    record: dict[str, Any],
    *,
    audit_events: list[dict[str, Any]] | None = None,
    expected_version: int | None = None,
) -> None:
    schemes = read_memory_dict(current_store, "deployment_schemes")
    if expected_version is not None:
        current = schemes.get(str(record["id"]))
        if current is not None and int(current.get("version") or 0) != expected_version:
            raise api_error(
                409,
                "VERSION_CONFLICT",
                "Deployment scheme has been changed by another user",
                {"current_version": current.get("version")},
            )
    if record.get("is_default") and record.get("status", "active") == "active":
        for scheme_id, scheme in list(schemes.items()):
            if (
                scheme_id != str(record["id"])
                and scheme.get("product_id") == record.get("product_id")
                and scheme.get("environment") == record.get("environment")
                and scheme.get("status", "active") == "active"
                and scheme.get("is_default")
            ):
                schemes[scheme_id] = {
                    **scheme,
                    "is_default": False,
                    "updated_at": record.get("updated_at") or datetime.now(UTC).isoformat(),
                    "version": int(scheme.get("version") or 1) + 1,
                }
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_deployment_scheme_record", None)
    if callable(save_record):
        try:
            save_record(
                record,
                audit_events=audit_events,
                expected_version=expected_version,
            )
        except DeploymentSchemeVersionConflictError as exc:
            raise api_error(
                409,
                "VERSION_CONFLICT",
                "Deployment scheme has been changed by another user",
                {"current_version": exc.current_version},
            ) from exc
    schemes[str(record["id"])] = record


def _delete_deployment_scheme_record(
    current_store: Any,
    scheme_id: str,
    *,
    audit_events: list[dict[str, Any]] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    delete_record = getattr(repository, "delete_deployment_scheme_record", None)
    if callable(delete_record):
        delete_record(scheme_id, audit_events=audit_events)
    read_memory_dict(current_store, "deployment_schemes").pop(scheme_id, None)


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


def _save_deployment_dispatch_transaction(
    current_store: Any,
    *,
    audit_events: list[dict[str, Any]],
    deployment: dict[str, Any],
    outbox_event: dict[str, Any],
    requirements: list[dict[str, Any]],
    run: dict[str, Any],
    steps: list[dict[str, Any]],
) -> None:
    repository = getattr(current_store, "repository", None)
    save_transaction = getattr(repository, "create_deployment_dispatch_transaction", None)
    if callable(save_transaction):
        save_transaction(
            audit_events=audit_events,
            deployment=deployment,
            outbox_event=outbox_event,
            requirements=requirements,
            run=run,
            steps=steps,
        )
    read_memory_dict(current_store, "deployment_requests")[deployment["id"]] = deployment
    read_memory_dict(current_store, "deployment_runs")[run["id"]] = run
    read_memory_dict(current_store, "execution_outbox_events")[outbox_event["id"]] = outbox_event
    requirement_store = read_memory_dict(current_store, "requirements")
    for requirement in requirements:
        requirement_store[str(requirement["id"])] = requirement
    step_store = read_memory_dict(current_store, "deployment_run_steps")
    for step in steps:
        step_store[step["id"]] = step


def _save_deployment_dispatch_failure_transaction(
    current_store: Any,
    *,
    audit_events: list[dict[str, Any]],
    deployment: dict[str, Any],
    outbox_event: dict[str, Any],
    requirements: list[dict[str, Any]],
    run: dict[str, Any],
    steps: list[dict[str, Any]],
) -> None:
    repository = getattr(current_store, "repository", None)
    save_transaction = getattr(
        repository,
        "save_deployment_dispatch_failure_transaction",
        None,
    )
    if callable(save_transaction):
        save_transaction(
            audit_events=audit_events,
            deployment=deployment,
            outbox_event=outbox_event,
            requirements=requirements,
            run=run,
            steps=steps,
        )
    read_memory_dict(current_store, "deployment_requests")[deployment["id"]] = deployment
    read_memory_dict(current_store, "deployment_runs")[run["id"]] = run
    read_memory_dict(current_store, "execution_outbox_events")[outbox_event["id"]] = outbox_event
    requirement_store = read_memory_dict(current_store, "requirements")
    for requirement in requirements:
        requirement_store[str(requirement["id"])] = requirement
    step_store = read_memory_dict(current_store, "deployment_run_steps")
    for step in steps:
        step_store[str(step["id"])] = step


def _deployment_requirement_transition_records(
    current_store: Any,
    *,
    actor_id: str,
    deployment: dict[str, Any],
    from_statuses: set[str],
    target_status: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    requirements: list[dict[str, Any]] = []
    audit_events: list[dict[str, Any]] = []
    for requirement_id in deployment.get("requirement_ids", []):
        requirement = read_memory_dict(current_store, "requirements").get(str(requirement_id))
        if requirement is None or requirement.get("status") not in from_statuses:
            continue
        updated = dict(requirement)
        set_requirement_status(updated, target_status)
        requirements.append(updated)
        audit_events.append(
            record_audit_event(
                current_store,
                event_type="requirement.status.updated",
                actor_id=actor_id,
                subject_type="requirement",
                subject_id=str(requirement_id),
                payload={
                    "deployment_request_id": deployment["id"],
                    "next_status": target_status,
                    "previous_status": requirement.get("status"),
                },
            )
        )
    return requirements, audit_events


def _save_deployment_dispatch_result(
    current_store: Any,
    *,
    audit_events: list[dict[str, Any]],
    outbox_event: dict[str, Any],
    run: dict[str, Any],
) -> None:
    repository = getattr(current_store, "repository", None)
    save_transaction = getattr(
        repository,
        "save_deployment_dispatch_result_transaction",
        None,
    )
    if callable(save_transaction):
        save_transaction(
            audit_events=audit_events,
            outbox_event=outbox_event,
            run=run,
        )
    read_memory_dict(current_store, "deployment_runs")[run["id"]] = run
    read_memory_dict(current_store, "execution_outbox_events")[outbox_event["id"]] = outbox_event


def _deployment_steps_for_run(
    current_store: Any,
    deployment_run_id: str,
) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    list_steps = getattr(repository, "list_deployment_run_steps", None)
    if callable(list_steps):
        return list(list_steps(deployment_run_id=deployment_run_id))
    return sorted(
        [
            step
            for step in read_memory_records(current_store, "deployment_run_steps")
            if step.get("deployment_run_id") == deployment_run_id
        ],
        key=lambda step: int(step.get("sequence") or 0),
    )


def _save_deployment_steps(
    current_store: Any,
    steps: list[dict[str, Any]],
    *,
    audit_events: list[dict[str, Any]] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_steps = getattr(repository, "save_deployment_run_steps_records", None)
    if callable(save_steps):
        save_steps(steps, audit_events=audit_events)
    step_store = read_memory_dict(current_store, "deployment_run_steps")
    for step in steps:
        step_store[step["id"]] = step


def _deployment_runs_for_request(
    current_store: Any,
    deployment_request_id: str,
) -> list[dict[str, Any]]:
    return [
        run
        for run in read_memory_records(current_store, "deployment_runs")
        if str(run.get("deployment_request_id")) == deployment_request_id
    ]


def _deployment_run_by_id(
    current_store: Any,
    *,
    deployment_request_id: str,
    deployment_run_id: str,
) -> dict[str, Any]:
    for run in _deployment_runs_for_request(current_store, deployment_request_id):
        if str(run.get("id")) == deployment_run_id:
            return dict(run)
    raise api_error(404, "NOT_FOUND", "Deployment run not found")


def _deployment_log_item(
    item: dict[str, Any],
    *,
    fallback_time: str | None,
    source: str,
) -> dict[str, Any] | None:
    message = str(item.get("message") or "").strip()
    if not message:
        return None
    return {
        "created_at": item.get("created_at") or item.get("timestamp") or fallback_time,
        "level": str(item.get("level") or "info").lower(),
        "message": message,
        "source": source,
    }


def _deployment_with_runs(current_store: Any, deployment: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(deployment)
    runs = [
        {
            **dict(run),
            "steps": _deployment_steps_for_run(current_store, str(run["id"])),
        }
        for run in _deployment_runs_for_request(current_store, str(deployment["id"]))
    ]
    enriched["runs"] = sorted(
        runs,
        key=lambda item: item.get("started_at") or item.get("created_at") or "",
        reverse=True,
    )
    repository = getattr(current_store, "repository", None)
    list_outbox = getattr(repository, "list_execution_outbox_events", None)
    if callable(list_outbox):
        enriched["dispatch_events"] = list(
            list_outbox(
                aggregate_id=str(deployment["id"]),
                aggregate_type="deployment_request",
            )
        )
    else:
        enriched["dispatch_events"] = [
            event
            for event in read_memory_records(current_store, "execution_outbox_events")
            if event.get("aggregate_type") == "deployment_request"
            and event.get("aggregate_id") == deployment["id"]
        ]
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
        and (bug.get("requirement_id") in requirement_ids or not bug.get("requirement_id"))
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


def _pre_deploy_gate_checks(
    deployment: dict[str, Any],
    *,
    blocking_bug_count: int,
) -> list[dict[str, Any]]:
    scheme = deployment.get("scheme_snapshot") or {}
    strict_production = (
        deployment.get("environment") == "prod" and deployment.get("window_enforcement") == "strict"
    )
    rollback_config = (
        scheme.get("rollback_config") if isinstance(scheme.get("rollback_config"), dict) else {}
    )
    health_config = (
        scheme.get("health_check_config")
        if isinstance(scheme.get("health_check_config"), dict)
        else {}
    )
    rollout_health_required = str(scheme.get("rollout_strategy") or "all_at_once") != "all_at_once"
    executor_channel = str(deployment.get("executor_channel") or "manual")
    health_ready = executor_channel == "manual"
    if executor_channel == "runner":
        health_ready = bool(health_config.get("required"))
    elif executor_channel == "integration":
        health_ready = bool(health_config.get("job_name"))
    checks = [
        {
            "code": "release_readiness",
            "passed": True,
            "required": True,
            "summary": "需求状态与阻塞 Bug 检查通过",
        },
        {
            "code": "blocking_bug",
            "passed": blocking_bug_count == 0,
            "required": True,
            "summary": "无阻断发布的严重 Bug",
        },
        {
            "code": "deployment_window",
            "passed": bool(
                deployment.get("deploy_window_start") and deployment.get("deploy_window_end")
            ),
            "required": strict_production,
            "summary": "部署窗口配置完整",
        },
        {
            "code": "rollback_ready",
            "passed": bool(
                deployment.get("rollback_plan")
                or rollback_config.get("enabled")
                or rollback_config.get("strategy")
                or rollback_config.get("command")
                or rollback_config.get("job_name")
            ),
            "required": strict_production,
            "summary": "回滚方案配置完整",
        },
        {
            "code": "post_deploy_health_ready",
            "passed": health_ready,
            "required": strict_production or rollout_health_required,
            "summary": "部署后健康检查已配置",
        },
    ]
    checks.extend(
        {
            **item,
            "required": strict_production,
            "summary": {
                "artifact_digest_valid": "制品 SHA-256 摘要有效",
                "artifact_version_present": "制品版本已填写",
                "commit_sha_valid": "Commit SHA 有效",
            }.get(str(item.get("code")), "制品身份有效"),
        }
        for item in deployment_release_identity_checks(deployment)
    )
    return checks


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


def _deployment_scheme_snapshot(scheme: dict[str, Any]) -> dict[str, Any]:
    snapshot_fields = (
        "id",
        "product_id",
        "code",
        "name",
        "environment",
        "deployment_method",
        "executor_channel",
        "runner_id",
        "target_code",
        "jenkins_connection_id",
        "jenkins_job_name",
        "timeout_seconds",
        "config",
        "rollout_strategy",
        "wave_config",
        "preflight_config",
        "health_check_config",
        "rollback_config",
        "window_enforcement",
        "version",
    )
    return {
        field: (
            dict(scheme[field])
            if field
            in {
                "config",
                "wave_config",
                "preflight_config",
                "health_check_config",
                "rollback_config",
            }
            else scheme[field]
        )
        for field in snapshot_fields
        if scheme.get(field) is not None
    }


def _resolve_deployment_scheme(
    current_store: Any,
    *,
    environment: str,
    product_id: str,
    scheme_id: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    if scheme_id:
        scheme = _deployment_scheme_by_id(current_store, scheme_id)
    else:
        schemes = [
            scheme
            for scheme in read_memory_records(current_store, "deployment_schemes")
            if scheme.get("product_id") == product_id
            and scheme.get("environment") == environment
            and scheme.get("status", "active") == "active"
            and scheme.get("is_default")
        ]
        if not schemes:
            repository = getattr(current_store, "repository", None)
            list_schemes = getattr(repository, "list_deployment_schemes", None)
            if callable(list_schemes):
                schemes = [
                    scheme
                    for scheme in list_schemes(
                        environment=environment,
                        product_id=product_id,
                        status="active",
                    )
                    if scheme.get("is_default")
                ]
        if not schemes and environment == "prod":
            schemes = [
                ensure_default_deployment_scheme(
                    current_store,
                    created_by=user["id"],
                    product_id=product_id,
                )
            ]
        if not schemes:
            raise api_error(
                409,
                "DEPLOYMENT_SCHEME_NOT_CONFIGURED",
                "No default deployment scheme is configured for this environment",
            )
        scheme = dict(schemes[0])
    if scheme.get("product_id") != product_id or scheme.get("environment") != environment:
        raise api_error(404, "NOT_FOUND", "Deployment scheme not found")
    if scheme.get("status") != "active":
        raise api_error(409, "DEPLOYMENT_SCHEME_DISABLED", "Deployment scheme is disabled")
    require_product_scope(user, scheme.get("product_id"))
    return scheme


def _scheme_binding_values(record: dict[str, Any]) -> dict[str, Any]:
    method = str(record.get("deployment_method") or "manual")
    ensure_enum(method, set(DEPLOYMENT_METHOD_CHANNELS), "deployment_method")
    expected_channel = DEPLOYMENT_METHOD_CHANNELS[method]
    requested_channel = record.get("executor_channel")
    if requested_channel is not None and requested_channel != expected_channel:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "executor_channel does not match deployment_method",
        )
    values = dict(record)
    values["deployment_method"] = method
    values["executor_channel"] = expected_channel
    if method == "manual":
        for field in (
            "runner_id",
            "target_code",
            "jenkins_connection_id",
            "jenkins_job_name",
        ):
            if values.get(field):
                raise api_error(
                    400,
                    "VALIDATION_ERROR",
                    f"{field} is not supported for manual deployment",
                )
            values.pop(field, None)
    elif method in {"ssh", "docker"}:
        values["runner_id"] = ensure_non_blank(values.get("runner_id"), "runner_id")
        values["target_code"] = ensure_non_blank(values.get("target_code"), "target_code")
        values.pop("jenkins_connection_id", None)
        values.pop("jenkins_job_name", None)
    else:
        values["jenkins_connection_id"] = ensure_non_blank(
            values.get("jenkins_connection_id"),
            "jenkins_connection_id",
        )
        values["jenkins_job_name"] = ensure_non_blank(
            values.get("jenkins_job_name"),
            "jenkins_job_name",
        )
        values.pop("runner_id", None)
        values.pop("target_code", None)
    return values


def _validate_scheme_execution_resource(
    current_store: Any,
    record: dict[str, Any],
    *,
    user: dict[str, Any],
) -> None:
    method = str(record.get("deployment_method") or "manual")
    if method in {"ssh", "docker"}:
        from app.services.ai_executor_runners import find_available_deployment_runner

        find_available_deployment_runner(
            current_store,
            deployment_method=method,
            runner_id=str(record["runner_id"]),
            target_code=str(record["target_code"]),
        )
        from app.services.execution_resource_grants import (
            ensure_execution_resource_grant_for_binding,
        )

        ensure_execution_resource_grant_for_binding(
            current_store,
            environment=str(record.get("environment") or "prod"),
            product_id=str(record.get("product_id") or ""),
            resource_id=str(record["runner_id"]),
            resource_type="runner_target",
            target_code=str(record["target_code"]),
            user=user,
        )
        return
    if method != "jenkins":
        return
    connection_id = str(record.get("jenkins_connection_id") or "")
    connection = read_memory_dict(current_store, "plugin_connections").get(connection_id)
    repository = getattr(current_store, "repository", None)
    list_connections = getattr(repository, "list_plugin_connections", None)
    if connection is None and callable(list_connections):
        connection = next(
            (
                item
                for item in list_connections(status="active")
                if str(item.get("id")) == connection_id
            ),
            None,
        )
    if connection is None or connection.get("status") != "active":
        raise api_error(
            409,
            "DEPLOYMENT_JENKINS_UNAVAILABLE",
            "Configured Jenkins connection is unavailable",
        )
    plugin_code = connection.get("plugin_code")
    if not plugin_code:
        plugin = read_memory_dict(current_store, "integration_plugins").get(
            str(connection.get("plugin_id") or "")
        )
        plugin_code = plugin.get("code") if plugin else None
    if plugin_code != "jenkins":
        raise api_error(
            409,
            "DEPLOYMENT_JENKINS_UNAVAILABLE",
            "Configured connection is not a Jenkins connection",
        )
    from app.services.execution_resource_grants import (
        ensure_execution_resource_grant_for_binding,
    )

    ensure_execution_resource_grant_for_binding(
        current_store,
        environment=str(record.get("environment") or "prod"),
        product_id=str(record.get("product_id") or ""),
        resource_id=connection_id,
        resource_type="jenkins_connection",
        target_code="",
        user=user,
    )


def _require_scheme_execution_resource_grant(
    current_store: Any,
    record: dict[str, Any],
) -> None:
    method = str(record.get("deployment_method") or "manual")
    if method == "manual":
        return
    from app.services.execution_resource_grants import require_execution_resource_grant

    if method in {"ssh", "docker"}:
        require_execution_resource_grant(
            current_store,
            environment=str(record.get("environment") or "prod"),
            product_id=str(record.get("product_id") or ""),
            resource_id=str(record.get("runner_id") or ""),
            resource_type="runner_target",
            target_code=str(record.get("target_code") or ""),
        )
        return
    require_execution_resource_grant(
        current_store,
        environment=str(record.get("environment") or "prod"),
        product_id=str(record.get("product_id") or ""),
        resource_id=str(record.get("jenkins_connection_id") or ""),
        resource_type="jenkins_connection",
        target_code="",
    )


def _deployment_scheme_by_id(current_store: Any, scheme_id: str) -> dict[str, Any]:
    repository = getattr(current_store, "repository", None)
    list_schemes = getattr(repository, "list_deployment_schemes", None)
    if callable(list_schemes):
        matches = list_schemes(scheme_id=scheme_id)
        if matches:
            return dict(matches[0])
    scheme = read_memory_dict(current_store, "deployment_schemes").get(scheme_id)
    if scheme is None:
        raise api_error(404, "NOT_FOUND", "Deployment scheme not found")
    return dict(scheme)


def _validate_scheme_product(current_store: Any, product_id: str, user: dict[str, Any]) -> None:
    require_product_scope(user, product_id)
    product = read_memory_dict(current_store, "products").get(product_id)
    if product is None:
        repository = getattr(current_store, "repository", None)
        get_product = getattr(repository, "get_product", None)
        if callable(get_product):
            product = get_product(product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product.get("status") != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")


def ensure_default_deployment_scheme(
    current_store: Any,
    *,
    created_by: str,
    product_id: str,
) -> dict[str, Any]:
    repository = getattr(current_store, "repository", None)
    list_schemes = getattr(repository, "list_deployment_schemes", None)
    if callable(list_schemes):
        existing = list_schemes(
            environment="prod",
            product_id=product_id,
            status="active",
        )
    else:
        existing = [
            scheme
            for scheme in read_memory_records(current_store, "deployment_schemes")
            if scheme.get("product_id") == product_id
            and scheme.get("environment") == "prod"
            and scheme.get("status", "active") == "active"
        ]
    for scheme in existing:
        if scheme.get("is_default"):
            return dict(scheme)
    now = datetime.now(UTC).isoformat()
    scheme = {
        "id": current_store.new_id("deployment_scheme"),
        "product_id": product_id,
        "code": "default-manual-prod",
        "name": "默认人工部署",
        "environment": "prod",
        "deployment_method": "manual",
        "executor_channel": "manual",
        "timeout_seconds": 1800,
        "config": {},
        "rollout_strategy": "all_at_once",
        "wave_config": {},
        "preflight_config": {},
        "health_check_config": {},
        "rollback_config": {},
        "window_enforcement": "warn",
        "is_default": True,
        "status": "active",
        "version": 1,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    _save_deployment_scheme_record(current_store, scheme)
    return scheme


def list_deployment_schemes_response(
    *,
    current_store: Any,
    deployment_method: str | None,
    environment: str | None,
    name: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    product_id: str | None,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    status: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(
        user,
        {"deployment.read"},
        {"product_owner", "rd_owner", "release_owner", "test_owner", "tester"},
    )
    ensure_enum(deployment_method, set(DEPLOYMENT_METHOD_CHANNELS), "deployment_method")
    ensure_enum(status, DEPLOYMENT_SCHEME_STATUSES, "status")
    use_pagination = page is not None or page_size is not None
    if use_pagination and (
        page is None or page_size is None or page < 1 or page_size < 1 or page_size > 100
    ):
        raise api_error(400, "VALIDATION_ERROR", "Invalid deployment scheme pagination")
    if sort_by not in {
        "code",
        "deployment_method",
        "environment",
        "is_default",
        "name",
        "status",
        "updated_at",
    } or sort_order not in {"asc", "desc"}:
        raise api_error(400, "VALIDATION_ERROR", "Invalid deployment scheme sort")
    if product_id is not None:
        require_product_scope(user, product_id)
    started_at = perf_counter()
    scoped_product_ids = product_scope_filter(user)
    repository = getattr(current_store, "repository", None)
    page_schemes = getattr(repository, "page_deployment_schemes", None)
    list_schemes = getattr(repository, "list_deployment_schemes", None)
    if use_pagination and callable(page_schemes):
        page_result = page_schemes(
            deployment_method=deployment_method,
            environment=environment,
            name=name,
            page=page,
            page_size=page_size,
            product_id=product_id,
            product_scope_ids=scoped_product_ids,
            sort_by=sort_by,
            sort_order=sort_order,
            status=status,
        )
        items = list(page_result["items"])
        total = int(page_result["total"])
    elif callable(list_schemes):
        schemes = list_schemes(
            deployment_method=deployment_method,
            environment=environment,
            product_id=product_id,
            product_scope_ids=scoped_product_ids,
            status=status,
        )
    else:
        schemes = read_memory_records(current_store, "deployment_schemes")
        if scoped_product_ids is not None:
            scoped = set(scoped_product_ids)
            schemes = [item for item in schemes if str(item.get("product_id")) in scoped]
        if product_id is not None:
            schemes = [item for item in schemes if item.get("product_id") == product_id]
        if environment is not None:
            schemes = [item for item in schemes if item.get("environment") == environment]
        if deployment_method is not None:
            schemes = [
                item for item in schemes if item.get("deployment_method") == deployment_method
            ]
        if status is not None:
            schemes = [item for item in schemes if item.get("status") == status]
    if not (use_pagination and callable(page_schemes)):
        if name is not None:
            normalized_name = name.casefold()
            schemes = [
                item
                for item in schemes
                if normalized_name in str(item.get("name") or "").casefold()
            ]
        if use_pagination:
            reverse = sort_order == "desc"
            schemes = sorted(
                schemes,
                key=lambda item: (
                    str(item.get(sort_by) or "").casefold(),
                    str(item.get("id") or ""),
                ),
                reverse=reverse,
            )
            total = len(schemes)
            start = (page - 1) * page_size
            items = [dict(item) for item in schemes[start : start + page_size]]
        else:
            items = sorted(
                (dict(item) for item in schemes),
                key=lambda item: (
                    not bool(item.get("is_default")),
                    str(item.get("name") or ""),
                    str(item.get("id") or ""),
                ),
            )
            total = len(items)
    response = {
        "items": items,
        "query_time_ms": round((perf_counter() - started_at) * 1000, 3),
        "total": total,
    }
    if use_pagination:
        response.update({"page": page, "page_size": page_size})
    return response


def list_deployment_runner_targets_response(
    *,
    current_store: Any,
    environment: str | None,
    method: str | None,
    product_id: str | None,
    runner_id: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(
        user,
        {"deployment.scheme.manage"},
        {"release_owner"},
    )
    ensure_enum(method, {"ssh", "docker"}, "method")
    if product_id is not None:
        require_product_scope(user, product_id)
    from app.services.execution_resource_grants import (
        active_execution_resource_grant_keys,
        user_has_global_execution_resource_access,
    )

    has_global_access = user_has_global_execution_resource_access(user)
    grant_keys = active_execution_resource_grant_keys(
        current_store,
        environment=environment,
        product_id=product_id,
        product_scope_ids=None if has_global_access else product_scope_filter(user),
    )
    repository = getattr(current_store, "repository", None)
    list_runners = getattr(repository, "list_ai_executor_runners", None)
    if callable(list_runners):
        runners = list_runners(status="active")
    else:
        runners = read_memory_records(current_store, "ai_executor_runners")
    items: list[dict[str, Any]] = []
    for runner in runners:
        if runner_id is not None and runner.get("id") != runner_id:
            continue
        if runner.get("status") != "active":
            continue
        if "deployment" not in (runner.get("capabilities") or []):
            continue
        if not runner_is_online(runner):
            continue
        metadata = runner.get("metadata") if isinstance(runner.get("metadata"), dict) else {}
        targets = metadata.get("deployment_targets")
        if not isinstance(targets, list):
            continue
        for target in targets:
            if not isinstance(target, dict):
                continue
            target_method = str(target.get("method") or "").lower()
            if target_method not in {"ssh", "docker"}:
                continue
            if method is not None and target_method != method:
                continue
            code = str(target.get("code") or "").strip()
            name = str(target.get("name") or "").strip()
            if not code or not name:
                continue
            if (
                not has_global_access
                and ("runner_target", str(runner["id"]), code) not in grant_keys
            ):
                continue
            item = {
                "code": code,
                "method": target_method,
                "name": name,
                "ready": bool(target.get("ready", True)),
                "runner_id": str(runner["id"]),
            }
            for capability in (
                "health_check_configured",
                "rollback_configured",
                "supports_blue_green",
            ):
                if bool(target.get(capability)):
                    item[capability] = True
            items.append(item)
    items.sort(key=lambda item: (item["runner_id"], item["method"], item["code"]))
    return {"items": items, "total": len(items)}


def list_deployment_jenkins_connections_response(
    *,
    current_store: Any,
    environment: str | None,
    product_id: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(
        user,
        {"deployment.scheme.manage"},
        {"release_owner"},
    )
    if product_id is not None:
        require_product_scope(user, product_id)
    from app.services.execution_resource_grants import (
        active_execution_resource_grant_keys,
        user_has_global_execution_resource_access,
    )

    has_global_access = user_has_global_execution_resource_access(user)
    grant_keys = active_execution_resource_grant_keys(
        current_store,
        environment=environment,
        product_id=product_id,
        product_scope_ids=None if has_global_access else product_scope_filter(user),
    )
    repository = getattr(current_store, "repository", None)
    list_connections = getattr(repository, "list_plugin_connections", None)
    if callable(list_connections):
        connections = list_connections(status="active")
    else:
        connections = read_memory_records(current_store, "plugin_connections")
    plugins = read_memory_dict(current_store, "integration_plugins")
    items: list[dict[str, Any]] = []
    for connection in connections:
        plugin_code = connection.get("plugin_code")
        plugin = plugins.get(str(connection.get("plugin_id") or ""))
        if not plugin_code and plugin is not None:
            plugin_code = plugin.get("code")
        if plugin_code != "jenkins" or connection.get("status") != "active":
            continue
        connection_environment = str(connection.get("environment") or "prod")
        if environment is not None and connection_environment != environment:
            continue
        if (
            not has_global_access
            and (
                "jenkins_connection",
                str(connection["id"]),
                "",
            )
            not in grant_keys
        ):
            continue
        items.append(
            {
                "environment": connection_environment,
                "id": str(connection["id"]),
                "name": str(connection.get("name") or connection["id"]),
                "ready": plugin is None or plugin.get("status", "active") == "active",
                "status": "active",
            }
        )
    items.sort(key=lambda item: (item["environment"], item["name"], item["id"]))
    return {"items": items, "total": len(items)}


def create_deployment_scheme_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"deployment.scheme.manage"}, {"release_owner"})
    write_store = task_workflow_write_store(current_store)
    product_id = ensure_non_blank(payload.product_id, "product_id")
    _validate_scheme_product(write_store, product_id, user)
    ensure_enum(payload.status, DEPLOYMENT_SCHEME_STATUSES, "status")
    record = _scheme_binding_values(
        {
            "product_id": product_id,
            "code": ensure_non_blank(payload.code, "code"),
            "name": ensure_non_blank(payload.name, "name"),
            "environment": ensure_non_blank(payload.environment, "environment"),
            "deployment_method": payload.deployment_method,
            "runner_id": payload.runner_id,
            "target_code": payload.target_code,
            "jenkins_connection_id": payload.jenkins_connection_id,
            "jenkins_job_name": payload.jenkins_job_name,
        }
    )
    _validate_scheme_execution_resource(write_store, record, user=user)
    existing = read_memory_records(write_store, "deployment_schemes")
    if any(
        item.get("product_id") == product_id and item.get("code") == record["code"]
        for item in existing
    ):
        raise api_error(409, "DEPLOYMENT_SCHEME_CODE_EXISTS", "Deployment scheme code exists")
    now = datetime.now(UTC).isoformat()
    record.update(
        {
            "id": write_store.new_id("deployment_scheme"),
            "timeout_seconds": payload.timeout_seconds,
            "config": dict(payload.config),
            "rollout_strategy": payload.rollout_strategy,
            "wave_config": dict(payload.wave_config),
            "preflight_config": dict(payload.preflight_config),
            "health_check_config": dict(payload.health_check_config),
            "rollback_config": dict(payload.rollback_config),
            "window_enforcement": payload.window_enforcement
            or ("strict" if record.get("environment") == "prod" else "warn"),
            "is_default": bool(payload.is_default),
            "status": payload.status,
            "version": 1,
            "created_by": user["id"],
            "created_at": now,
            "updated_at": now,
        }
    )
    ensure_enum(
        record["rollout_strategy"],
        DEPLOYMENT_ROLLOUT_STRATEGIES,
        "rollout_strategy",
    )
    ensure_enum(
        record["window_enforcement"],
        DEPLOYMENT_WINDOW_ENFORCEMENTS,
        "window_enforcement",
    )
    build_rollout_wave_plan(record)
    event = record_audit_event(
        write_store,
        event_type="deployment.scheme.created",
        actor_id=user["id"],
        subject_type="deployment_scheme",
        subject_id=str(record["id"]),
        payload={"deployment_method": record["deployment_method"], "product_id": product_id},
    )
    _save_deployment_scheme_record(write_store, record, audit_events=[event])
    return record


def update_deployment_scheme_response(
    *,
    current_store: Any,
    payload: Any,
    scheme_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"deployment.scheme.manage"}, {"release_owner"})
    write_store = task_workflow_write_store(current_store)
    existing = _deployment_scheme_by_id(write_store, scheme_id)
    require_product_scope(user, existing.get("product_id"))
    if payload.version != existing.get("version"):
        raise api_error(
            409,
            "VERSION_CONFLICT",
            "Deployment scheme has been changed by another user",
            {"current_version": existing.get("version")},
        )
    changes = payload_updates(payload)
    changes.pop("version", None)
    updated = {**existing, **changes}
    for field in ("code", "name", "environment"):
        updated[field] = ensure_non_blank(updated.get(field), field)
    ensure_enum(updated.get("status"), DEPLOYMENT_SCHEME_STATUSES, "status")
    ensure_enum(
        updated.get("rollout_strategy"),
        DEPLOYMENT_ROLLOUT_STRATEGIES,
        "rollout_strategy",
    )
    ensure_enum(
        updated.get("window_enforcement"),
        DEPLOYMENT_WINDOW_ENFORCEMENTS,
        "window_enforcement",
    )
    if (
        existing.get("is_default")
        and existing.get("status") == "active"
        and (
            not updated.get("is_default")
            or updated.get("status") != "active"
            or updated.get("environment") != existing.get("environment")
        )
    ):
        raise api_error(
            409,
            "DEFAULT_SCHEME_REQUIRED",
            "Set another default deployment scheme before changing the current default",
        )
    updated = _scheme_binding_values(updated)
    _validate_scheme_execution_resource(write_store, updated, user=user)
    updated["config"] = dict(updated.get("config") or {})
    for config_field in (
        "wave_config",
        "preflight_config",
        "health_check_config",
        "rollback_config",
    ):
        updated[config_field] = dict(updated.get(config_field) or {})
    build_rollout_wave_plan(updated)
    updated["version"] = int(existing.get("version") or 1) + 1
    updated["updated_at"] = datetime.now(UTC).isoformat()
    event = record_audit_event(
        write_store,
        event_type="deployment.scheme.updated",
        actor_id=user["id"],
        subject_type="deployment_scheme",
        subject_id=scheme_id,
        payload={"previous_version": existing.get("version"), "version": updated["version"]},
    )
    _save_deployment_scheme_record(
        write_store,
        updated,
        audit_events=[event],
        expected_version=int(existing.get("version") or 1),
    )
    return updated


def get_deployment_scheme_response(
    *,
    current_store: Any,
    scheme_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(
        user,
        {"deployment.read"},
        {"product_owner", "rd_owner", "release_owner", "test_owner", "tester"},
    )
    scheme = _deployment_scheme_by_id(current_store, scheme_id)
    require_product_scope(user, scheme.get("product_id"))
    return scheme


def delete_deployment_scheme_response(
    *,
    current_store: Any,
    scheme_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"deployment.scheme.manage"}, {"release_owner"})
    write_store = task_workflow_write_store(current_store)
    scheme = _deployment_scheme_by_id(write_store, scheme_id)
    require_product_scope(user, scheme.get("product_id"))
    if any(
        deployment.get("deployment_scheme_id") == scheme_id
        for deployment in read_memory_records(write_store, "deployment_requests")
    ):
        raise api_error(
            409,
            "RESOURCE_IN_USE",
            "Deployment scheme is referenced by deployment requests",
        )
    if scheme.get("is_default") and scheme.get("status") == "active":
        raise api_error(
            409,
            "DEFAULT_SCHEME_REQUIRED",
            "Set another default deployment scheme before deletion",
        )
    event = record_audit_event(
        write_store,
        event_type="deployment.scheme.deleted",
        actor_id=user["id"],
        subject_type="deployment_scheme",
        subject_id=scheme_id,
        payload={"product_id": scheme.get("product_id")},
    )
    _delete_deployment_scheme_record(write_store, scheme_id, audit_events=[event])
    return {"deleted": True, "id": scheme_id}


def list_deployment_requests_response(
    *,
    current_store: Any,
    environment: str | None,
    product_id: str | None,
    status: str | None,
    user: dict[str, Any],
    version_id: str | None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
    title: str | None = None,
) -> dict[str, Any]:
    require_any_permission_or_roles(
        user,
        {"deployment.read"},
        {"product_owner", "rd_owner", "release_owner", "test_owner", "tester"},
    )
    ensure_enum(status, DEPLOYMENT_REQUEST_STATUSES, "status")
    if page < 1 or page_size < 1 or page_size > 100:
        raise api_error(400, "VALIDATION_ERROR", "Invalid deployment pagination")
    if sort_by not in {
        "created_at",
        "environment",
        "risk_level",
        "status",
        "title",
        "updated_at",
    } or sort_order not in {"asc", "desc"}:
        raise api_error(400, "VALIDATION_ERROR", "Invalid deployment sort")
    if product_id is not None:
        require_product_scope(user, product_id)
    started_at = perf_counter()
    write_store = task_workflow_write_store(current_store)
    scoped_product_ids = product_scope_filter(user)
    repository = getattr(current_store, "repository", None)
    page_requests = getattr(repository, "page_deployment_requests", None)
    if callable(page_requests):
        page_result = page_requests(
            environment=environment,
            page=page,
            page_size=page_size,
            product_id=product_id,
            product_scope_ids=scoped_product_ids,
            sort_by=sort_by,
            sort_order=sort_order,
            status=status,
            title=title,
            version_id=version_id,
        )
        deployments = list(page_result["items"])
        total = int(page_result["total"])
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
        write_store.deployment_runs = run_records
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
                deployment
                for deployment in deployments
                if deployment.get("product_id") == product_id
            ]
        if version_id is not None:
            deployments = [
                deployment
                for deployment in deployments
                if deployment.get("version_id") == version_id
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
        if title is not None:
            normalized_title = title.casefold()
            deployments = [
                deployment
                for deployment in deployments
                if normalized_title in str(deployment.get("title") or "").casefold()
            ]
        reverse = sort_order == "desc"
        deployments = sorted(
            deployments,
            key=lambda item: (
                str(item.get(sort_by) or "").casefold(),
                str(item.get("id") or ""),
            ),
            reverse=reverse,
        )
        total = len(deployments)
        start = (page - 1) * page_size
        deployments = deployments[start : start + page_size]
    items = [_deployment_public_response(write_store, deployment) for deployment in deployments]
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "query_time_ms": round((perf_counter() - started_at) * 1000, 3),
        "total": total,
    }


def get_deployment_request_detail_response(
    *,
    current_store: Any,
    deployment_request_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(
        user,
        {"deployment.read"},
        {"product_owner", "rd_owner", "release_owner", "test_owner", "tester"},
    )
    write_store = task_workflow_write_store(current_store)
    deployment = _deployment_by_id(write_store, deployment_request_id)
    require_product_scope(user, deployment.get("product_id"))
    detail = _deployment_public_response(write_store, deployment)
    repository = getattr(current_store, "repository", None)
    list_audits = getattr(repository, "list_audit_events", None)
    if callable(list_audits):
        audit_events = list(
            list_audits(
                subject_id=deployment_request_id,
                subject_type="deployment_request",
            )
        )
        for run in detail.get("runs", []):
            audit_events.extend(
                list(
                    list_audits(
                        subject_id=str(run["id"]),
                        subject_type="deployment_run",
                    )
                )
            )
    else:
        run_ids = {str(run.get("id")) for run in detail.get("runs", [])}
        audit_events = [
            dict(event)
            for event in getattr(write_store, "audit_events", [])
            if (
                event.get("subject_type") == "deployment_request"
                and event.get("subject_id") == deployment_request_id
            )
            or (
                event.get("subject_type") == "deployment_run"
                and str(event.get("subject_id")) in run_ids
            )
        ]
    audit_events.sort(
        key=lambda event: str(event.get("created_at") or ""),
        reverse=True,
    )
    detail["audit_events"] = audit_events
    gate_run_id = str(detail.get("quality_gate_run_id") or "").strip()
    if gate_run_id:
        gate = read_memory_dict(write_store, "quality_gate_runs").get(gate_run_id)
        checks = [
            item
            for item in read_memory_records(write_store, "quality_gate_checks")
            if item.get("quality_gate_run_id") == gate_run_id
        ]
        list_gates = getattr(repository, "list_quality_gate_runs", None)
        list_checks = getattr(repository, "list_quality_gate_checks", None)
        if gate is None and callable(list_gates):
            gate = next(
                (
                    item
                    for item in list_gates(subject_id=None, subject_type=None)
                    if item.get("id") == gate_run_id
                ),
                None,
            )
        if not checks and callable(list_checks):
            checks = list(list_checks(gate_run_id))
        detail["quality_gate"] = {**dict(gate or {}), "checks": checks}
    return detail


def get_deployment_run_logs_response(
    *,
    current_store: Any,
    deployment_request_id: str,
    deployment_run_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(
        user,
        {"deployment.read"},
        {"product_owner", "rd_owner", "release_owner", "test_owner", "tester"},
    )
    write_store = task_workflow_write_store(current_store)
    deployment = _deployment_by_id(write_store, deployment_request_id)
    require_product_scope(user, deployment.get("product_id"))
    run = _deployment_run_by_id(
        write_store,
        deployment_request_id=deployment_request_id,
        deployment_run_id=deployment_run_id,
    )
    channel = str(run.get("executor_channel") or "manual")
    source = (
        "runner" if channel == "runner" else "jenkins" if channel == "integration" else "manual"
    )
    fallback_time = run.get("updated_at") or run.get("started_at") or run.get("created_at")
    items = [
        normalized
        for raw_item in (run.get("logs") or [])
        if isinstance(raw_item, dict)
        if (
            normalized := _deployment_log_item(
                raw_item,
                fallback_time=fallback_time,
                source=source,
            )
        )
        is not None
    ]
    if not items:
        started_at = run.get("started_at") or run.get("created_at")
        if started_at:
            items.append(
                {
                    "created_at": started_at,
                    "level": "info",
                    "message": f"部署运行已启动，方式：{run.get('deployment_method') or 'manual'}",
                    "source": source,
                }
            )
        if run.get("external_build_id"):
            items.append(
                {
                    "created_at": fallback_time,
                    "level": "info",
                    "message": f"外部构建已创建：{run['external_build_id']}",
                    "source": source,
                }
            )
        if run.get("failure_reason"):
            items.append(
                {
                    "created_at": run.get("finished_at") or fallback_time,
                    "level": "error",
                    "message": str(run["failure_reason"]),
                    "source": source,
                }
            )
        elif run.get("status") in {"success", "cancelled", "rolled_back"}:
            items.append(
                {
                    "created_at": run.get("finished_at") or fallback_time,
                    "level": "info",
                    "message": f"部署运行状态：{run['status']}",
                    "source": source,
                }
            )
    return {
        "items": items,
        "run": {
            "deployment_method": run.get("deployment_method") or "manual",
            "executor_channel": channel,
            "id": run["id"],
            "status": run.get("status"),
        },
        "total": len(items),
    }


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
    environment = ensure_non_blank(payload.environment, "environment")
    if deploy_window_start is not None and deploy_window_end is not None:
        if deploy_window_end < deploy_window_start:
            raise api_error(
                400,
                "VALIDATION_ERROR",
                "deploy_window_end must be after deploy_window_start",
            )
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
    deployment_scheme = _resolve_deployment_scheme(
        write_store,
        environment=environment,
        product_id=payload.product_id,
        scheme_id=payload.deployment_scheme_id,
        user=user,
    )
    now = datetime.now(UTC).isoformat()
    deployment_id = write_store.new_id("deployment_request")
    deployment = {
        "artifact_digest": payload.artifact_digest,
        "artifact_version": payload.artifact_version,
        "assigned_ops_user": payload.assigned_ops_user,
        "commit_sha": payload.commit_sha,
        "created_at": now,
        "created_by": user["id"],
        "deployment_method": deployment_scheme["deployment_method"],
        "deployment_scheme_id": deployment_scheme["id"],
        "deploy_window_end": deploy_window_end,
        "deploy_window_start": deploy_window_start,
        "environment": environment,
        "executor_channel": deployment_scheme["executor_channel"],
        "failure_reason": None,
        "gate_summary": _deployment_gate_summary(
            requirement_count=len(requirements),
            blocking_bug_count=len(blocking_bugs),
            release_readiness_task_id=release_readiness_task_id,
        ),
        "id": deployment_id,
        "current_wave": 0,
        "product_id": payload.product_id,
        "release_branch": payload.release_branch,
        "release_readiness_task_id": release_readiness_task_id,
        "requirement_ids": requirement_ids,
        "risk_level": payload.risk_level,
        "rollback_plan": payload.rollback_plan,
        "scheme_snapshot": _deployment_scheme_snapshot(deployment_scheme),
        "status": "pending_ops",
        "title": ensure_non_blank(payload.title, "title"),
        "updated_at": now,
        "version_id": payload.version_id,
        "window_enforcement": deployment_scheme.get("window_enforcement") or "warn",
        "total_waves": _rollout_wave_total(deployment_scheme),
        "quality_gate_run_id": None,
    }
    from app.services.quality_gates import create_pre_deploy_quality_gate

    pre_deploy_gate = create_pre_deploy_quality_gate(
        write_store,
        actor_id=user["id"],
        checks=_pre_deploy_gate_checks(
            deployment,
            blocking_bug_count=len(blocking_bugs),
        ),
        deployment=deployment,
    )
    deployment["quality_gate_run_id"] = pre_deploy_gate["id"]
    deployment["gate_summary"] = {
        **deployment["gate_summary"],
        "quality_gate_run_id": pre_deploy_gate["id"],
        "quality_gate_status": pre_deploy_gate["status"],
    }
    for optional_key in (
        "artifact_digest",
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
            "deployment_scheme_id": deployment_scheme["id"],
            "product_id": payload.product_id,
            "requirement_ids": requirement_ids,
            "version_id": payload.version_id,
        },
    )
    _save_deployment_request_record(write_store, deployment, audit_events=[audit_event])
    if environment == "prod" and payload.risk_level in {"high", "critical"}:
        from app.services.production_change_controls import create_production_change_control

        control = create_production_change_control(
            write_store,
            created_by=user["id"],
            deployment_id=deployment_id,
            product_id=payload.product_id,
            required_roles=["release_owner", "test_owner"],
        )
        deployment["production_change_control_id"] = control["id"]
        _save_deployment_request_record(write_store, deployment, audit_events=[])
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
    if deployment.get("status") in {"deploying", "cancelling"}:
        active_run = _latest_deployment_run(write_store, deployment_request_id)
        if active_run is not None and active_run.get("status") in {
            "queued",
            "running",
            "cancelling",
        }:
            return _deployment_public_response(write_store, deployment)
    if deployment.get("status") not in DEPLOYMENT_STARTABLE_STATUSES:
        raise api_error(409, "DEPLOYMENT_STATE_INVALID", "Deployment cannot be started")
    if deployment.get("environment") == "prod":
        from app.services.production_change_controls import (
            production_deployment_can_start,
            production_release_is_frozen,
        )

        if production_release_is_frozen(write_store, product_id=str(deployment["product_id"])):
            raise api_error(409, "RELEASE_FROZEN", "Production deployment is frozen")
        if deployment.get("risk_level") in {
            "high",
            "critical",
        } and not production_deployment_can_start(
            write_store,
            deployment_id=deployment_request_id,
            product_id=str(deployment["product_id"]),
        ):
            raise api_error(
                409,
                "PRODUCTION_CHANGE_CONTROL_REQUIRED",
                "Production deployment requires independent release and test approval",
            )
    executor_channel = str(deployment.get("executor_channel") or "manual")
    deployment_method = str(deployment.get("deployment_method") or "manual")
    scheme_snapshot = dict(deployment.get("scheme_snapshot") or {})
    runner_binding: dict[str, Any] | None = None
    if executor_channel != "manual":
        _require_scheme_execution_resource_grant(write_store, scheme_snapshot)
    if executor_channel == "runner":
        from app.services.ai_executor_runners import find_available_deployment_runner

        runner_binding = find_available_deployment_runner(
            write_store,
            deployment_method=deployment_method,
            runner_id=ensure_non_blank(scheme_snapshot.get("runner_id"), "runner_id"),
            target_code=ensure_non_blank(scheme_snapshot.get("target_code"), "target_code"),
        )
    elif executor_channel == "integration" and deployment_method == "jenkins":
        _validate_scheme_execution_resource(write_store, scheme_snapshot, user=user)
    now_datetime = datetime.now(UTC)
    window_evidence = _deployment_window_evidence(deployment, now=now_datetime)
    preflight_evidence = _deployment_preflight_evidence(
        write_store,
        deployment,
        runner_binding=runner_binding,
    )
    now = now_datetime.isoformat()
    deployment.update(
        {
            "approved_by": user["id"],
            "current_wave": 1,
            "failure_reason": None,
            "started_at": now,
            "status": "deploying",
            "updated_at": now,
        }
    )
    run_id = write_store.new_id("deployment_run")
    run_status = "running" if executor_channel == "manual" else "queued"
    attempt = len(_deployment_runs_for_request(write_store, deployment_request_id)) + 1
    run = {
        "created_at": now,
        "created_by": user["id"],
        "deployment_method": deployment_method,
        "deployment_request_id": deployment_request_id,
        "executor_channel": executor_channel,
        "executor_type": (
            payload.executor_type or "manual"
            if executor_channel == "manual"
            else "deployment"
            if executor_channel == "runner"
            else "jenkins"
        ),
        "execution_snapshot": dict(deployment.get("scheme_snapshot") or {}),
        "external_build_id": payload.external_build_id,
        "external_job_name": payload.external_job_name,
        "id": run_id,
        "idempotency_key": f"deployment-start:{deployment_request_id}:{attempt}",
        "log_url": payload.log_url,
        "started_at": now,
        "status": run_status,
        "updated_at": now,
        "operation": "deploy",
        "wave_number": 1,
        "wave_total": int(deployment.get("total_waves") or 1),
        "health_status": "pending",
        "rollback_run_id": None,
        "quality_gate_run_id": deployment.get("quality_gate_run_id"),
    }
    for optional_key in ("external_build_id", "external_job_name", "log_url"):
        if run[optional_key] is None:
            run.pop(optional_key)

    steps = [
        {
            "id": write_store.new_id("deployment_run_step"),
            "deployment_run_id": run_id,
            "step_type": "preflight",
            "status": "passed",
            "sequence": 1,
            "summary": "部署前检查通过",
            "evidence": {
                "preflight": preflight_evidence,
                "window": window_evidence,
            },
            "started_at": now,
            "finished_at": now,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": write_store.new_id("deployment_run_step"),
            "deployment_run_id": run_id,
            "step_type": "deploy",
            "status": "pending",
            "sequence": 2,
            "summary": "等待派发部署执行",
            "evidence": {},
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": write_store.new_id("deployment_run_step"),
            "deployment_run_id": run_id,
            "step_type": "health_check",
            "status": "pending",
            "sequence": 3,
            "summary": "等待部署后健康检查",
            "evidence": {},
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": write_store.new_id("deployment_run_step"),
            "deployment_run_id": run_id,
            "step_type": "smoke_test",
            "status": "pending",
            "sequence": 4,
            "summary": "等待部署后冒烟测试",
            "evidence": {},
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": write_store.new_id("deployment_run_step"),
            "deployment_run_id": run_id,
            "step_type": "rollback",
            "status": "pending",
            "sequence": 5,
            "summary": "仅在部署验证失败时执行",
            "evidence": {},
            "created_at": now,
            "updated_at": now,
        },
    ]
    if scheme_snapshot.get("rollout_strategy") == "blue_green":
        steps[-1]["sequence"] = 6
        steps.insert(
            -1,
            {
                "id": write_store.new_id("deployment_run_step"),
                "deployment_run_id": run_id,
                "step_type": "traffic_switch",
                "status": "pending",
                "sequence": 5,
                "summary": "等待受控蓝绿流量切换",
                "evidence": {},
                "created_at": now,
                "updated_at": now,
            },
        )
    outbox_event = {
        "id": write_store.new_id("execution_outbox_event"),
        "aggregate_type": "deployment_request",
        "aggregate_id": deployment_request_id,
        "event_type": "deployment_dispatch_requested",
        "idempotency_key": f"deployment:{deployment_request_id}:run:{run_id}:dispatch",
        "payload": {
            "actor_id": user["id"],
            "deployment_request_id": deployment_request_id,
            "deployment_run_id": run_id,
            "operation": "deploy",
        },
        "status": "pending",
        "attempt_count": 0,
        "available_at": now,
        "lease_owner": None,
        "lease_until": None,
        "last_error": None,
        "created_at": now,
        "updated_at": now,
        "processed_at": None,
    }
    deployment_event = record_audit_event(
        write_store,
        event_type="deployment.request.started",
        actor_id=user["id"],
        subject_type="deployment_request",
        subject_id=deployment_request_id,
        payload={
            "deployment_run_id": run_id,
            "outbox_event_id": outbox_event["id"],
            "product_id": deployment.get("product_id"),
        },
    )
    run_event = record_audit_event(
        write_store,
        event_type="deployment.run.started",
        actor_id=user["id"],
        subject_type="deployment_run",
        subject_id=run_id,
        payload={"deployment_request_id": deployment_request_id},
    )
    requirements, requirement_events = _deployment_requirement_transition_records(
        write_store,
        actor_id=user["id"],
        deployment=deployment,
        from_statuses=DEPLOYMENT_ELIGIBLE_REQUIREMENT_STATUSES,
        target_status="deploying",
    )
    _save_deployment_dispatch_transaction(
        write_store,
        audit_events=[deployment_event, run_event, *requirement_events],
        deployment=deployment,
        outbox_event=outbox_event,
        requirements=requirements,
        run=run,
        steps=steps,
    )
    if _should_process_execution_outbox_inline(write_store):
        process_execution_outbox_events(
            write_store,
            limit=1,
            worker_id=f"deployment-request-{user['id']}",
        )
    persisted_deployment = _deployment_by_id(write_store, deployment_request_id)
    return _deployment_public_response(write_store, persisted_deployment)


def _claim_execution_outbox_events(
    current_store: Any,
    *,
    lease_seconds: int,
    limit: int,
    worker_id: str,
) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    claim = getattr(repository, "claim_execution_outbox_events", None)
    if callable(claim):
        return list(
            claim(
                lease_seconds=lease_seconds,
                limit=limit,
                worker_id=worker_id,
            )
        )
    now = datetime.now(UTC)
    claimed: list[dict[str, Any]] = []
    for event in sorted(
        read_memory_records(current_store, "execution_outbox_events"),
        key=lambda item: str(item.get("available_at") or item.get("created_at") or ""),
    ):
        if event.get("status") not in {"pending", "failed", "processing"}:
            continue
        available_at = _parse_utc_datetime(event.get("available_at")) or now
        lease_until = _parse_utc_datetime(event.get("lease_until"))
        if available_at > now or (lease_until is not None and lease_until > now):
            continue
        event.update(
            {
                "attempt_count": int(event.get("attempt_count") or 0) + 1,
                "lease_owner": worker_id,
                "lease_until": (now + timedelta(seconds=lease_seconds)).isoformat(),
                "status": "processing",
                "updated_at": now.isoformat(),
            }
        )
        claimed.append(dict(event))
        if len(claimed) >= limit:
            break
    return claimed


def _outbox_deployment_and_run(
    current_store: Any,
    event: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = event.get("payload") or {}
    deployment_id = str(payload.get("deployment_request_id") or event.get("aggregate_id") or "")
    run_id = str(payload.get("deployment_run_id") or "")
    deployment = read_memory_dict(current_store, "deployment_requests").get(deployment_id)
    run = read_memory_dict(current_store, "deployment_runs").get(run_id)
    repository = getattr(current_store, "repository", None)
    if deployment is None:
        list_deployments = getattr(repository, "list_deployment_requests", None)
        if callable(list_deployments):
            deployment = next(
                (item for item in list_deployments() if item.get("id") == deployment_id),
                None,
            )
    if run is None:
        list_runs = getattr(repository, "list_deployment_runs", None)
        if callable(list_runs):
            run = next(
                (
                    item
                    for item in list_runs(deployment_request_id=deployment_id)
                    if item.get("id") == run_id
                ),
                None,
            )
    if deployment is None or run is None:
        raise RuntimeError("Deployment outbox aggregate is unavailable")
    read_memory_dict(current_store, "deployment_requests")[deployment_id] = dict(deployment)
    read_memory_dict(current_store, "deployment_runs")[run_id] = dict(run)
    return dict(deployment), dict(run)


def _existing_runner_task_for_outbox(
    current_store: Any,
    idempotency_key: str,
) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    list_tasks = getattr(repository, "list_ai_executor_tasks", None)
    tasks = (
        list(list_tasks())
        if callable(list_tasks)
        else read_memory_records(
            current_store,
            "ai_executor_tasks",
        )
    )
    return next(
        (
            task
            for task in tasks
            if (task.get("request_config") or {}).get("outbox_idempotency_key") == idempotency_key
        ),
        None,
    )


def _dispatch_deployment_outbox_event(
    current_store: Any,
    *,
    event: dict[str, Any],
    worker_id: str,
) -> None:
    deployment, run = _outbox_deployment_and_run(current_store, event)
    scheme_snapshot = dict(deployment.get("scheme_snapshot") or {})
    executor_channel = str(deployment.get("executor_channel") or "manual")
    deployment_method = str(deployment.get("deployment_method") or "manual")
    operation = str((event.get("payload") or {}).get("operation") or "deploy")
    wave_plan = build_rollout_wave_plan(scheme_snapshot)
    wave_number = int(run.get("wave_number") or 1)
    wave = wave_plan[min(max(wave_number - 1, 0), len(wave_plan) - 1)]
    now = datetime.now(UTC).isoformat()
    if executor_channel == "runner":
        from app.services.ai_executor_runners import (
            create_ai_executor_task,
            find_available_deployment_runner,
        )

        runner = find_available_deployment_runner(
            current_store,
            deployment_method=deployment_method,
            runner_id=ensure_non_blank(scheme_snapshot.get("runner_id"), "runner_id"),
            target_code=ensure_non_blank(scheme_snapshot.get("target_code"), "target_code"),
        )
        runner_task = _existing_runner_task_for_outbox(
            current_store,
            str(event["idempotency_key"]),
        )
        if runner_task is None:
            runner_task = create_ai_executor_task(
                current_store,
                action_id=None,
                connection_id=None,
                created_by=str((event.get("payload") or {}).get("actor_id") or worker_id),
                deployment_run_id=run["id"],
                executor_type="deployment",
                input_payload={
                    "artifact_digest": deployment.get("artifact_digest"),
                    "artifact_version": deployment.get("artifact_version"),
                    "commit_sha": deployment.get("commit_sha"),
                    "deployment_method": deployment_method,
                    "deployment_request_id": deployment["id"],
                    "deployment_run_id": run["id"],
                    "environment": deployment.get("environment"),
                    "health_check_config": scheme_snapshot.get("health_check_config") or {},
                    "operation": operation,
                    "product_id": deployment.get("product_id"),
                    "release_branch": deployment.get("release_branch"),
                    "rollback_config": scheme_snapshot.get("rollback_config") or {},
                    "rollout_strategy": scheme_snapshot.get("rollout_strategy") or "all_at_once",
                    "smoke_test_config": (scheme_snapshot.get("health_check_config") or {}).get(
                        "smoke_test"
                    )
                    or {},
                    "target_code": scheme_snapshot.get("target_code"),
                    "version_id": deployment.get("version_id"),
                    "wave": wave,
                    "wave_config": scheme_snapshot.get("wave_config") or {},
                    "wave_number": wave_number,
                    "wave_total": run.get("wave_total", 1),
                },
                instruction=(
                    "Execute the configured deployment operation, health checks and smoke tests; "
                    "report structured evidence without exposing target credentials."
                ),
                plugin_invocation_log_id=None,
                request_config={
                    "deployment_method": deployment_method,
                    "operation": operation,
                    "outbox_idempotency_key": event["idempotency_key"],
                },
                runner_id=str(runner["id"]),
                scheduled_job_id=None,
                scheduled_job_run_id=None,
                task_kind="deployment",
                timeout_seconds=int(scheme_snapshot.get("timeout_seconds") or 1800),
                workspace_root="",
            )
        run.update(
            {
                "runner_task_id": runner_task["id"],
                "status": "queued",
                "updated_at": now,
            }
        )
    elif executor_channel == "integration" and deployment_method == "jenkins":
        from app.services.jenkins_deployments import trigger_jenkins_deployment

        run = trigger_jenkins_deployment(
            current_store=current_store,
            deployment=deployment,
            run=run,
            user={"id": str((event.get("payload") or {}).get("actor_id") or worker_id)},
            operation=operation,
            record_failure=False,
        )
    else:
        run.update({"status": "running", "updated_at": now})

    event.update(
        {
            "last_error": None,
            "lease_owner": None,
            "lease_until": None,
            "processed_at": now,
            "status": "completed",
            "updated_at": now,
        }
    )
    audit = record_audit_event(
        current_store,
        event_type="deployment.run.dispatched",
        actor_id=worker_id,
        subject_type="deployment_run",
        subject_id=str(run["id"]),
        payload={
            "operation": operation,
            "outbox_event_id": event["id"],
            "runner_task_id": run.get("runner_task_id"),
        },
    )
    _save_deployment_dispatch_result(
        current_store,
        audit_events=[audit],
        outbox_event=event,
        run=run,
    )
    steps = _deployment_steps_for_run(current_store, str(run["id"]))
    for step in steps:
        if step.get("step_type") == ("rollback" if operation == "rollback" else "deploy"):
            step.update(
                {
                    "status": "running",
                    "started_at": step.get("started_at") or now,
                    "summary": "执行通道已派发",
                    "updated_at": now,
                }
            )
    _save_deployment_steps(current_store, steps)


def _outbox_exception_code(exc: Exception) -> str | None:
    detail = getattr(exc, "detail", None)
    if not isinstance(detail, dict):
        return None
    code = str(detail.get("code") or "").strip()
    return code or None


def _record_deployment_outbox_failure(
    current_store: Any,
    *,
    event: dict[str, Any],
    exc: Exception,
    worker_id: str,
) -> None:
    now = datetime.now(UTC)
    now_iso = now.isoformat()
    attempts = int(event.get("attempt_count") or 1)
    error_code = _outbox_exception_code(exc)
    terminal = (
        attempts >= EXECUTION_OUTBOX_MAX_ATTEMPTS
        or error_code in EXECUTION_OUTBOX_NON_RETRYABLE_CODES
    )
    error_label = error_code or type(exc).__name__
    event.update(
        {
            "available_at": (now + timedelta(seconds=min(300, 2 ** min(attempts, 8)))).isoformat(),
            "last_error": f"{type(exc).__name__}: {error_label}",
            "lease_owner": None,
            "lease_until": None,
            "status": "dead_letter" if terminal else "failed",
            "updated_at": now_iso,
        }
    )
    deployment, run = _outbox_deployment_and_run(current_store, event)
    operation = str((event.get("payload") or {}).get("operation") or "deploy")
    reason = (
        "Deployment dispatch reached the retry limit"
        if terminal and error_code is None
        else error_label
    )
    run.update(
        {
            "failure_reason": reason,
            "status": "failed" if terminal else "queued",
            "updated_at": now_iso,
        }
    )
    deployment.update(
        {
            "failure_reason": reason,
            "status": (
                "waiting_takeover"
                if terminal and operation == "rollback"
                else "failed"
                if terminal
                else deployment.get("status")
            ),
            "updated_at": now_iso,
        }
    )
    if terminal:
        event["processed_at"] = now_iso
        run["finished_at"] = now_iso
        deployment["finished_at"] = now_iso
    steps = _deployment_steps_for_run(current_store, str(run["id"]))
    active_step_type = "rollback" if operation == "rollback" else "deploy"
    for step in steps:
        if step.get("step_type") == active_step_type:
            step.update(
                {
                    "evidence": {
                        **dict(step.get("evidence") or {}),
                        "attempt_count": attempts,
                        "error_code": error_label,
                    },
                    "finished_at": now_iso if terminal else None,
                    "status": "failed" if terminal else "pending",
                    "summary": (
                        "执行通道派发失败，已进入人工处理"
                        if terminal
                        else f"执行通道派发失败，将自动重试（第 {attempts} 次）"
                    ),
                    "updated_at": now_iso,
                }
            )
        elif terminal and step.get("status") == "pending":
            step.update(
                {
                    "finished_at": now_iso,
                    "status": "skipped",
                    "summary": "前置派发失败，未执行",
                    "updated_at": now_iso,
                }
            )
    requirements: list[dict[str, Any]] = []
    requirement_events: list[dict[str, Any]] = []
    if terminal:
        requirements, requirement_events = _deployment_requirement_transition_records(
            current_store,
            actor_id=worker_id,
            deployment=deployment,
            from_statuses={"deploying"},
            target_status="ready_for_release",
        )
    event_type = (
        "execution.outbox.dead_lettered" if terminal else "execution.outbox.retry_scheduled"
    )
    audit = record_audit_event(
        current_store,
        event_type=event_type,
        actor_id=worker_id,
        subject_type="execution_outbox_event",
        subject_id=str(event["id"]),
        payload={
            "attempt_count": attempts,
            "deployment_request_id": deployment["id"],
            "error_code": error_label,
            "next_available_at": None if terminal else event["available_at"],
        },
    )
    _save_deployment_dispatch_failure_transaction(
        current_store,
        audit_events=[audit, *requirement_events],
        deployment=deployment,
        outbox_event=event,
        requirements=requirements,
        run=run,
        steps=steps,
    )


def _dispatch_git_writeback_outbox_event(
    current_store: Any,
    *,
    event: dict[str, Any],
    worker_id: str,
) -> None:
    from app.services.git_provider_writeback import dispatch_git_writeback_event

    result = dispatch_git_writeback_event(current_store, event=event)
    now = datetime.now(UTC).isoformat()
    event.update(
        {
            "last_error": None,
            "lease_owner": None,
            "lease_until": None,
            "payload": {**dict(event.get("payload") or {}), "result": result},
            "processed_at": now,
            "status": "completed",
            "updated_at": now,
        }
    )
    audit = record_audit_event(
        current_store,
        event_type="git.writeback_completed",
        actor_id=worker_id,
        subject_type=str(event.get("aggregate_type") or "git_writeback"),
        subject_id=str(event.get("aggregate_id") or event["id"]),
        payload={
            "action": result.get("action"),
            "outbox_event_id": event["id"],
            "provider": result.get("provider"),
            "status_code": result.get("status_code"),
        },
    )
    repository = getattr(current_store, "repository", None)
    save_event = getattr(repository, "save_execution_outbox_event_record", None)
    if callable(save_event):
        save_event(event, audit_event=audit)
    read_memory_dict(current_store, "execution_outbox_events")[event["id"]] = event


def _record_generic_outbox_failure(
    current_store: Any,
    *,
    event: dict[str, Any],
    exc: Exception,
    worker_id: str,
) -> None:
    now = datetime.now(UTC)
    attempts = int(event.get("attempt_count") or 1)
    terminal = attempts >= EXECUTION_OUTBOX_MAX_ATTEMPTS
    event.update(
        {
            "available_at": (now + timedelta(seconds=min(300, 2 ** min(attempts, 8)))).isoformat(),
            "last_error": f"{type(exc).__name__}: dispatch_failed",
            "lease_owner": None,
            "lease_until": None,
            "processed_at": now.isoformat() if terminal else None,
            "status": "dead_letter" if terminal else "failed",
            "updated_at": now.isoformat(),
        }
    )
    audit = record_audit_event(
        current_store,
        event_type=(
            "execution.outbox.dead_lettered" if terminal else "execution.outbox.retry_scheduled"
        ),
        actor_id=worker_id,
        subject_type="execution_outbox_event",
        subject_id=str(event["id"]),
        payload={
            "attempt_count": attempts,
            "event_type": event.get("event_type"),
        },
    )
    repository = getattr(current_store, "repository", None)
    save_event = getattr(repository, "save_execution_outbox_event_record", None)
    if callable(save_event):
        save_event(event, audit_event=audit)
    read_memory_dict(current_store, "execution_outbox_events")[event["id"]] = event


def _save_execution_outbox_event(current_store: Any, event: dict[str, Any]) -> None:
    repository = getattr(current_store, "repository", None)
    save_event = getattr(repository, "save_execution_outbox_event_record", None)
    if callable(save_event):
        save_event(event)
    read_memory_dict(current_store, "execution_outbox_events")[event["id"]] = event


def _external_result_is_uncertain(exc: Exception) -> bool:
    return isinstance(exc, (TimeoutError, URLError, ConnectionError, OSError))


def process_execution_outbox_events(
    current_store: Any,
    *,
    lease_seconds: int = 30,
    limit: int = 10,
    worker_id: str,
) -> int:
    events = _claim_execution_outbox_events(
        current_store,
        lease_seconds=lease_seconds,
        limit=limit,
        worker_id=worker_id,
    )
    processed = 0
    for event in events:
        external_operation = None
        if event.get("event_type") in {
            "deployment_dispatch_requested",
            "deployment_rollback_requested",
            "deployment_verify_requested",
            "git_writeback_requested",
        }:
            from app.services.external_operation_reconciliation import record_external_operation

            payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
            product_id = str(payload.get("product_id") or "")
            provider = str(payload.get("provider") or payload.get("executor_channel") or "")
            if event.get("aggregate_type") == "deployment_request":
                try:
                    deployment, _ = _outbox_deployment_and_run(current_store, event)
                    product_id = product_id or str(deployment.get("product_id") or "")
                    provider = provider or str(deployment.get("executor_channel") or "")
                except Exception:  # noqa: BLE001 - the dispatch path remains the authoritative error.
                    pass
            external_operation = record_external_operation(
                current_store,
                idempotency_key=str(event.get("idempotency_key") or event["id"]),
                operation_type=str(event.get("event_type")),
                product_id=product_id,
                provider=provider or "runner",
                reference={
                    "deployment_request_id": payload.get("deployment_request_id"),
                    "deployment_run_id": payload.get("deployment_run_id"),
                },
                status="reconciling",
            )
        try:
            if event.get("event_type") in {
                "deployment_dispatch_requested",
                "deployment_rollback_requested",
                "deployment_verify_requested",
            }:
                _dispatch_deployment_outbox_event(
                    current_store,
                    event=event,
                    worker_id=worker_id,
                )
            elif event.get("event_type") == "git_writeback_requested":
                _dispatch_git_writeback_outbox_event(
                    current_store,
                    event=event,
                    worker_id=worker_id,
                )
            else:
                raise RuntimeError("Unsupported execution outbox event")
            if external_operation is not None:
                from app.services.external_operation_reconciliation import (
                    update_external_operation_status,
                )

                update_external_operation_status(
                    current_store,
                    idempotency_key=external_operation["idempotency_key"],
                    status="succeeded",
                )
            processed += 1
        except Exception as exc:  # noqa: BLE001 - durable outbox retries bounded failures.
            if external_operation is not None and _external_result_is_uncertain(exc):
                from app.services.external_operation_reconciliation import (
                    update_external_operation_status,
                )

                update_external_operation_status(
                    current_store,
                    idempotency_key=external_operation["idempotency_key"],
                    status="unknown",
                )
                event.update(
                    {
                        "last_error": f"{type(exc).__name__}: external_result_unknown",
                        "lease_owner": None,
                        "lease_until": None,
                        "processed_at": datetime.now(UTC).isoformat(),
                        "status": "completed",
                        "updated_at": datetime.now(UTC).isoformat(),
                    }
                )
                _save_execution_outbox_event(current_store, event)
                continue
            if external_operation is not None:
                from app.services.external_operation_reconciliation import (
                    update_external_operation_status,
                )

                update_external_operation_status(
                    current_store,
                    idempotency_key=external_operation["idempotency_key"],
                    status="failed",
                )
            if event.get("aggregate_type") == "deployment_request":
                _record_deployment_outbox_failure(
                    current_store,
                    event=event,
                    exc=exc,
                    worker_id=worker_id,
                )
            else:
                _record_generic_outbox_failure(
                    current_store,
                    event=event,
                    exc=exc,
                    worker_id=worker_id,
                )
    return processed


def reconcile_platform_external_operations(
    current_store: Any,
    *,
    actor_id: str,
) -> list[dict[str, Any]]:
    """Read-only provider reconciliation for uncertain dispatches; never re-dispatches work."""
    from app.services.external_operation_reconciliation import reconcile_external_operations

    def provider_lookup(operation: dict[str, Any]) -> dict[str, Any]:
        reference = (
            operation.get("reference") if isinstance(operation.get("reference"), dict) else {}
        )
        deployment_request_id = str(reference.get("deployment_request_id") or "")
        deployment_run_id = str(reference.get("deployment_run_id") or "")
        runner_task = _existing_runner_task_for_outbox(
            current_store,
            str(operation.get("idempotency_key") or ""),
        )
        if runner_task is not None:
            status = str(runner_task.get("status") or "")
            if status == "succeeded":
                return {"provider_status": "succeeded", "receipt": f"runner:{runner_task['id']}"}
            if status in {"cancelled", "failed", "timed_out", "dead_letter"}:
                return {
                    "provider_status": "failed",
                    "receipt": f"runner:{runner_task['id']}:{status}",
                }
            return {"provider_status": "unknown", "receipt": f"runner:{runner_task['id']}:{status}"}
        if not deployment_request_id or not deployment_run_id:
            return {"provider_status": "unknown", "receipt": "provider reference unavailable"}
        try:
            deployment, run = _outbox_deployment_and_run(
                current_store,
                {
                    "aggregate_id": deployment_request_id,
                    "payload": {"deployment_run_id": deployment_run_id},
                },
            )
            if deployment.get("deployment_method") == "jenkins":
                from app.services.jenkins_deployments import sync_jenkins_deployment

                run = sync_jenkins_deployment(
                    current_store=current_store,
                    deployment_request_id=deployment_request_id,
                    deployment_run_id=deployment_run_id,
                    actor_id=actor_id,
                )["run"]
            status = str(run.get("status") or "")
            if status in {"succeeded", "rolled_back"}:
                return {
                    "provider_status": "succeeded",
                    "receipt": f"deployment:{deployment_run_id}:{status}",
                }
            if status in {"failed", "cancelled"}:
                return {
                    "provider_status": "failed",
                    "receipt": f"deployment:{deployment_run_id}:{status}",
                }
            return {
                "provider_status": "unknown",
                "receipt": f"deployment:{deployment_run_id}:{status}",
            }
        except Exception as exc:  # noqa: BLE001 - unknown state must remain non-retryable.
            return {"provider_status": "unknown", "receipt": f"lookup:{type(exc).__name__}"}

    return reconcile_external_operations(current_store, provider_lookup=provider_lookup)


def _queue_followup_deployment_operation(
    current_store: Any,
    *,
    actor_id: str,
    deployment: dict[str, Any],
    operation: str,
    parent_run: dict[str, Any],
    reason: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    run_id = current_store.new_id("deployment_run")
    next_wave = int(parent_run.get("wave_number") or 1) + (1 if operation == "deploy" else 0)
    deployment = dict(deployment)
    deployment.update(
        {
            "current_wave": next_wave,
            "failure_reason": reason,
            "status": (
                "rolling_back"
                if operation == "rollback"
                else "verifying"
                if operation == "verify"
                else "deploying"
            ),
            "updated_at": now,
        }
    )
    deployment.pop("finished_at", None)
    run = {
        "id": run_id,
        "deployment_request_id": deployment["id"],
        "executor_type": parent_run.get("executor_type") or "deployment",
        "deployment_method": deployment.get("deployment_method") or "manual",
        "executor_channel": deployment.get("executor_channel") or "manual",
        "status": "queued" if deployment.get("executor_channel") != "manual" else "running",
        "execution_snapshot": dict(deployment.get("scheme_snapshot") or {}),
        "idempotency_key": (f"deployment-{operation}:{deployment['id']}:{next_wave}:{run_id}"),
        "operation": operation,
        "wave_number": next_wave,
        "wave_total": int(deployment.get("total_waves") or 1),
        "health_status": "pending",
        "rollback_run_id": parent_run["id"] if operation == "rollback" else None,
        "quality_gate_run_id": deployment.get("quality_gate_run_id"),
        "failure_reason": reason,
        "created_by": actor_id,
        "created_at": now,
        "updated_at": now,
    }
    step_type = (
        "rollback"
        if operation == "rollback"
        else "health_check"
        if operation == "verify"
        else "deploy"
    )
    steps = [
        {
            "id": current_store.new_id("deployment_run_step"),
            "deployment_run_id": run_id,
            "step_type": "preflight",
            "status": "passed",
            "sequence": 1,
            "summary": f"{operation} 后续操作预检通过",
            "evidence": {"parent_run_id": parent_run["id"], "reason": reason},
            "started_at": now,
            "finished_at": now,
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": current_store.new_id("deployment_run_step"),
            "deployment_run_id": run_id,
            "step_type": step_type,
            "status": "pending",
            "sequence": 2,
            "summary": "等待执行通道派发",
            "evidence": {},
            "created_at": now,
            "updated_at": now,
        },
    ]
    if operation == "deploy":
        steps.extend(
            [
                {
                    "id": current_store.new_id("deployment_run_step"),
                    "deployment_run_id": run_id,
                    "step_type": "health_check",
                    "status": "pending",
                    "sequence": 3,
                    "summary": "等待部署后健康检查",
                    "evidence": {},
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": current_store.new_id("deployment_run_step"),
                    "deployment_run_id": run_id,
                    "step_type": "smoke_test",
                    "status": "pending",
                    "sequence": 4,
                    "summary": "等待部署后冒烟测试",
                    "evidence": {},
                    "created_at": now,
                    "updated_at": now,
                },
            ]
        )
        if (deployment.get("scheme_snapshot") or {}).get(
            "rollout_strategy"
        ) == "blue_green" and next_wave == int(deployment.get("total_waves") or 1):
            steps.append(
                {
                    "id": current_store.new_id("deployment_run_step"),
                    "deployment_run_id": run_id,
                    "step_type": "traffic_switch",
                    "status": "pending",
                    "sequence": 5,
                    "summary": "等待受控蓝绿流量切换",
                    "evidence": {},
                    "created_at": now,
                    "updated_at": now,
                }
            )
    elif operation == "verify":
        steps.append(
            {
                "id": current_store.new_id("deployment_run_step"),
                "deployment_run_id": run_id,
                "step_type": "smoke_test",
                "status": "pending",
                "sequence": 3,
                "summary": "等待 Jenkins 冒烟验证",
                "evidence": {},
                "created_at": now,
                "updated_at": now,
            }
        )
    outbox = {
        "id": current_store.new_id("execution_outbox_event"),
        "aggregate_type": "deployment_request",
        "aggregate_id": deployment["id"],
        "event_type": (
            "deployment_rollback_requested"
            if operation == "rollback"
            else "deployment_verify_requested"
            if operation == "verify"
            else "deployment_dispatch_requested"
        ),
        "idempotency_key": f"deployment:{deployment['id']}:run:{run_id}:{operation}",
        "payload": {
            "actor_id": actor_id,
            "deployment_request_id": deployment["id"],
            "deployment_run_id": run_id,
            "operation": operation,
            "parent_run_id": parent_run["id"],
            "reason": reason,
        },
        "status": "pending",
        "attempt_count": 0,
        "available_at": now,
        "created_at": now,
        "updated_at": now,
    }
    deployment_audit = record_audit_event(
        current_store,
        event_type=f"deployment.request.{operation}_queued",
        actor_id=actor_id,
        subject_type="deployment_request",
        subject_id=deployment["id"],
        payload={"parent_run_id": parent_run["id"], "run_id": run_id},
    )
    run_audit = record_audit_event(
        current_store,
        event_type=f"deployment.run.{operation}_queued",
        actor_id=actor_id,
        subject_type="deployment_run",
        subject_id=run_id,
        payload={"parent_run_id": parent_run["id"]},
    )
    _save_deployment_dispatch_transaction(
        current_store,
        audit_events=[deployment_audit, run_audit],
        deployment=deployment,
        outbox_event=outbox,
        requirements=[],
        run=run,
        steps=steps,
    )
    if _should_process_execution_outbox_inline(current_store):
        process_execution_outbox_events(
            current_store,
            limit=1,
            worker_id=f"deployment-followup-{actor_id}",
        )
    return deployment


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
    if (deployment.get("executor_channel") or "manual") != "manual":
        raise api_error(
            409,
            "DEPLOYMENT_RESULT_MANAGED_EXTERNALLY",
            "Automated deployment results must be reported by the execution channel",
        )
    failure_reason = payload.failure_reason
    if payload.status in {"failed", "rolled_back"}:
        failure_reason = ensure_non_blank(failure_reason, "failure_reason")
    finished_at = (
        parse_optional_time(payload.finished_at, "finished_at") or datetime.now(UTC).isoformat()
    )
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
    active_runs = [
        run
        for run in _deployment_runs_for_request(write_store, deployment_request_id)
        if run.get("status") in {"queued", "running", "cancelling"}
    ]
    waits_for_external_confirmation = any(
        run.get("executor_channel") in {"runner", "integration"} for run in active_runs
    )
    next_status = "cancelling" if waits_for_external_confirmation else "cancelled"
    deployment.update(
        {
            "failure_reason": reason,
            "status": next_status,
            "updated_at": now,
        }
    )
    if waits_for_external_confirmation:
        deployment.pop("finished_at", None)
    else:
        deployment["finished_at"] = now
    deployment_event = record_audit_event(
        write_store,
        event_type=(
            "deployment.request.cancel_requested"
            if waits_for_external_confirmation
            else "deployment.request.cancelled"
        ),
        actor_id=user["id"],
        subject_type="deployment_request",
        subject_id=deployment_request_id,
        payload={"reason": reason},
    )
    _save_deployment_request_record(write_store, deployment, audit_events=[deployment_event])

    for run in active_runs:
        updated_run = dict(run)
        run_status = (
            "cancelling"
            if run.get("executor_channel") in {"runner", "integration"}
            else "cancelled"
        )
        updated_run.update({"status": run_status, "updated_at": now})
        if run_status == "cancelled":
            updated_run["finished_at"] = now
        run_event = record_audit_event(
            write_store,
            event_type=(
                "deployment.run.cancel_requested"
                if run_status == "cancelling"
                else "deployment.run.cancelled"
            ),
            actor_id=user["id"],
            subject_type="deployment_run",
            subject_id=str(run["id"]),
            payload={"deployment_request_id": deployment_request_id},
        )
        _save_deployment_run_record(write_store, updated_run, audit_events=[run_event])

    if waits_for_external_confirmation:
        from app.services.ai_executor_runners import request_ai_executor_task_cancel
        from app.services.jenkins_deployments import cancel_jenkins_deployment

        for run in active_runs:
            if run.get("executor_channel") == "integration":
                cancel_jenkins_deployment(
                    current_store=current_store,
                    deployment_request_id=deployment_request_id,
                    deployment_run_id=str(run["id"]),
                    actor_id=user["id"],
                )
                continue
            runner_task_id = str(run.get("runner_task_id") or "").strip()
            if run.get("executor_channel") != "runner" or not runner_task_id:
                continue
            request_ai_executor_task_cancel(
                current_store,
                actor_id=user["id"],
                reason=reason,
                task_id=runner_task_id,
            )
        refreshed_store = task_workflow_write_store(current_store)
        refreshed_deployment = _deployment_by_id(refreshed_store, deployment_request_id)
        return _deployment_public_response(refreshed_store, refreshed_deployment)

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


def rollback_deployment_request_response(
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
    if deployment.get("status") == "rolling_back":
        return _deployment_public_response(write_store, deployment)
    if deployment.get("status") not in {"failed", "succeeded", "waiting_takeover"}:
        raise api_error(
            409,
            "DEPLOYMENT_STATE_INVALID",
            "Deployment cannot be rolled back in the current state",
        )
    parent_run = _latest_deployment_run(write_store, deployment_request_id)
    if parent_run is None:
        raise api_error(409, "DEPLOYMENT_RUN_MISSING", "Deployment has no run to roll back")
    rollback_config = (deployment.get("scheme_snapshot") or {}).get("rollback_config") or {}
    if deployment.get("executor_channel") != "manual" and not any(
        rollback_config.get(field) for field in ("command", "enabled", "job_name", "strategy")
    ):
        raise api_error(
            409,
            "DEPLOYMENT_ROLLBACK_NOT_CONFIGURED",
            "Automated rollback is not configured for this deployment scheme",
        )
    _queue_followup_deployment_operation(
        write_store,
        actor_id=user["id"],
        deployment=deployment,
        operation="rollback",
        parent_run=parent_run,
        reason=ensure_non_blank(payload.reason, "reason"),
    )
    refreshed = _deployment_by_id(write_store, deployment_request_id)
    return _deployment_public_response(write_store, refreshed)


def sync_jenkins_deployment_response(
    *,
    current_store: Any,
    deployment_request_id: str,
    deployment_run_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"deployment.execute"}, {"release_owner"})
    write_store = task_workflow_write_store(current_store)
    deployment = _deployment_by_id(write_store, deployment_request_id)
    require_product_scope(user, deployment.get("product_id"))
    from app.services.jenkins_deployments import sync_jenkins_deployment

    return sync_jenkins_deployment(
        current_store=current_store,
        deployment_request_id=deployment_request_id,
        deployment_run_id=deployment_run_id,
        actor_id=user["id"],
    )


def sync_deployment_runner_task(
    *,
    current_store: Any,
    runner_id: str,
    task: dict[str, Any],
) -> None:
    deployment_run_id = str(task.get("deployment_run_id") or "").strip()
    if not deployment_run_id:
        return
    write_store = task_workflow_write_store(current_store)
    run = read_memory_dict(write_store, "deployment_runs").get(deployment_run_id)
    if run is None:
        return
    run = dict(run)
    deployment_request_id = str(run.get("deployment_request_id") or "")
    deployment = read_memory_dict(write_store, "deployment_requests").get(deployment_request_id)
    if deployment is None:
        return
    deployment = dict(deployment)
    task_status = str(task.get("status") or "")
    operation = str(run.get("operation") or "deploy")
    result_json = task.get("result_json") if isinstance(task.get("result_json"), dict) else {}
    wave_number = int(run.get("wave_number") or 1)
    wave_total = int(run.get("wave_total") or deployment.get("total_waves") or 1)
    strict_runner_health_required = (
        operation == "deploy"
        and deployment.get("executor_channel") == "runner"
        and deployment.get("environment") == "prod"
        and deployment.get("window_enforcement") == "strict"
    )
    rollout_health_required = operation == "deploy" and (
        strict_runner_health_required or wave_total > 1
    )
    if (
        task_status == "succeeded"
        and rollout_health_required
        and not health_evidence_passed(result_json)
    ):
        task_status = "failed"
        task = {
            **task,
            "error_message": "Deployment wave is missing passing health and smoke evidence",
        }
        result_json = {**result_json, "health_status": "failed"}
    active_deployment_status = (
        "rolling_back"
        if operation == "rollback"
        else "verifying"
        if operation == "verify"
        else "deploying"
    )
    status_mapping = {
        "queued": ("queued", active_deployment_status),
        "claimed": ("running", active_deployment_status),
        "running": ("running", active_deployment_status),
        "cancel_requested": ("cancelling", "cancelling"),
        "succeeded": (
            "rolled_back" if operation == "rollback" else "success",
            "rolled_back" if operation == "rollback" else "succeeded",
        ),
        "cancelled": ("cancelled", "cancelled"),
        "failed": ("failed", "failed"),
        "timed_out": ("failed", "failed"),
        "dead_letter": ("failed", "failed"),
    }
    mapped = status_mapping.get(task_status)
    if mapped is None:
        return
    run_status, deployment_status = mapped
    now = datetime.now(UTC).isoformat()
    terminal = task_status in {"succeeded", "cancelled", "failed", "timed_out", "dead_letter"}
    previous_run_status = str(run.get("status") or "")
    failure_reason = str(task.get("error_message") or "").strip() or None
    if task_status == "cancelled":
        failure_reason = deployment.get("failure_reason") or failure_reason or "部署取消"
    queue_next_wave = (
        operation == "deploy" and task_status == "succeeded" and wave_number < wave_total
    )
    health_config = (
        (deployment.get("scheme_snapshot") or {}).get("health_check_config")
        if isinstance(
            (deployment.get("scheme_snapshot") or {}).get("health_check_config"),
            dict,
        )
        else {}
    )
    queue_verification = (
        operation == "deploy"
        and task_status == "succeeded"
        and not queue_next_wave
        and deployment.get("deployment_method") == "jenkins"
        and bool(health_config.get("job_name"))
    )
    rollback_config = (
        (deployment.get("scheme_snapshot") or {}).get("rollback_config")
        if isinstance((deployment.get("scheme_snapshot") or {}).get("rollback_config"), dict)
        else {}
    )
    auto_rollback = (
        operation in {"deploy", "verify"}
        and task_status in {"failed", "timed_out", "dead_letter"}
        and auto_rollback_allowed(
            risk_level=str(deployment.get("risk_level") or "medium"),
            rollback_config=rollback_config,
        )
    )
    if queue_next_wave:
        deployment_status = "deploying"
    elif queue_verification:
        deployment_status = "verifying"
    elif auto_rollback:
        deployment_status = "rolling_back"
    elif (
        operation in {"deploy", "verify"}
        and task_status in {"failed", "timed_out", "dead_letter"}
        and bool(rollback_config.get("human_takeover_on_failure", True))
    ):
        deployment_status = "waiting_takeover"
    elif operation == "rollback" and task_status in {"failed", "timed_out", "dead_letter"}:
        deployment_status = "waiting_takeover"
    run.update(
        {
            "failure_reason": failure_reason,
            "logs": [dict(item) for item in task.get("logs") or [] if isinstance(item, dict)],
            "status": run_status,
            "health_status": result_json.get("health_status")
            and (
                "healthy"
                if result_json.get("health_status") == "passed"
                else "unhealthy"
                if result_json.get("health_status") == "failed"
                else str(result_json.get("health_status"))
            )
            or (
                "healthy" if task_status == "succeeded" else "unhealthy" if terminal else "pending"
            ),
            "updated_at": now,
        }
    )
    if not task.get("preserve_runner_task_id") and task.get("id"):
        run["runner_task_id"] = task.get("id")
    deployment.update(
        {
            "failure_reason": failure_reason,
            "status": deployment_status,
            "updated_at": now,
        }
    )
    if terminal:
        run["finished_at"] = task.get("finished_at") or now
        run["next_sync_at"] = None
        run["sync_lease_owner"] = None
        run["sync_lease_until"] = None
        if deployment_status in {
            "cancelled",
            "failed",
            "rolled_back",
            "succeeded",
            "waiting_takeover",
        }:
            deployment["finished_at"] = task.get("finished_at") or now
        else:
            deployment.pop("finished_at", None)
    else:
        run.pop("finished_at", None)
        deployment.pop("finished_at", None)
    run_event = record_audit_event(
        write_store,
        event_type=f"deployment.run.runner_{task_status}",
        actor_id=runner_id,
        subject_type="deployment_run",
        subject_id=deployment_run_id,
        payload={"runner_task_id": task.get("id"), "status": run_status},
    )
    deployment_event = record_audit_event(
        write_store,
        event_type=f"deployment.request.runner_{task_status}",
        actor_id=runner_id,
        subject_type="deployment_request",
        subject_id=deployment_request_id,
        payload={"deployment_run_id": deployment_run_id, "status": deployment_status},
    )
    _save_deployment_run_record(write_store, run, audit_events=[run_event])
    _save_deployment_request_record(write_store, deployment, audit_events=[deployment_event])

    steps = _deployment_steps_for_run(write_store, deployment_run_id)
    for step in steps:
        step_type = step.get("step_type")
        active_step_type = (
            "rollback" if operation == "rollback" else "deploy" if operation == "deploy" else None
        )
        if active_step_type is not None and step_type == active_step_type:
            step.update(
                {
                    "status": "passed"
                    if task_status == "succeeded"
                    else "failed"
                    if terminal
                    else "running",
                    "finished_at": task.get("finished_at") or now if terminal else None,
                    "summary": failure_reason
                    or ("执行完成" if task_status == "succeeded" else "执行中"),
                    "updated_at": now,
                }
            )
        elif step_type == "health_check" and terminal:
            health_status = str(result_json.get("health_status") or "pending")
            step.update(
                {
                    "status": "passed" if health_status == "passed" else "failed",
                    "evidence": {"checks": result_json.get("health_checks") or []},
                    "finished_at": task.get("finished_at") or now,
                    "summary": f"健康检查：{health_status}",
                    "updated_at": now,
                }
            )
        elif step_type == "smoke_test" and terminal:
            smoke_tests = result_json.get("smoke_tests") or []
            smoke_passed = (
                all(item.get("passed") for item in smoke_tests)
                if smoke_tests
                else (task_status == "succeeded")
            )
            step.update(
                {
                    "status": "passed" if smoke_passed else "failed",
                    "evidence": {"tests": smoke_tests},
                    "finished_at": task.get("finished_at") or now,
                    "summary": "冒烟测试通过" if smoke_passed else "冒烟测试失败",
                    "updated_at": now,
                }
            )
        elif step_type == "traffic_switch" and terminal:
            switched = bool(result_json.get("traffic_switch_passed"))
            if not result_json.get("traffic_switch_attempted"):
                switched = task_status == "succeeded"
            step.update(
                {
                    "status": "passed" if switched else "failed",
                    "evidence": {
                        "action": result_json.get("traffic_switch_action"),
                        "attempted": result_json.get("traffic_switch_attempted", False),
                    },
                    "finished_at": task.get("finished_at") or now,
                    "summary": "蓝绿流量切换通过" if switched else "蓝绿流量切换失败",
                    "updated_at": now,
                }
            )
    _save_deployment_steps(write_store, steps)

    if not terminal:
        return
    if queue_next_wave:
        _queue_followup_deployment_operation(
            write_store,
            actor_id=runner_id,
            deployment=deployment,
            operation="deploy",
            parent_run=run,
            reason=f"rollout_wave_{wave_number}_completed",
        )
        return
    if queue_verification:
        _queue_followup_deployment_operation(
            write_store,
            actor_id=runner_id,
            deployment=deployment,
            operation="verify",
            parent_run=run,
            reason="jenkins_deployment_completed",
        )
        return
    if auto_rollback:
        _queue_followup_deployment_operation(
            write_store,
            actor_id=runner_id,
            deployment=deployment,
            operation="rollback",
            parent_run=run,
            reason=failure_reason or "deployment_health_validation_failed",
        )
        return
    target_requirement_status = (
        "released"
        if task_status == "succeeded" and operation in {"deploy", "verify"}
        else "ready_for_release"
    )
    for requirement_id in deployment.get("requirement_ids", []):
        requirement = read_memory_dict(write_store, "requirements").get(str(requirement_id))
        if requirement is None:
            continue
        if requirement.get("status") in {
            "deploying",
            "ready_for_release",
            "testing",
        }:
            updated_requirement = dict(requirement)
            set_requirement_status(updated_requirement, target_requirement_status)
            requirement_event = record_audit_event(
                write_store,
                event_type="requirement.status.updated",
                actor_id=runner_id,
                subject_type="requirement",
                subject_id=str(requirement_id),
                payload={
                    "deployment_request_id": deployment_request_id,
                    "next_status": target_requirement_status,
                    "previous_status": requirement.get("status"),
                },
            )
            save_requirement_record(
                write_store,
                updated_requirement,
                audit_event=requirement_event,
            )
        if (
            task_status in {"failed", "timed_out", "dead_letter"}
            and previous_run_status != "failed"
        ):
            _create_deployment_failure_bug(
                write_store,
                deployment=deployment,
                failure_reason=failure_reason or "Runner deployment failed",
                requirement=requirement,
                run=run,
                user={"id": runner_id},
            )


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
    rollback_failure = str(run.get("operation") or "deploy") == "rollback"
    bug_id = current_store.new_id("bug")
    bug = {
        "assignee": deployment.get("assigned_ops_user"),
        "created_at": now,
        "created_by": user["id"],
        "description": (
            f"运维部署单 {deployment['id']} 在 "
            f"{deployment.get('environment', 'prod')} 环境执行失败："
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
        "severity": "critical" if rollback_failure else "major",
        "source": "deployment_rollback_failure" if rollback_failure else "deployment_failure",
        "status": "open",
        "title": (
            f"回滚失败需人工接管：{requirement.get('title') or deployment.get('title')}"
            if rollback_failure
            else f"部署失败：{requirement.get('title') or deployment.get('title')}"
        ),
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
            "source": bug["source"],
        },
    )
    save_bug_record(current_store, bug, audit_event=bug_event)
