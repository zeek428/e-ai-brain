from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AuthorizationSnapshot:
    user_id: str
    roles: list[str]
    permissions: set[str] = field(default_factory=set)
    scopes: list[dict[str, Any]] = field(default_factory=list)
    menus: list[dict[str, Any]] = field(default_factory=list)


def has_permission(snapshot: AuthorizationSnapshot, permission_code: str) -> bool:
    return (
        "admin" in snapshot.roles
        or permission_code in snapshot.permissions
        or "system.admin" in snapshot.permissions
    )


def build_menu_tree(
    *,
    granted_codes: set[str],
    resources: list[dict[str, Any]],
    permissions: set[str],
) -> list[dict[str, Any]]:
    by_code = {
        item["code"]: item
        for item in resources
        if item.get("status", "active") == "active"
    }
    sorted_resources = sorted(
        by_code.values(),
        key=lambda row: (row.get("sort_order", 0), row["code"]),
    )
    visible_codes: set[str] = set()

    def is_allowed(item: dict[str, Any]) -> bool:
        required_permissions = set(item.get("required_permissions") or [])
        return not required_permissions or required_permissions.issubset(permissions)

    for code in granted_codes:
        item = by_code.get(code)
        if item is None or not is_allowed(item):
            continue

        current_code: str | None = code
        while current_code:
            current = by_code.get(current_code)
            if current is None or not is_allowed(current):
                break
            visible_codes.add(current_code)
            current_code = current.get("parent_code")

    def build_node(item: dict[str, Any]) -> dict[str, Any]:
        children = [
            build_node(child)
            for child in sorted_resources
            if child.get("parent_code") == item["code"]
            and child["code"] in visible_codes
            and child.get("menu_type") != "hidden_page"
        ]
        return {
            "code": item["code"],
            "name": item["name"],
            "path": item.get("path"),
            "children": children,
        }

    roots = [
        item
        for item in sorted_resources
        if item["code"] in visible_codes
        and not item.get("parent_code")
        and item.get("menu_type") != "hidden_page"
    ]
    return [build_node(item) for item in roots]
