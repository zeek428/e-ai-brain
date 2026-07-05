from __future__ import annotations

from typing import Any

from app.api.deps import require_any_permission, require_permissions
from app.services.scheduled_job_catalog import (
    SCHEDULED_JOB_MANAGE_PERMISSION,
    SCHEDULED_JOB_RUN_PERMISSION,
)
from app.services.scheduled_job_store import read_memory_dict


def require_admin(user: dict[str, Any]) -> None:
    require_permissions(user, {SCHEDULED_JOB_MANAGE_PERMISSION})


def require_scheduled_job_runner(user: dict[str, Any]) -> None:
    require_any_permission(
        user,
        {SCHEDULED_JOB_MANAGE_PERMISSION, SCHEDULED_JOB_RUN_PERMISSION},
    )


def user_product_access(user: dict[str, Any]) -> tuple[bool, set[str]]:
    roles = set(user.get("roles") or [])
    permissions = set(user.get("permissions") or [])
    if "admin" in roles or "system.admin" in permissions:
        return True, set()
    scope_summary = user.get("scope_summary") or []
    if not scope_summary:
        return False, set()
    product_ids: set[str] = set()
    has_product_scope = False
    for scope in scope_summary:
        if not isinstance(scope, dict):
            continue
        if scope.get("access_level") not in {"admin", "read", "write"}:
            continue
        scope_type = scope.get("scope_type")
        scope_id = scope.get("scope_id")
        if scope_type == "global" and scope_id == "*":
            return True, set()
        if scope_type == "product" and scope_id:
            has_product_scope = True
            product_ids.add(str(scope_id))
    if not has_product_scope:
        return False, set()
    return False, product_ids


def user_can_access_scheduled_job_product(user: dict[str, Any], product_id: Any) -> bool:
    if product_id is None:
        return True
    global_access, product_ids = user_product_access(user)
    if global_access:
        return True
    return product_id is not None and str(product_id) in product_ids


def scheduled_job_product_scope_filter(user: dict[str, Any]) -> list[str] | None:
    global_access, product_ids = user_product_access(user)
    return None if global_access else sorted(product_ids)


def scheduled_job_matches_product_scope(job: dict[str, Any], user: dict[str, Any]) -> bool:
    return user_can_access_scheduled_job_product(user, job.get("product_id"))


def scheduled_job_run_product_id(
    current_store: Any,
    run: dict[str, Any],
) -> Any:
    job_id = run.get("scheduled_job_id")
    if job_id:
        job = read_memory_dict(current_store, "scheduled_jobs").get(str(job_id))
        if isinstance(job, dict) and job.get("product_id") is not None:
            return job.get("product_id")
    config_snapshot = run.get("config_snapshot")
    if isinstance(config_snapshot, dict):
        return config_snapshot.get("product_id")
    return None


def scheduled_job_run_matches_product_scope(
    current_store: Any,
    run: dict[str, Any],
    user: dict[str, Any],
) -> bool:
    return user_can_access_scheduled_job_product(
        user,
        scheduled_job_run_product_id(current_store, run),
    )


def scheduled_job_plugin_invocation_user(user: dict[str, Any]) -> dict[str, Any]:
    permissions = set(user.get("permissions") or [])
    permissions.add("system.plugins.manage")
    # Running a configured job authorizes invoking its bound action; direct plugin APIs
    # still require plugin management permission at the router/service boundary.
    return {**user, "permissions": sorted(permissions)}
