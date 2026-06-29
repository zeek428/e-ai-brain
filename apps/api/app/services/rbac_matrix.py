from __future__ import annotations

from typing import Any

HIGH_RISK_LEVELS = {"critical", "danger", "high"}
SCOPE_TYPE_LABELS = {
    "department": "部门",
    "global": "全局",
    "knowledge_space": "知识空间",
    "product": "产品",
    "review_assignment": "评审任务",
}
SCOPE_TYPE_SORT_ORDER = {
    "global": 0,
    "department": 1,
    "knowledge_space": 2,
    "product": 3,
    "review_assignment": 4,
}
ScopeResourceNames = dict[str, dict[str, str]]


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
    return "，".join(
        f"{_scope_type_label(scope_type)} {count} 项"
        for scope_type, count in sorted(
            grouped.items(),
            key=lambda item: (SCOPE_TYPE_SORT_ORDER.get(item[0], 99), _scope_type_label(item[0])),
        )
    )


def _scope_type_label(scope_type: str) -> str:
    return SCOPE_TYPE_LABELS.get(scope_type, scope_type)


def _scope_sort_key(scope: dict[str, Any]) -> tuple[int, str, str, str]:
    scope_type = str(scope.get("scope_type") or "unknown")
    return (
        SCOPE_TYPE_SORT_ORDER.get(scope_type, 99),
        str(scope.get("scope_name") or ""),
        str(scope.get("scope_id") or ""),
        str(scope.get("access_level") or ""),
    )


def _enrich_scopes(
    scopes: list[dict[str, Any]],
    *,
    scope_resource_names: ScopeResourceNames | None = None,
) -> list[dict[str, Any]]:
    resource_names = scope_resource_names or {}
    enriched_scopes: list[dict[str, Any]] = []
    for scope in scopes:
        enriched = dict(scope)
        scope_type = str(enriched.get("scope_type") or "unknown")
        scope_id = str(enriched.get("scope_id") or "")
        scope_name = str(
            resource_names.get(scope_type, {}).get(scope_id)
            or enriched.get("scope_name")
            or ""
        ).strip()
        if scope_name:
            enriched["scope_name"] = scope_name
        enriched_scopes.append(enriched)
    return sorted(enriched_scopes, key=_scope_sort_key)


def _role_grant_reasons(
    roles: list[dict[str, Any]],
    role_codes: list[str],
    *,
    field: str,
    target: str,
) -> list[dict[str, str]]:
    fallback_fields = {
        "menu_codes": ("menu_codes", "menu_scope"),
        "permission_codes": ("permission_codes", "permissions"),
    }
    role_code_set = set(role_codes)
    reasons: list[dict[str, str]] = []
    for role in roles:
        role_code = str(role.get("code") or "")
        if role_code not in role_code_set or str(role.get("status") or "active") != "active":
            continue
        values = _string_list(
            [
                value
                for current_field in fallback_fields.get(field, (field,))
                for value in _string_list(role.get(current_field) or [])
            ]
        )
        if target in values:
            reasons.append(
                {
                    "role_code": role_code,
                    "role_name": str(role.get("name") or role_code),
                }
            )
    return reasons


def _scope_matches(scope: dict[str, Any], *, scope_type: str, scope_id: str) -> bool:
    current_type = str(scope.get("scope_type") or "")
    current_id = str(scope.get("scope_id") or "")
    if current_type == "global" and current_id == "*":
        return True
    if current_type != scope_type:
        return False
    return current_id in {scope_id, "*"}


def _check_status(status: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"message": message, "status": status, **extra}


def build_user_permission_diagnostic(
    repository: Any,
    target_user: dict[str, Any],
    *,
    path: str | None = None,
    permission_code: str | None = None,
    scope_type: str | None = None,
    scope_id: str | None = None,
    scope_resource_names: ScopeResourceNames | None = None,
) -> dict[str, Any]:
    """Explain why a user can or cannot access a menu, permission, or scope."""

    effective = repository.effective_permissions_for_user(target_user)
    roles = list(repository.list_roles())
    menus = list(repository.menu_resources())
    permissions = list(repository.list_permissions())
    role_codes = _string_list(effective.get("role_codes") or [])
    permission_codes = _string_list(effective.get("permission_codes") or [])
    menu_codes = _string_list(effective.get("menu_codes") or [])
    scopes = _enrich_scopes(
        [
            dict(scope)
            for scope in effective.get("scopes", [])
            if isinstance(scope, dict)
        ],
        scope_resource_names=scope_resource_names,
    )
    user_status = str(target_user.get("status") or "active")

    checks: list[dict[str, Any]] = [
        {
            "code": "user_status",
            **_check_status(
                "allowed" if user_status == "active" else "blocked",
                (
                    "用户状态为启用"
                    if user_status == "active"
                    else "用户状态不是启用，运行时不可登录或访问业务入口"
                ),
                target=user_status,
            ),
        },
        {
            "code": "roles",
            **_check_status(
                "allowed" if role_codes else "blocked",
                f"用户拥有 {len(role_codes)} 个角色" if role_codes else "用户未分配任何角色",
                role_codes=role_codes,
            ),
        },
    ]

    blocked_reasons: list[str] = []
    granted_reasons: list[str] = []
    if user_status != "active":
        blocked_reasons.append("用户状态不是启用")
    if not role_codes:
        blocked_reasons.append("用户未分配角色")
    else:
        granted_reasons.append(f"角色：{', '.join(role_codes)}")

    normalized_path = str(path or "").strip()
    if normalized_path:
        matched_menu = next(
            (
                menu
                for menu in menus
                if str(menu.get("path") or "").strip() == normalized_path
                and str(menu.get("status") or "active") == "active"
            ),
            None,
        )
        if matched_menu is None:
            checks.append(
                {
                    "code": "menu_path",
                    **_check_status(
                        "blocked",
                        "没有找到启用状态的菜单资源，请检查菜单管理是否配置该路由",
                        target=normalized_path,
                    ),
                }
            )
            blocked_reasons.append(f"菜单未配置：{normalized_path}")
        else:
            menu_code = str(matched_menu.get("code") or "")
            required_permission_codes = _string_list(matched_menu.get("required_permissions") or [])
            missing_permission_codes = sorted(
                set(required_permission_codes) - set(permission_codes)
            )
            menu_role_reasons = _role_grant_reasons(
                roles,
                role_codes,
                field="menu_codes",
                target=menu_code,
            )
            has_menu_grant = menu_code in menu_codes
            status = "allowed" if has_menu_grant and not missing_permission_codes else "blocked"
            checks.append(
                {
                    "code": "menu_path",
                    **_check_status(
                        status,
                        (
                            "菜单可见且所需权限满足"
                            if status == "allowed"
                            else "菜单不可见或缺少所需权限"
                        ),
                        granted_by_roles=menu_role_reasons,
                        granted_menu_code=menu_code if has_menu_grant else None,
                        matched_menu={
                            "code": menu_code,
                            "name": matched_menu.get("name"),
                            "path": matched_menu.get("path"),
                        },
                        missing_permission_codes=missing_permission_codes,
                        required_permission_codes=required_permission_codes,
                        target=normalized_path,
                    ),
                }
            )
            if status == "allowed":
                granted_reasons.append(f"菜单可见：{menu_code}")
            else:
                if not has_menu_grant:
                    blocked_reasons.append(f"未授予菜单：{menu_code}")
                if missing_permission_codes:
                    blocked_reasons.append(f"缺少菜单权限：{', '.join(missing_permission_codes)}")

    normalized_permission = str(permission_code or "").strip()
    if normalized_permission:
        known_permission = next(
            (
                permission
                for permission in permissions
                if permission.get("code") == normalized_permission
            ),
            None,
        )
        permission_role_reasons = _role_grant_reasons(
            roles,
            role_codes,
            field="permission_codes",
            target=normalized_permission,
        )
        has_permission = normalized_permission in permission_codes
        status = "allowed" if has_permission else "blocked"
        checks.append(
            {
                "code": "permission",
                **_check_status(
                    status,
                    "用户拥有该权限点" if has_permission else "用户未拥有该权限点",
                    granted_by_roles=permission_role_reasons,
                    known=known_permission is not None,
                    permission={
                        "code": normalized_permission,
                        "name": (
                            known_permission.get("name")
                            if known_permission
                            else normalized_permission
                        ),
                        "risk_level": (
                            known_permission.get("risk_level") if known_permission else None
                        ),
                    },
                    target=normalized_permission,
                ),
            }
        )
        if has_permission:
            granted_reasons.append(f"权限点：{normalized_permission}")
        else:
            blocked_reasons.append(f"缺少权限点：{normalized_permission}")

    normalized_scope_type = str(scope_type or "").strip()
    normalized_scope_id = str(scope_id or "").strip()
    if normalized_scope_type or normalized_scope_id:
        if not normalized_scope_type or not normalized_scope_id:
            checks.append(
                {
                    "code": "scope",
                    **_check_status(
                        "blocked",
                        "范围诊断需要同时填写范围类型和范围 ID",
                        target=f"{normalized_scope_type}:{normalized_scope_id}",
                    ),
                }
            )
            blocked_reasons.append("范围诊断参数不完整")
        else:
            matched_scopes = [
                scope
                for scope in scopes
                if _scope_matches(
                    scope,
                    scope_type=normalized_scope_type,
                    scope_id=normalized_scope_id,
                )
            ]
            has_scope = bool(matched_scopes)
            checks.append(
                {
                    "code": "scope",
                    **_check_status(
                        "allowed" if has_scope else "blocked",
                        "数据范围覆盖目标资源" if has_scope else "数据范围未覆盖目标资源",
                        matched_scopes=matched_scopes,
                        target=f"{normalized_scope_type}:{normalized_scope_id}",
                    ),
                }
            )
            if has_scope:
                granted_reasons.append(f"范围：{normalized_scope_type}:{normalized_scope_id}")
            else:
                blocked_reasons.append(f"缺少范围：{normalized_scope_type}:{normalized_scope_id}")

    allowed = not blocked_reasons and any(check["status"] == "allowed" for check in checks)
    return {
        "checks": checks,
        "decision": {
            "allowed": allowed,
            "blocked_reasons": blocked_reasons,
            "granted_reasons": granted_reasons,
        },
        "effective": {
            "menu_codes": menu_codes,
            "permission_codes": permission_codes,
            "role_codes": role_codes,
            "scopes": scopes,
        },
        "user": {
            "display_name": target_user.get("display_name"),
            "id": str(target_user.get("id") or ""),
            "roles": role_codes,
            "status": user_status,
            "username": target_user.get("username"),
        },
    }


def build_rbac_policy_matrix(
    repository: Any,
    *,
    scope_resource_names: ScopeResourceNames | None = None,
) -> dict[str, Any]:
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
        scopes = _enrich_scopes(
            [
                dict(scope)
                for scope in role.get("scopes", [])
                if isinstance(scope, dict)
            ],
            scope_resource_names=scope_resource_names,
        )

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
