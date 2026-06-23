from __future__ import annotations

from typing import Any

HIGH_RISK_LEVELS = {"critical", "danger", "high"}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(dict.fromkeys(str(item) for item in value if str(item or "").strip()))


def _scope_summary(scopes: list[dict[str, Any]]) -> str:
    if not scopes:
        return "未配置数据范围"
    grouped: dict[str, int] = {}
    for scope in scopes:
        scope_type = str(scope.get("scope_type") or "unknown")
        grouped[scope_type] = grouped.get(scope_type, 0) + 1
    return "，".join(f"{scope_type} {count} 项" for scope_type, count in sorted(grouped.items()))


def build_rbac_policy_matrix(repository: Any) -> dict[str, Any]:
    permissions = list(repository.list_permissions())
    menus = list(repository.menu_resources())
    roles = list(repository.list_roles())

    permission_by_code = {permission["code"]: permission for permission in permissions}
    menu_by_code = {menu["code"]: menu for menu in menus}

    matrix_rows: list[dict[str, Any]] = []
    for role in roles:
        role_code = str(role.get("code") or "")
        granted_permission_codes = _string_list(
            role.get("permission_codes") or role.get("permissions") or []
        )
        granted_menu_codes = _string_list(role.get("menu_codes") or role.get("menu_scope") or [])
        scopes = [
            dict(scope)
            for scope in role.get("scopes", [])
            if isinstance(scope, dict)
        ]

        required_permission_codes = sorted(
            {
                str(permission_code)
                for menu_code in granted_menu_codes
                for permission_code in menu_by_code.get(menu_code, {}).get(
                    "required_permissions",
                    [],
                )
                if str(permission_code or "").strip()
            }
        )
        missing_menu_permission_codes = sorted(
            set(required_permission_codes) - set(granted_permission_codes)
        )
        standalone_permission_codes = sorted(
            set(granted_permission_codes) - set(required_permission_codes)
        )
        high_risk_permission_codes = sorted(
            permission_code
            for permission_code in granted_permission_codes
            if str(permission_by_code.get(permission_code, {}).get("risk_level") or "").lower()
            in HIGH_RISK_LEVELS
        )

        diagnostics: list[dict[str, Any]] = []
        if missing_menu_permission_codes:
            diagnostics.append(
                {
                    "code": "menu_permission_gap",
                    "level": "warning",
                    "message": "已授权菜单缺少对应权限点",
                    "permission_codes": missing_menu_permission_codes,
                }
            )
        if high_risk_permission_codes:
            diagnostics.append(
                {
                    "code": "high_risk_permission",
                    "level": "risk",
                    "message": "包含高风险权限点",
                    "permission_codes": high_risk_permission_codes,
                }
            )

        matrix_rows.append(
            {
                "role_id": str(role.get("id") or role_code),
                "role_code": role_code,
                "role_name": str(role.get("name") or role_code),
                "category": str(role.get("category") or "workspace"),
                "status": str(role.get("status") or "active"),
                "is_system": bool(role.get("is_system", False)),
                "permission_count": len(granted_permission_codes),
                "granted_permission_codes": granted_permission_codes,
                "high_risk_permission_count": len(high_risk_permission_codes),
                "high_risk_permission_codes": high_risk_permission_codes,
                "menu_count": len(granted_menu_codes),
                "granted_menu_codes": granted_menu_codes,
                "required_permission_codes": required_permission_codes,
                "missing_menu_permission_codes": missing_menu_permission_codes,
                "standalone_permission_codes": standalone_permission_codes,
                "scope_count": len(scopes),
                "scope_summary": _scope_summary(scopes),
                "scopes": scopes,
                "diagnostics": diagnostics,
            }
        )

    active_rows = [row for row in matrix_rows if row["status"] == "active"]
    return {
        "roles": roles,
        "permissions": permissions,
        "menus": menus,
        "rows": matrix_rows,
        "summary": {
            "active_role_count": len(active_rows),
            "menu_count": len(menus),
            "permission_count": len(permissions),
            "role_count": len(roles),
            "roles_with_high_risk_permissions": sum(
                1 for row in matrix_rows if row["high_risk_permission_count"] > 0
            ),
            "roles_with_menu_permission_gaps": sum(
                1 for row in matrix_rows if row["missing_menu_permission_codes"]
            ),
            "scope_grant_count": sum(row["scope_count"] for row in matrix_rows),
        },
    }
