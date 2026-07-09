from __future__ import annotations

from typing import Any

from app.core.authorization import build_menu_tree

HIGH_RISK_LEVELS = {"critical", "danger", "high"}
RISK_SEVERITY_ORDER = {"info": 0, "warning": 1, "risk": 2, "blocked": 3}
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


def _permission_sort_key(permission: dict[str, Any]) -> tuple[str, str]:
    return (
        str(permission.get("category") or ""),
        str(permission.get("code") or ""),
    )


def _menu_sort_key(menu: dict[str, Any]) -> tuple[int, str, str]:
    return (
        int(menu.get("sort_order") or 0),
        str(menu.get("parent_code") or ""),
        str(menu.get("code") or ""),
    )


def _scope_groups(scopes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for scope in scopes:
        scope_type = str(scope.get("scope_type") or "unknown")
        grouped.setdefault(scope_type, []).append(scope)
    return [
        {
            "count": len(items),
            "scope_type": scope_type,
            "scope_type_label": _scope_type_label(scope_type),
            "scopes": items,
        }
        for scope_type, items in sorted(
            grouped.items(),
            key=lambda item: (
                SCOPE_TYPE_SORT_ORDER.get(item[0], 99),
                _scope_type_label(item[0]),
            ),
        )
    ]


def _flatten_menu_tree(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for node in nodes:
        flattened.append(
            {
                "code": node.get("code"),
                "name": node.get("name"),
                "path": node.get("path"),
            }
        )
        flattened.extend(_flatten_menu_tree(node.get("children") or []))
    return flattened


def _scope_access_counts(scopes: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for scope in scopes:
        scope_type = str(scope.get("scope_type") or "unknown")
        access_level = str(scope.get("access_level") or "read")
        by_level = counts.setdefault(scope_type, {"admin": 0, "read": 0, "write": 0})
        by_level[access_level] = by_level.get(access_level, 0) + 1
    return counts


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


def build_user_menu_preview(
    repository: Any,
    target_user: dict[str, Any],
    *,
    scope_resource_names: ScopeResourceNames | None = None,
) -> dict[str, Any]:
    """Render the exact menu tree a target user can see, plus blocked menu evidence."""

    effective = repository.effective_permissions_for_user(target_user)
    menus = list(repository.menu_resources())
    menu_by_code = {str(menu.get("code") or ""): menu for menu in menus}
    permission_codes = set(_string_list(effective.get("permission_codes") or []))
    granted_menu_codes = set(_string_list(effective.get("menu_codes") or []))
    menu_tree = build_menu_tree(
        granted_codes=granted_menu_codes,
        permissions=permission_codes,
        resources=menus,
    )
    visible_menus = _flatten_menu_tree(menu_tree)
    visible_menu_codes = {
        str(menu.get("code") or "")
        for menu in visible_menus
        if str(menu.get("code") or "").strip()
    }
    blocked_menus: list[dict[str, Any]] = []
    for menu_code in sorted(granted_menu_codes - visible_menu_codes):
        menu = menu_by_code.get(menu_code)
        if menu is None:
            blocked_menus.append(
                {
                    "code": menu_code,
                    "message": "菜单授权存在，但菜单资源不存在",
                    "reason": "menu_missing",
                }
            )
            continue
        required_permissions = _string_list(menu.get("required_permissions") or [])
        missing_permissions = sorted(set(required_permissions) - permission_codes)
        if str(menu.get("status") or "active") != "active":
            reason = "menu_inactive"
            message = "菜单已授权，但当前菜单状态不是启用"
        elif missing_permissions:
            reason = "permission_missing"
            message = "菜单已授权，但缺少菜单所需权限点"
        elif str(menu.get("menu_type") or "") == "hidden_page":
            reason = "hidden_page"
            message = "隐藏页面不在导航树中展示"
        else:
            reason = "parent_hidden"
            message = "菜单父级不可见或无可展示子节点"
        blocked_menus.append(
            {
                "code": menu_code,
                "message": message,
                "missing_permission_codes": missing_permissions,
                "name": menu.get("name"),
                "path": menu.get("path"),
                "reason": reason,
                "required_permission_codes": required_permissions,
            }
        )
    scopes = _enrich_scopes(
        [
            dict(scope)
            for scope in effective.get("scopes", [])
            if isinstance(scope, dict)
        ],
        scope_resource_names=scope_resource_names,
    )
    return {
        "blocked_menus": blocked_menus,
        "effective": {
            "menu_codes": sorted(granted_menu_codes),
            "permission_codes": sorted(permission_codes),
            "role_codes": _string_list(effective.get("role_codes") or []),
            "scopes": scopes,
        },
        "menu_tree": menu_tree,
        "scope_summary": _scope_summary(scopes),
        "summary": {
            "blocked_menu_count": len(blocked_menus),
            "granted_menu_count": len(granted_menu_codes),
            "visible_menu_count": len(visible_menu_codes),
        },
        "user": {
            "display_name": target_user.get("display_name"),
            "id": str(target_user.get("id") or ""),
            "roles": _string_list(effective.get("role_codes") or []),
            "status": str(target_user.get("status") or "active"),
            "username": target_user.get("username"),
        },
        "visible_menu_codes": sorted(visible_menu_codes),
        "visible_menus": visible_menus,
    }


def build_role_access_preview(
    repository: Any,
    role: dict[str, Any],
    *,
    scope_resource_names: ScopeResourceNames | None = None,
) -> dict[str, Any]:
    """Project a single role into readable menu, permission, scope, and risk previews."""

    permissions = list(repository.list_permissions())
    menus = list(repository.menu_resources())
    permission_by_code = {
        str(permission.get("code") or ""): permission for permission in permissions
    }
    menu_by_code = {str(menu.get("code") or ""): menu for menu in menus}

    granted_permission_codes = _string_list(
        role.get("permission_codes") or role.get("permissions") or [],
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
            for permission_code in menu_by_code.get(menu_code, {}).get("required_permissions", [])
            if str(permission_code or "").strip()
        }
    )
    missing_menu_permission_codes = sorted(
        set(required_permission_codes) - set(granted_permission_codes)
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
    if not scopes:
        diagnostics.append(
            {
                "code": "scope_not_configured",
                "level": "warning",
                "message": "未配置产品、知识空间或全局数据范围",
                "permission_codes": [],
            }
        )

    visible_menus = [
        {
            "code": str(menu.get("code") or menu_code),
            "menu_type": str(menu.get("menu_type") or "page"),
            "name": str(menu.get("name") or menu_code),
            "parent_code": menu.get("parent_code"),
            "path": menu.get("path"),
            "required_permissions": _string_list(menu.get("required_permissions") or []),
            "sort_order": int(menu.get("sort_order") or 0),
            "status": str(menu.get("status") or "active"),
        }
        for menu_code in granted_menu_codes
        if (menu := menu_by_code.get(menu_code)) is not None
    ]
    visible_menus.sort(key=_menu_sort_key)

    operation_permissions = [
        {
            "category": str(permission.get("category") or ""),
            "code": str(permission.get("code") or permission_code),
            "description": str(permission.get("description") or ""),
            "name": str(permission.get("name") or permission_code),
            "risk_level": str(permission.get("risk_level") or "normal"),
            "status": str(permission.get("status") or "active"),
        }
        for permission_code in granted_permission_codes
        for permission in [permission_by_code.get(permission_code, {"code": permission_code})]
    ]
    operation_permissions.sort(key=_permission_sort_key)

    return {
        "diagnostics": diagnostics,
        "granted_menu_codes": granted_menu_codes,
        "granted_permission_codes": granted_permission_codes,
        "high_risk_permission_codes": high_risk_permission_codes,
        "high_risk_permission_count": len(high_risk_permission_codes),
        "menu_count": len(granted_menu_codes),
        "missing_menu_permission_codes": missing_menu_permission_codes,
        "operation_permissions": operation_permissions,
        "permission_count": len(granted_permission_codes),
        "required_permission_codes": required_permission_codes,
        "role_code": str(role.get("code") or ""),
        "role_id": str(role.get("id") or role.get("code") or ""),
        "role_name": str(role.get("name") or role.get("code") or ""),
        "scope_count": len(scopes),
        "scope_groups": _scope_groups(scopes),
        "scope_summary": _scope_summary(scopes),
        "scopes": scopes,
        "visible_menus": visible_menus,
    }


def build_role_risk_precheck(
    repository: Any,
    role: dict[str, Any],
    *,
    menu_codes: list[str] | None = None,
    permission_codes: list[str] | None = None,
    scope_resource_names: ScopeResourceNames | None = None,
    scopes: list[dict[str, Any]] | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """Preview role risks before persisting menu, permission, or scope changes."""

    current_preview = build_role_access_preview(
        repository,
        role,
        scope_resource_names=scope_resource_names,
    )
    candidate_role = {
        **role,
        "menu_codes": _string_list(
            menu_codes if menu_codes is not None else role.get("menu_codes") or role.get("menu_scope") or []
        ),
        "permission_codes": _string_list(
            permission_codes
            if permission_codes is not None
            else role.get("permission_codes") or role.get("permissions") or []
        ),
        "permissions": _string_list(
            permission_codes
            if permission_codes is not None
            else role.get("permission_codes") or role.get("permissions") or []
        ),
        "scopes": [
            dict(scope)
            for scope in (
                scopes if scopes is not None else role.get("scopes", [])
            )
            if isinstance(scope, dict)
        ],
        "status": status or str(role.get("status") or "active"),
    }
    candidate_preview = build_role_access_preview(
        repository,
        candidate_role,
        scope_resource_names=scope_resource_names,
    )

    risks: list[dict[str, Any]] = []
    auto_fix_suggestions: list[dict[str, Any]] = []
    for diagnostic in candidate_preview.get("diagnostics") or []:
        code = str(diagnostic.get("code") or "")
        level = str(diagnostic.get("level") or "warning")
        severity = "blocked" if code == "menu_permission_gap" else level
        risk = {
            **diagnostic,
            "severity": severity,
        }
        risks.append(risk)
        if code == "menu_permission_gap":
            missing_permissions = _string_list(diagnostic.get("permission_codes") or [])
            auto_fix_suggestions.append(
                {
                    "action": "add_permissions",
                    "description": "补齐菜单所需权限点，避免菜单可见但接口 Forbidden。",
                    "permission_codes": missing_permissions,
                }
            )
        elif code == "scope_not_configured":
            auto_fix_suggestions.append(
                {
                    "action": "configure_scope",
                    "description": "为角色配置产品、知识空间或全局 scope，避免只能看到入口但查不到数据。",
                    "scope_examples": [
                        {"access_level": "read", "scope_id": "<product_id>", "scope_type": "product"},
                        {"access_level": "read", "scope_id": "*", "scope_type": "global"},
                    ],
                }
            )
        elif code == "high_risk_permission":
            auto_fix_suggestions.append(
                {
                    "action": "review_high_risk_permissions",
                    "description": "保存前复核高风险权限是否确实需要，必要时拆分为更小角色。",
                    "permission_codes": _string_list(diagnostic.get("permission_codes") or []),
                }
            )
    if candidate_role["status"] != "active":
        risks.append(
            {
                "code": "role_inactive",
                "level": "warning",
                "message": "角色保存为停用状态，用户不会获得该角色权限。",
                "severity": "warning",
            }
        )
    highest = max(
        (RISK_SEVERITY_ORDER.get(str(risk.get("severity") or "warning"), 1) for risk in risks),
        default=0,
    )
    decision_status = "blocked" if highest >= 3 else ("warning" if highest else "pass")
    return {
        "auto_fix_suggestions": auto_fix_suggestions,
        "candidate": candidate_preview,
        "current": current_preview,
        "decision": {
            "can_save": decision_status != "blocked",
            "risk_count": len(risks),
            "status": decision_status,
        },
        "risks": risks,
        "scope_comparison": {
            "current": _scope_access_counts(current_preview.get("scopes") or []),
            "candidate": _scope_access_counts(candidate_preview.get("scopes") or []),
        },
    }


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
