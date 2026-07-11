from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_any_permission_or_roles
from app.core.repositories.devops_writes import DeploymentSchemeVersionConflictError
from app.services.ai_executor_runner_health import runner_is_online
from app.services.bugs import save_bug_record
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
    "rolled_back",
    "succeeded",
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
        "version",
    )
    return {
        field: dict(scheme[field]) if field == "config" else scheme[field]
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


def _validate_scheme_execution_resource(current_store: Any, record: dict[str, Any]) -> None:
    method = str(record.get("deployment_method") or "manual")
    if method in {"ssh", "docker"}:
        from app.services.ai_executor_runners import find_available_deployment_runner

        find_available_deployment_runner(
            current_store,
            deployment_method=method,
            runner_id=str(record["runner_id"]),
            target_code=str(record["target_code"]),
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
    product_id: str | None,
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
    if product_id is not None:
        require_product_scope(user, product_id)
    scoped_product_ids = product_scope_filter(user)
    repository = getattr(current_store, "repository", None)
    list_schemes = getattr(repository, "list_deployment_schemes", None)
    if callable(list_schemes):
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
    items = sorted(
        (dict(item) for item in schemes),
        key=lambda item: (
            not bool(item.get("is_default")),
            str(item.get("name") or ""),
            str(item.get("id") or ""),
        ),
    )
    return {"items": items, "total": len(items)}


def list_deployment_runner_targets_response(
    *,
    current_store: Any,
    method: str | None,
    runner_id: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(
        user,
        {"deployment.scheme.manage"},
        {"release_owner"},
    )
    ensure_enum(method, {"ssh", "docker"}, "method")
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
            items.append(
                {
                    "code": code,
                    "method": target_method,
                    "name": name,
                    "ready": bool(target.get("ready", True)),
                    "runner_id": str(runner["id"]),
                }
            )
    items.sort(key=lambda item: (item["runner_id"], item["method"], item["code"]))
    return {"items": items, "total": len(items)}


def list_deployment_jenkins_connections_response(
    *,
    current_store: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(
        user,
        {"deployment.scheme.manage"},
        {"release_owner"},
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
        items.append(
            {
                "environment": str(connection.get("environment") or "prod"),
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
    _validate_scheme_execution_resource(write_store, record)
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
            "is_default": bool(payload.is_default),
            "status": payload.status,
            "version": 1,
            "created_by": user["id"],
            "created_at": now,
            "updated_at": now,
        }
    )
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
    _validate_scheme_execution_resource(write_store, updated)
    updated["config"] = dict(updated.get("config") or {})
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
) -> dict[str, Any]:
    require_any_permission_or_roles(
        user,
        {"deployment.read"},
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
    items = [
        _deployment_public_response(write_store, deployment)
        for deployment in sorted(
            deployments,
            key=lambda item: item.get("updated_at") or item.get("created_at") or "",
            reverse=True,
        )
    ]
    return {"items": items, "total": len(items)}


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
        "runner"
        if channel == "runner"
        else "jenkins"
        if channel == "integration"
        else "manual"
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
            "deployment_scheme_id": deployment_scheme["id"],
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
    executor_channel = str(deployment.get("executor_channel") or "manual")
    deployment_method = str(deployment.get("deployment_method") or "manual")
    scheme_snapshot = dict(deployment.get("scheme_snapshot") or {})
    runner_binding: dict[str, Any] | None = None
    if executor_channel == "runner":
        from app.services.ai_executor_runners import find_available_deployment_runner

        runner_binding = find_available_deployment_runner(
            write_store,
            deployment_method=deployment_method,
            runner_id=ensure_non_blank(scheme_snapshot.get("runner_id"), "runner_id"),
            target_code=ensure_non_blank(scheme_snapshot.get("target_code"), "target_code"),
        )
    elif executor_channel == "integration" and deployment_method == "jenkins":
        _validate_scheme_execution_resource(write_store, scheme_snapshot)
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
            else "deployment" if executor_channel == "runner" else "jenkins"
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

    if runner_binding is not None:
        from app.services.ai_executor_runners import create_ai_executor_task

        runner_task = create_ai_executor_task(
            write_store,
            action_id=None,
            connection_id=None,
            created_by=user["id"],
            deployment_run_id=run_id,
            executor_type="deployment",
            input_payload={
                "artifact_version": deployment.get("artifact_version"),
                "commit_sha": deployment.get("commit_sha"),
                "deployment_method": deployment_method,
                "deployment_request_id": deployment_request_id,
                "deployment_run_id": run_id,
                "environment": deployment.get("environment"),
                "product_id": deployment.get("product_id"),
                "release_branch": deployment.get("release_branch"),
                "target_code": scheme_snapshot.get("target_code"),
                "version_id": deployment.get("version_id"),
            },
            instruction="Execute the configured deployment target and report the result.",
            plugin_invocation_log_id=None,
            request_config={"deployment_method": deployment_method},
            runner_id=str(runner_binding["id"]),
            scheduled_job_id=None,
            scheduled_job_run_id=None,
            timeout_seconds=int(scheme_snapshot.get("timeout_seconds") or 1800),
            workspace_root="",
        )
        run = {
            **run,
            "runner_task_id": runner_task["id"],
            "updated_at": datetime.now(UTC).isoformat(),
        }
        runner_task_event = record_audit_event(
            write_store,
            event_type="deployment.run.dispatched",
            actor_id=user["id"],
            subject_type="deployment_run",
            subject_id=run_id,
            payload={
                "runner_id": runner_binding["id"],
                "runner_task_id": runner_task["id"],
                "target_code": scheme_snapshot.get("target_code"),
            },
        )
        _save_deployment_run_record(write_store, run, audit_events=[runner_task_event])
    elif executor_channel == "integration" and deployment_method == "jenkins":
        from app.services.jenkins_deployments import trigger_jenkins_deployment

        run = trigger_jenkins_deployment(
            current_store=current_store,
            deployment=deployment,
            run=run,
            user=user,
        )

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
        parse_optional_time(payload.finished_at, "finished_at")
        or datetime.now(UTC).isoformat()
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
        run.get("executor_channel") in {"runner", "integration"}
        for run in active_runs
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
    deployment = read_memory_dict(write_store, "deployment_requests").get(
        deployment_request_id
    )
    if deployment is None:
        return
    deployment = dict(deployment)
    task_status = str(task.get("status") or "")
    status_mapping = {
        "queued": ("queued", "deploying"),
        "claimed": ("running", "deploying"),
        "running": ("running", "deploying"),
        "cancel_requested": ("cancelling", "cancelling"),
        "succeeded": ("success", "succeeded"),
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
    run.update(
        {
            "failure_reason": failure_reason,
            "logs": [dict(item) for item in task.get("logs") or [] if isinstance(item, dict)],
            "status": run_status,
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
        deployment["finished_at"] = task.get("finished_at") or now
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

    if not terminal:
        return
    target_requirement_status = (
        "released" if task_status == "succeeded" else "ready_for_release"
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
