from __future__ import annotations

from typing import Any


def user_product_access(user: dict[str, Any]) -> tuple[bool, set[str]]:
    roles = set(user.get("roles") or [])
    permissions = set(user.get("permissions") or [])
    if "admin" in roles or "system.admin" in permissions:
        return True, set()
    scope_summary = user.get("scope_summary") or []
    if not scope_summary:
        return True, set()

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
        return True, set()
    return False, product_ids


def product_scope_filter(user: dict[str, Any]) -> list[str] | None:
    global_access, product_ids = user_product_access(user)
    return None if global_access else sorted(product_ids)


def user_can_read_product(user: dict[str, Any], product_id: Any) -> bool:
    global_access, product_ids = user_product_access(user)
    if global_access:
        return True
    return product_id is not None and str(product_id) in product_ids
