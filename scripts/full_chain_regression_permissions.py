from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from full_chain_regression_slug import regression_slug


@dataclass
class StepResult:
    name: str
    detail: str


def _slug() -> str:
    return regression_slug()


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _assert_contains(values: set[str], expected: str, message: str) -> None:
    _assert(expected in values, f"{message}: expected {expected}, got {sorted(values)}")


def validate_permission_visibility_quick_regression(
    client: Any,
    *,
    username: str,
    password: str,
) -> list[StepResult]:
    slug = _slug()
    code_suffix = slug.replace("-", "_")
    results: list[StepResult] = []

    user = client.login(username, password).get("user", {})
    results.append(StepResult("login", f"logged in as {user.get('username') or username}"))

    scoped_product = client.post(
        "/api/products",
        {
            "code": f"permission-scope-{slug}",
            "description": "权限可视化快速回归脚本创建的产品范围。",
            "name": f"权限可视化产品范围 {slug}",
            "status": "active",
        },
    )
    blocked_product = client.post(
        "/api/products",
        {
            "code": f"permission-blocked-{slug}",
            "description": "权限可视化快速回归脚本创建的未授权产品范围。",
            "name": f"权限可视化未授权产品 {slug}",
            "status": "active",
        },
    )
    knowledge_space = client.post(
        "/api/knowledge/spaces",
        {
            "code": f"permission-space-{slug}",
            "description": "权限可视化快速回归脚本创建的知识空间范围。",
            "name": f"权限可视化知识空间 {slug}",
        },
    )
    results.append(
        StepResult(
            "permission_visibility_scope_resources",
            f"{scoped_product['id']} / {knowledge_space['id']}",
        )
    )

    gap_role_code = f"perm_gap_{code_suffix}"
    gap_role = client.post(
        "/api/system/roles",
        {
            "category": "workspace",
            "code": gap_role_code,
            "description": "权限可视化快速回归：菜单已授权但缺少权限点。",
            "name": f"权限可视化菜单缺口 {slug}",
        },
    )
    client.request(
        "PUT",
        f"/api/system/roles/{gap_role['id']}/menus",
        body={"menu_codes": ["workspace.dashboard"]},
    )

    scope_role_code = f"perm_scope_{code_suffix}"
    scope_role = client.post(
        "/api/system/roles",
        {
            "category": "workspace",
            "code": scope_role_code,
            "description": "权限可视化快速回归：产品和知识空间范围投影。",
            "name": f"权限可视化范围角色 {slug}",
        },
    )
    client.request(
        "PUT",
        f"/api/system/roles/{scope_role['id']}/menus",
        body={"menu_codes": ["task.center"]},
    )
    client.request(
        "PUT",
        f"/api/system/roles/{scope_role['id']}/scopes",
        body={
            "scopes": [
                {
                    "access_level": "read",
                    "scope_id": scoped_product["id"],
                    "scope_type": "product",
                },
                {
                    "access_level": "read",
                    "scope_id": knowledge_space["id"],
                    "scope_type": "knowledge_space",
                },
            ]
        },
    )
    results.append(
        StepResult(
            "permission_visibility_roles",
            f"{gap_role_code} / {scope_role_code}",
        )
    )

    listed_roles = client.get(
        "/api/system/roles",
        {
            "page": 1,
            "page_size": 10,
            "role": code_suffix,
            "sort_by": "code",
            "sort_order": "asc",
            "status": "active",
        },
    )
    role_codes = {str(item.get("code") or "") for item in listed_roles.get("items", [])}
    _assert_contains(role_codes, gap_role_code, "Role list missed permission gap role")
    _assert_contains(role_codes, scope_role_code, "Role list missed scoped role")
    _assert(
        listed_roles.get("performance"),
        f"Role list did not include observability metadata: {listed_roles}",
    )
    _assert(
        (listed_roles.get("query") or {}).get("sort_by") == "code",
        f"Role list did not echo remote sort field: {listed_roles}",
    )

    matrix = client.get("/api/system/permissions/matrix")
    matrix_rows = matrix.get("rows") or []
    gap_row = next(
        (row for row in matrix_rows if row.get("role_code") == gap_role_code),
        None,
    )
    _assert(gap_row is not None, f"Permission matrix missed gap role: {matrix_rows}")
    _assert(
        "workspace.read" in set(gap_row.get("missing_menu_permission_codes") or []),
        f"Permission matrix missed workspace.read menu gap: {gap_row}",
    )
    _assert(
        any(item.get("code") == "menu_permission_gap" for item in gap_row.get("diagnostics") or []),
        f"Permission matrix missed menu_permission_gap diagnostic: {gap_row}",
    )

    scope_row = next(
        (row for row in matrix_rows if row.get("role_code") == scope_role_code),
        None,
    )
    _assert(scope_row is not None, f"Permission matrix missed scoped role: {matrix_rows}")
    scope_entries = scope_row.get("scopes") or []
    product_scope = next(
        (
            scope
            for scope in scope_entries
            if scope.get("scope_type") == "product"
            and scope.get("scope_id") == scoped_product["id"]
        ),
        None,
    )
    knowledge_scope = next(
        (
            scope
            for scope in scope_entries
            if scope.get("scope_type") == "knowledge_space"
            and scope.get("scope_id") == knowledge_space["id"]
        ),
        None,
    )
    _assert(
        product_scope and product_scope.get("scope_name") == scoped_product["name"],
        f"Permission matrix missed product scope name: {scope_row}",
    )
    _assert(
        knowledge_scope and knowledge_scope.get("scope_name") == knowledge_space["name"],
        f"Permission matrix missed knowledge space scope name: {scope_row}",
    )
    _assert(
        "产品 1 项" in str(scope_row.get("scope_summary") or "")
        and "知识空间 1 项" in str(scope_row.get("scope_summary") or ""),
        f"Permission matrix missed readable scope summary: {scope_row}",
    )
    _assert(
        int((matrix.get("summary") or {}).get("roles_with_menu_permission_gaps") or 0) >= 1,
        f"Permission matrix summary missed menu gap count: {matrix.get('summary')}",
    )
    results.append(
        StepResult(
            "permission_visibility_matrix",
            (
                f"gap={gap_row.get('missing_menu_permission_codes')} / "
                f"scopes={scope_row.get('scope_summary')}"
            ),
        )
    )

    role_detail = client.get(f"/api/system/roles/{scope_role['id']}")
    _assert(
        str(role_detail.get("code") or "") == scope_role_code,
        f"Role detail returned the wrong role: {role_detail}",
    )
    _assert(
        any(scope.get("scope_id") == scoped_product["id"] for scope in role_detail.get("scopes") or []),
        f"Role detail missed product scope grant: {role_detail}",
    )
    access_preview = role_detail.get("access_preview") or {}
    _assert(
        access_preview.get("role_code") == scope_role_code,
        f"Role detail access preview missed role code: {role_detail}",
    )
    _assert(
        any(
            menu.get("code") == "task.center" and menu.get("path") == "/delivery/rd-tasks"
            for menu in access_preview.get("visible_menus") or []
        ),
        f"Role detail access preview missed visible menu path: {access_preview}",
    )
    _assert(
        access_preview.get("missing_menu_permission_codes") == ["task.read"],
        f"Role detail access preview missed menu permission gap: {access_preview}",
    )
    _assert(
        any(item.get("code") == "menu_permission_gap" for item in access_preview.get("diagnostics") or []),
        f"Role detail access preview missed menu gap diagnostic: {access_preview}",
    )
    _assert(
        not access_preview.get("operation_permissions"),
        f"Role detail access preview should show no granted operation permissions: {access_preview}",
    )
    _assert(
        {group.get("scope_type") for group in access_preview.get("scope_groups") or []}
        >= {"knowledge_space", "product"},
        f"Role detail access preview missed scope groups: {access_preview}",
    )
    _assert(
        any(
            scope.get("scope_id") == scoped_product["id"]
            and scope.get("scope_name") == scoped_product["name"]
            for scope in access_preview.get("scopes") or []
        ),
        f"Role detail access preview missed readable product scope: {access_preview}",
    )
    results.append(
        StepResult(
            "permission_visibility_role_preview",
            (
                f"menus={access_preview.get('menu_count')} / "
                f"scopes={access_preview.get('scope_summary')}"
            ),
        )
    )

    diagnostic_user = client.post(
        "/api/users",
        {
            "display_name": f"权限诊断用户 {slug}",
            "password": "diagnostic123",
            "roles": ["viewer"],
            "status": "active",
            "username": f"permission-visibility-{slug}@example.com",
        },
    )
    client.request(
        "PUT",
        f"/api/users/{diagnostic_user['id']}/roles",
        body={"role_codes": [scope_role_code]},
    )
    diagnostic = client.get(
        "/api/system/permissions/diagnostics",
        {
            "path": "/delivery/rd-tasks",
            "permission_code": "task.read",
            "scope_id": blocked_product["id"],
            "scope_type": "product",
            "user_id": diagnostic_user["id"],
        },
    )
    blocked_reasons = diagnostic.get("decision", {}).get("blocked_reasons") or []
    _assert(
        diagnostic.get("decision", {}).get("allowed") is False,
        f"Permission diagnostics unexpectedly allowed blocked user: {diagnostic}",
    )
    _assert(
        "缺少菜单权限：task.read" in blocked_reasons,
        f"Permission diagnostics missed menu permission block: {diagnostic}",
    )
    _assert(
        "缺少权限点：task.read" in blocked_reasons,
        f"Permission diagnostics missed permission block: {diagnostic}",
    )
    _assert(
        f"缺少范围：product:{blocked_product['id']}" in blocked_reasons,
        f"Permission diagnostics missed product scope block: {diagnostic}",
    )
    checks = {check.get("code"): check for check in diagnostic.get("checks") or []}
    _assert(
        (checks.get("menu_path") or {}).get("granted_menu_code") == "task.center",
        f"Permission diagnostics missed granted menu evidence: {diagnostic}",
    )
    _assert(
        (checks.get("permission") or {}).get("status") == "blocked",
        f"Permission diagnostics missed blocked permission check: {diagnostic}",
    )
    _assert(
        (checks.get("scope") or {}).get("status") == "blocked",
        f"Permission diagnostics missed blocked scope check: {diagnostic}",
    )
    effective_scopes = diagnostic.get("effective", {}).get("scopes") or []
    _assert(
        any(
            scope.get("scope_id") == scoped_product["id"]
            and scope.get("scope_name") == scoped_product["name"]
            for scope in effective_scopes
        ),
        f"Permission diagnostics missed readable effective scope: {diagnostic}",
    )
    results.append(
        StepResult(
            "permission_visibility_diagnostics",
            f"user={diagnostic_user['id']} / blocked={len(blocked_reasons)}",
        )
    )
    return results
