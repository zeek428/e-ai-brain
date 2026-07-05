from __future__ import annotations

from typing import Any

from app.api.deps import require_any_permission_or_roles


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


def can_read_task(user: dict[str, Any], task: dict[str, Any]) -> bool:
    user_roles = set(user["roles"])
    user_permissions = set(user.get("permissions") or [])
    if "admin" in user_roles or "system.admin" in user_permissions:
        return True
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
