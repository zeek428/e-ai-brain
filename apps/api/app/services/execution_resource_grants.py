from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from fastapi import HTTPException

from app.api.deps import api_error, require_any_permission_or_roles
from app.core.repositories.execution_governance_writes import (
    ExecutionGovernanceVersionConflictError,
)
from app.services.operational_records import (
    ensure_enum,
    ensure_non_blank,
    read_memory_dict,
    read_memory_records,
    record_audit_event,
)
from app.services.product_scope import product_scope_filter, require_product_scope

EXECUTION_RESOURCE_TYPES = {"jenkins_connection", "runner_target"}
EXECUTION_RESOURCE_GRANT_STATUSES = {"active", "disabled"}


def user_has_global_execution_resource_access(user: dict[str, Any]) -> bool:
    return "admin" in set(user.get("roles") or []) or "system.admin" in set(
        user.get("permissions") or []
    )


def _list_grants(
    current_store: Any,
    *,
    environment: str | None = None,
    product_id: str | None = None,
    product_scope_ids: list[str] | None = None,
    resource_type: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None)
    list_records = getattr(repository, "list_execution_resource_grants", None)
    if callable(list_records):
        return list(
            list_records(
                environment=environment,
                product_id=product_id,
                product_scope_ids=product_scope_ids,
                resource_type=resource_type,
                status=status,
            )
        )
    items = read_memory_records(current_store, "execution_resource_grants")
    if product_scope_ids is not None:
        allowed = set(product_scope_ids)
        items = [item for item in items if str(item.get("product_id")) in allowed]
    for field, value in (
        ("environment", environment),
        ("product_id", product_id),
        ("resource_type", resource_type),
        ("status", status),
    ):
        if value is not None:
            items = [item for item in items if item.get(field) == value]
    return [dict(item) for item in items]


def active_execution_resource_grant_keys(
    current_store: Any,
    *,
    environment: str | None,
    product_id: str | None,
    product_scope_ids: list[str] | None,
) -> set[tuple[str, str, str]]:
    return {
        (
            str(grant.get("resource_type") or ""),
            str(grant.get("resource_id") or ""),
            str(grant.get("target_code") or ""),
        )
        for grant in _list_grants(
            current_store,
            environment=environment,
            product_id=product_id,
            product_scope_ids=product_scope_ids,
            status="active",
        )
    }


def require_execution_resource_grant(
    current_store: Any,
    *,
    environment: str,
    product_id: str,
    resource_id: str,
    resource_type: str,
    target_code: str = "",
) -> dict[str, Any]:
    matches = _list_grants(
        current_store,
        environment=environment,
        product_id=product_id,
        resource_type=resource_type,
        status="active",
    )
    normalized_target = target_code if resource_type == "runner_target" else ""
    grant = next(
        (
            item
            for item in matches
            if str(item.get("resource_id")) == resource_id
            and str(item.get("target_code") or "") == normalized_target
        ),
        None,
    )
    if grant is None:
        raise api_error(
            409,
            "EXECUTION_RESOURCE_NOT_GRANTED",
            "Execution resource is not granted to this product and environment",
        )
    return dict(grant)


def _validate_runner_target(
    current_store: Any,
    *,
    resource_id: str,
    target_code: str,
) -> None:
    repository = getattr(current_store, "repository", None)
    list_runners = getattr(repository, "list_ai_executor_runners", None)
    runners = (
        list(list_runners(status="active"))
        if callable(list_runners)
        else read_memory_records(current_store, "ai_executor_runners")
    )
    runner = next(
        (
            item
            for item in runners
            if str(item.get("id")) == resource_id and item.get("status") == "active"
        ),
        None,
    )
    targets = (runner or {}).get("metadata", {}).get("deployment_targets", [])
    if runner is None or not any(
        isinstance(target, dict) and str(target.get("code") or "") == target_code
        for target in targets
    ):
        raise api_error(
            409,
            "EXECUTION_RESOURCE_UNAVAILABLE",
            "Runner deployment target is unavailable",
        )


def _validate_jenkins_connection(current_store: Any, *, resource_id: str) -> None:
    repository = getattr(current_store, "repository", None)
    list_connections = getattr(repository, "list_plugin_connections", None)
    connections = (
        list(list_connections(status="active"))
        if callable(list_connections)
        else read_memory_records(current_store, "plugin_connections")
    )
    connection = next(
        (
            item
            for item in connections
            if str(item.get("id")) == resource_id and item.get("status") == "active"
        ),
        None,
    )
    plugin_code = (connection or {}).get("plugin_code")
    if not plugin_code and connection is not None:
        plugin = read_memory_dict(current_store, "integration_plugins").get(
            str(connection.get("plugin_id") or "")
        )
        plugin_code = (plugin or {}).get("code")
    if connection is None or plugin_code != "jenkins":
        raise api_error(
            409,
            "EXECUTION_RESOURCE_UNAVAILABLE",
            "Jenkins connection is unavailable",
        )


def _save_grant(
    current_store: Any,
    grant: dict[str, Any],
    *,
    audit_event: dict[str, Any],
    expected_version: int | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_execution_resource_grant_record", None)
    if callable(save_record):
        try:
            save_record(
                grant,
                audit_event=audit_event,
                expected_version=expected_version,
            )
        except ExecutionGovernanceVersionConflictError as exc:
            raise api_error(
                409,
                "RESOURCE_VERSION_CONFLICT",
                "Execution resource grant was updated by another user",
                {"current_version": exc.current_version},
            ) from exc
    read_memory_dict(current_store, "execution_resource_grants")[grant["id"]] = grant


def create_execution_resource_grant_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"system.settings.manage"}, {"admin"})
    product_id = ensure_non_blank(payload.product_id, "product_id")
    environment = ensure_non_blank(payload.environment, "environment")
    resource_type = ensure_non_blank(payload.resource_type, "resource_type")
    resource_id = ensure_non_blank(payload.resource_id, "resource_id")
    ensure_enum(resource_type, EXECUTION_RESOURCE_TYPES, "resource_type")
    target_code = (
        ensure_non_blank(payload.target_code, "target_code")
        if resource_type == "runner_target"
        else ""
    )
    if resource_type == "runner_target":
        _validate_runner_target(
            current_store,
            resource_id=resource_id,
            target_code=target_code,
        )
    else:
        _validate_jenkins_connection(current_store, resource_id=resource_id)
    existing = next(
        (
            item
            for item in _list_grants(current_store)
            if item.get("product_id") == product_id
            and item.get("environment") == environment
            and item.get("resource_type") == resource_type
            and item.get("resource_id") == resource_id
            and str(item.get("target_code") or "") == target_code
        ),
        None,
    )
    if existing is not None:
        return dict(existing)
    now = datetime.now(UTC).isoformat()
    grant = {
        "id": current_store.new_id("execution_resource_grant"),
        "product_id": product_id,
        "environment": environment,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "target_code": target_code,
        "status": "active",
        "version": 1,
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now,
    }
    audit = record_audit_event(
        current_store,
        event_type="execution_resource.granted",
        actor_id=user["id"],
        subject_type="execution_resource_grant",
        subject_id=grant["id"],
        payload={
            "environment": environment,
            "product_id": product_id,
            "resource_id": resource_id,
            "resource_type": resource_type,
            "target_code": target_code,
        },
    )
    _save_grant(current_store, grant, audit_event=audit)
    return dict(grant)


def update_execution_resource_grant_response(
    *,
    current_store: Any,
    grant_id: str,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(user, {"system.settings.manage"}, {"admin"})
    grant = read_memory_dict(current_store, "execution_resource_grants").get(grant_id)
    if grant is None:
        grant = next(
            (item for item in _list_grants(current_store) if item.get("id") == grant_id),
            None,
        )
    if grant is None:
        raise api_error(404, "NOT_FOUND", "Execution resource grant not found")
    current_version = int(grant.get("version") or 1)
    if int(payload.version) != current_version:
        raise api_error(
            409,
            "RESOURCE_VERSION_CONFLICT",
            "Execution resource grant was updated by another user",
            {"current_version": current_version},
        )
    ensure_enum(payload.status, EXECUTION_RESOURCE_GRANT_STATUSES, "status")
    updated = {
        **grant,
        "status": payload.status,
        "updated_at": datetime.now(UTC).isoformat(),
        "version": current_version + 1,
    }
    audit = record_audit_event(
        current_store,
        event_type="execution_resource.updated",
        actor_id=user["id"],
        subject_type="execution_resource_grant",
        subject_id=grant_id,
        payload={"previous_status": grant.get("status"), "status": payload.status},
    )
    _save_grant(
        current_store,
        updated,
        audit_event=audit,
        expected_version=current_version,
    )
    return dict(updated)


def list_execution_resource_grants_response(
    *,
    current_store: Any,
    environment: str | None,
    product_id: str | None,
    resource_type: str | None,
    status: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_any_permission_or_roles(
        user,
        {"deployment.scheme.manage"},
        {"admin", "release_owner"},
    )
    ensure_enum(resource_type, EXECUTION_RESOURCE_TYPES, "resource_type")
    ensure_enum(status, EXECUTION_RESOURCE_GRANT_STATUSES, "status")
    if product_id is not None:
        require_product_scope(user, product_id)
    product_scope_ids = (
        None if user_has_global_execution_resource_access(user) else product_scope_filter(user)
    )
    items = _list_grants(
        current_store,
        environment=environment,
        product_id=product_id,
        product_scope_ids=product_scope_ids,
        resource_type=resource_type,
        status=status,
    )
    items.sort(
        key=lambda item: (
            str(item.get("product_id") or ""),
            str(item.get("environment") or ""),
            str(item.get("resource_type") or ""),
            str(item.get("resource_id") or ""),
            str(item.get("target_code") or ""),
        )
    )
    return {"items": items, "total": len(items)}


def ensure_execution_resource_grant_for_binding(
    current_store: Any,
    *,
    environment: str,
    product_id: str,
    resource_id: str,
    resource_type: str,
    target_code: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    try:
        return require_execution_resource_grant(
            current_store,
            environment=environment,
            product_id=product_id,
            resource_id=resource_id,
            resource_type=resource_type,
            target_code=target_code,
        )
    except HTTPException as exc:
        if (
            exc.detail.get("code") != "EXECUTION_RESOURCE_NOT_GRANTED"
            or not user_has_global_execution_resource_access(user)
        ):
            raise
    return create_execution_resource_grant_response(
        current_store=current_store,
        payload=SimpleNamespace(
            environment=environment,
            product_id=product_id,
            resource_id=resource_id,
            resource_type=resource_type,
            target_code=target_code,
        ),
        user=user,
    )
