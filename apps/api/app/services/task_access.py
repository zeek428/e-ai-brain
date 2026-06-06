from __future__ import annotations

from typing import Any


def task_allowed_roles(task: dict[str, Any]) -> set[str]:
    if task["task_type"] == "code_review":
        return {"reviewer", "rd_owner"}
    return {"product_owner", "rd_owner"}


def can_read_task(user: dict[str, Any], task: dict[str, Any]) -> bool:
    user_roles = set(user["roles"])
    return "admin" in user_roles or bool(user_roles.intersection(task_allowed_roles(task)))


def task_read_scope(user: dict[str, Any]) -> str:
    user_roles = set(user["roles"])
    if "admin" in user_roles or "rd_owner" in user_roles:
        return "all"
    if "product_owner" in user_roles and "reviewer" in user_roles:
        return "all"
    if "product_owner" in user_roles:
        return "non_code_review"
    if "reviewer" in user_roles:
        return "code_review"
    return "none"
