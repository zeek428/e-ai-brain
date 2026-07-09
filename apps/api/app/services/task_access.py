from __future__ import annotations

from typing import Any

from app.api.deps import api_error, require_any_permission_or_roles
from app.services.product_scope import user_can_read_product


def task_allowed_roles(task: dict[str, Any]) -> set[str]:
    if task["task_type"] == "code_review":
        return {"reviewer", "rd_owner"}
    return {"product_owner", "rd_owner"}


def require_task_permission_or_roles(
    user: dict[str, Any],
    task: dict[str, Any],
    permissions: set[str],
) -> None:
    require_any_permission_or_roles(user, permissions, task_allowed_roles(task))
    if not can_access_task_product(user, task):
        raise api_error(403, "FORBIDDEN", "Insufficient product scope for this AI task")


def can_access_task_product(user: dict[str, Any], task: dict[str, Any]) -> bool:
    user_roles = set(user["roles"])
    user_permissions = set(user.get("permissions") or [])
    if "admin" in user_roles or "system.admin" in user_permissions:
        return True
    if "reviewer" in user_roles and task.get("task_type") == "code_review":
        return True
    return user_can_read_product(user, task.get("product_id"))


def can_read_task(user: dict[str, Any], task: dict[str, Any]) -> bool:
    user_roles = set(user["roles"])
    user_permissions = set(user.get("permissions") or [])
    if "admin" in user_roles or "system.admin" in user_permissions:
        return True
    if not can_access_task_product(user, task):
        return False
    if bool(user_roles.intersection(task_allowed_roles(task))):
        return True
    if "task.read" not in user_permissions:
        return False
    if "product_owner" in user_roles and task.get("task_type") == "code_review":
        return False
    if "reviewer" in user_roles and task.get("task_type") != "code_review":
        return False
    return True


def task_read_scope(user: dict[str, Any]) -> str:
    user_roles = set(user["roles"])
    user_permissions = set(user.get("permissions") or [])
    if "admin" in user_roles or "system.admin" in user_permissions or "rd_owner" in user_roles:
        return "all"
    if "product_owner" in user_roles and "reviewer" in user_roles:
        return "all"
    if "product_owner" in user_roles:
        return "non_code_review"
    if "reviewer" in user_roles:
        return "code_review"
    if "task.read" in user_permissions:
        return "all"
    return "none"
