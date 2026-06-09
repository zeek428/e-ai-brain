# RBAC Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the reviewed v1.2 RBAC permission system with configurable roles, menu authorization, departments, product members, knowledge spaces, internal-user-bound SSO identities, audit trails, and compatibility for current MVP roles.

**Architecture:** Keep FastAPI as the modular monolith and PostgreSQL as the RBAC source of truth. Introduce the new authorization tables and `AuthorizationService` first, keep `users.roles`, `role_definitions`, and `knowledge_documents.permission_roles` as compatibility projections during migration, then move business endpoints from `require_roles` to permission-and-scope checks by domain.

**Tech Stack:** FastAPI, Python 3.11/3.12, PostgreSQL, psycopg, pytest, ruff, React + TypeScript, Ant Design Pro, Vitest, Playwright/browser smoke through existing scripts.

---

## Source Documents

- Product and technical source of truth: `docs/02-specs/enterprise-ai-brain/spec.md`
- API contract source of truth: `docs/02-specs/enterprise-ai-brain/api.md`
- RBAC design source of truth: `docs/02-specs/enterprise-ai-brain/rbac-redesign.md`
- Changelog: `docs/changelog.md`

## File Structure

- Create `apps/api/app/db/migrations/031_rbac_foundation.sql`: RBAC tables, indexes, seeded permissions, seeded menu resources, compatibility role rows, and backfill from `users.roles`.
- Create `apps/api/app/core/authorization.py`: `AuthorizationSnapshot`, permission matching, scope matching, menu tree building, and compatibility helpers.
- Create `apps/api/app/core/repositories/authorization.py`: PostgreSQL read/write repository for permissions, roles, grants, departments, external identities, product members, and knowledge spaces.
- Modify `apps/api/app/core/roles.py`: keep compatibility role definitions, add developer/test/release templates, and map template permissions/menus to DB seeds.
- Modify `apps/api/app/api/deps.py`: add `require_permissions`, `require_any_permission`, `require_scope`, and keep `require_roles` as a compatibility adapter.
- Modify `apps/api/app/api/routers/auth.py`: enrich `/api/auth/me`, keep `/api/auth/roles` compatibility, and add permission snapshot fields.
- Create `apps/api/app/api/routers/system_rbac.py`: `/api/system/roles`, `/api/system/permissions`, `/api/system/menus`, `/api/system/departments`, `/api/system/external-identities`, and user authorization endpoints.
- Modify `apps/api/app/api/routers/users.py`: move user role writes to `user_roles`, keep `users.roles` projection during compatibility.
- Modify `apps/api/app/api/routers/products.py`: add product member endpoints under `/api/products/{product_id}/members`.
- Modify `apps/api/app/api/routers/knowledge.py`: add knowledge space endpoints and require `knowledge_space_id` on new knowledge documents.
- Modify `apps/api/app/main.py`: include the new RBAC router and repository wiring.
- Modify `apps/api/app/core/persistence_contracts.py` and `apps/api/app/core/persistence_runtime.py`: add authorization repository protocol wiring and expose it from the PostgreSQL runtime container.
- Create `apps/api/tests/test_rbac_foundation.py`: migration seeds, snapshots, menu tree, and compatibility tests.
- Create `apps/api/tests/test_rbac_system_api.py`: role CRUD, menu grants, departments, external identity binding, user role grants, and audit tests.
- Create `apps/api/tests/test_rbac_scope_enforcement.py`: product member scope, knowledge space scope, and business endpoint allow/deny coverage.
- Modify `apps/api/tests/test_foundation.py`, `apps/api/tests/test_knowledge_governance.py`, and affected domain tests as endpoints move to permission checks.
- Modify `apps/web/src/services/aiBrain.ts`: typed RBAC APIs and `/auth/me` menu/snapshot mapping.
- Modify `apps/web/src/app.tsx` or the Ant Design Pro layout entry if dynamic menu injection lives there.
- Modify `apps/web/config/routes.ts`: bind routes to stable menu codes while preserving existing redirects.
- Modify `apps/web/src/pages/Roles/index.tsx`: upgrade from read-only catalog to role governance.
- Create `apps/web/src/pages/Departments/index.tsx`: department tree and member assignment surface.
- Modify `apps/web/src/pages/Users/index.tsx`: role grant source, effective permissions, department membership, and external identity display.
- Modify `apps/web/src/pages/Products/index.tsx`: product member management tab or drawer.
- Modify `apps/web/src/pages/Knowledge/index.tsx`: knowledge space selector and membership management.
- Create or modify `apps/web/tests/RbacSystemPages.test.tsx`, `apps/web/tests/SystemManagementPages.test.tsx`, `apps/web/tests/KnowledgePage.test.tsx`, and route/menu tests.

## Execution Rules

- Implement one task per commit unless a task explicitly says to split it.
- Every backend write slice must write PostgreSQL tables before returning and must not rely on request-end `persist()`.
- Every UI task that changes routes, menus, visible copy, or rendered API fields must finish with real browser validation against the PostgreSQL-backed API runtime.
- Compatibility fields remain until Task 8 is complete: `users.roles`, `/api/auth/roles`, `role_definitions`, and `knowledge_documents.permission_roles`.
- No business endpoint may trust the frontend menu. Backend permission and scope checks are mandatory.

## Task 1: RBAC Schema, Seeds, And Compatibility Backfill

**Files:**
- Create: `apps/api/app/db/migrations/031_rbac_foundation.sql`
- Modify: `apps/api/app/core/roles.py`
- Test: `apps/api/tests/test_rbac_foundation.py`
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md`
- Modify: `docs/changelog.md`

- [x] **Step 1: Write migration-seed tests**

Add tests in `apps/api/tests/test_rbac_foundation.py` that assert the SQL migration declares all reviewed tables and required seed codes. The first implementation can inspect the migration text, matching the existing lightweight migration tests in this repo.

```python
from pathlib import Path


MIGRATION = Path("app/db/migrations/031_rbac_foundation.sql")


def test_rbac_migration_declares_core_tables():
    sql = MIGRATION.read_text(encoding="utf-8")

    for table in [
        "departments",
        "external_identities",
        "user_departments",
        "permissions",
        "menu_resources",
        "roles",
        "role_permissions",
        "role_menu_grants",
        "user_roles",
        "role_scope_grants",
        "user_scope_grants",
        "product_members",
        "knowledge_spaces",
        "knowledge_space_products",
        "knowledge_space_members",
        "role_change_events",
    ]:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql


def test_rbac_migration_seeds_reviewed_role_and_permission_codes():
    sql = MIGRATION.read_text(encoding="utf-8")

    for role_code in [
        "admin",
        "product_owner",
        "rd_owner",
        "reviewer",
        "knowledge_owner",
        "viewer",
        "developer",
        "test_owner",
        "tester",
        "release_owner",
    ]:
        assert f"'{role_code}'" in sql

    for permission_code in [
        "system.roles.manage",
        "system.users.manage",
        "org.department.manage",
        "product.member.manage",
        "knowledge_space.manage",
        "knowledge.search",
        "test.bug.verify",
        "release.decide",
    ]:
        assert f"'{permission_code}'" in sql
```

- [x] **Step 2: Run the failing tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_rbac_foundation.py -q
```

Expected: fail because `031_rbac_foundation.sql` and the seed constants do not exist yet.

- [x] **Step 3: Create the migration**

Create `apps/api/app/db/migrations/031_rbac_foundation.sql` with:

```sql
CREATE TABLE IF NOT EXISTS departments (
  id text PRIMARY KEY,
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  parent_id text REFERENCES departments(id),
  leader_user_id text REFERENCES users(id),
  status text NOT NULL DEFAULT 'active',
  sort_order integer NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS external_identities (
  id text PRIMARY KEY,
  provider text NOT NULL,
  external_subject text NOT NULL,
  external_email text,
  user_id text REFERENCES users(id),
  status text NOT NULL DEFAULT 'active',
  last_login_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (provider, external_subject)
);

CREATE TABLE IF NOT EXISTS user_departments (
  user_id text NOT NULL REFERENCES users(id),
  department_id text NOT NULL REFERENCES departments(id),
  is_primary boolean NOT NULL DEFAULT false,
  position_title text NOT NULL DEFAULT '',
  status text NOT NULL DEFAULT 'active',
  joined_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, department_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_departments_primary
  ON user_departments(user_id)
  WHERE is_primary IS TRUE AND status = 'active';
```

Continue the same file with the remaining tables from `rbac-redesign.md`, explicit unique constraints for role/permission/menu codes, and repeatable `INSERT ... ON CONFLICT DO UPDATE` seeds for permissions, menus, and the ten system role templates. Backfill existing `users.roles` into `user_roles` using `jsonb_array_elements_text(roles)`.

- [x] **Step 4: Extend role templates**

Add `developer`, `test_owner`, `tester`, and `release_owner` to `ROLE_DEFINITIONS` in `apps/api/app/core/roles.py`. Keep their `permissions` and `menu_scope` aligned with `031_rbac_foundation.sql`.

- [x] **Step 5: Run migration foundation tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_rbac_foundation.py tests/test_foundation.py -q
uv run ruff check app tests
```

Expected: pass.

- [x] **Step 6: Commit**

Superseded 2026-06-09 by the consolidated RBAC implementation commit after full backend, frontend, browser, code, and documentation verification.

```bash
git add apps/api/app/db/migrations/031_rbac_foundation.sql apps/api/app/core/roles.py apps/api/tests/test_rbac_foundation.py docs/02-specs/enterprise-ai-brain/spec.md docs/changelog.md
git commit -m "feat: add rbac foundation schema"
```

## Task 2: Authorization Snapshot And Compatibility Adapter

**Files:**
- Create: `apps/api/app/core/authorization.py`
- Create: `apps/api/app/core/repositories/authorization.py`
- Modify: `apps/api/app/api/deps.py`
- Modify: `apps/api/app/api/routers/auth.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_rbac_foundation.py`
- Test: `apps/api/tests/test_api_contract_completion.py`

- [x] **Step 1: Write snapshot tests**

Add tests proving that a user receives permissions, scopes, and menu tree from role grants while legacy `roles` stays available.

```python
from app.core.authorization import AuthorizationSnapshot, build_menu_tree, has_permission


def test_authorization_snapshot_keeps_legacy_roles_and_permission_codes():
    snapshot = AuthorizationSnapshot(
        user_id="user_001",
        roles=["tester"],
        permissions={"bug.read", "test.bug.verify", "workspace.read"},
        scopes=[{"scope_type": "product", "scope_id": "product_001", "access_level": "write"}],
        menus=[{"code": "delivery.bugs", "name": "Bug 管理", "path": "/delivery/bugs", "parent_code": "delivery"}],
    )

    assert snapshot.roles == ["tester"]
    assert has_permission(snapshot, "test.bug.verify") is True
    assert has_permission(snapshot, "system.roles.manage") is False


def test_build_menu_tree_adds_parent_chain_for_authorized_page():
    menu_tree = build_menu_tree(
        granted_codes={"delivery.bugs"},
        resources=[
            {"code": "delivery", "name": "需求交付", "path": "/delivery", "parent_code": None, "menu_type": "group", "sort_order": 20, "required_permissions": []},
            {"code": "delivery.bugs", "name": "Bug 管理", "path": "/delivery/bugs", "parent_code": "delivery", "menu_type": "page", "sort_order": 30, "required_permissions": ["bug.read"]},
        ],
        permissions={"bug.read"},
    )

    assert menu_tree == [
        {
            "code": "delivery",
            "name": "需求交付",
            "path": "/delivery",
            "children": [
                {"code": "delivery.bugs", "name": "Bug 管理", "path": "/delivery/bugs", "children": []}
            ],
        }
    ]
```

- [x] **Step 2: Run the failing tests**

```bash
cd apps/api
uv run pytest tests/test_rbac_foundation.py::test_authorization_snapshot_keeps_legacy_roles_and_permission_codes tests/test_rbac_foundation.py::test_build_menu_tree_adds_parent_chain_for_authorized_page -q
```

Expected: fail because `app.core.authorization` does not exist.

- [x] **Step 3: Implement `AuthorizationSnapshot` helpers**

Create `apps/api/app/core/authorization.py` with a frozen dataclass and pure functions:

```python
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
    return permission_code in snapshot.permissions or "system.admin" in snapshot.permissions


def build_menu_tree(*, granted_codes: set[str], resources: list[dict[str, Any]], permissions: set[str]) -> list[dict[str, Any]]:
    by_code = {item["code"]: item for item in resources if item.get("status", "active") == "active"}
    visible_codes = set()
    for code in granted_codes:
        item = by_code.get(code)
        if item is None:
            continue
        required_permissions = set(item.get("required_permissions") or [])
        if required_permissions and not required_permissions.issubset(permissions):
            continue
        current_code = code
        while current_code:
            current = by_code.get(current_code)
            if current is None:
                break
            visible_codes.add(current_code)
            current_code = current.get("parent_code")

    def build_node(item: dict[str, Any]) -> dict[str, Any]:
        children = [
            build_node(child)
            for child in sorted(by_code.values(), key=lambda row: (row.get("sort_order", 0), row["code"]))
            if child.get("parent_code") == item["code"] and child["code"] in visible_codes and child.get("menu_type") != "hidden_page"
        ]
        return {"code": item["code"], "name": item["name"], "path": item.get("path"), "children": children}

    roots = [
        item
        for item in sorted(by_code.values(), key=lambda row: (row.get("sort_order", 0), row["code"]))
        if item["code"] in visible_codes and not item.get("parent_code") and item.get("menu_type") != "hidden_page"
    ]
    return [build_node(item) for item in roots]
```

- [x] **Step 4: Add dependencies**

In `apps/api/app/api/deps.py`, add permission dependencies while keeping `require_roles` working:

```python
def require_permissions(user: dict[str, Any], required_permissions: set[str]) -> None:
    user_permissions = set(user.get("permissions") or [])
    legacy_roles = set(user.get("roles") or [])
    if "admin" in legacy_roles or required_permissions.issubset(user_permissions):
        return
    raise api_error(403, "FORBIDDEN", "Permission denied")
```

Use this helper in new RBAC endpoints first. Do not migrate existing business endpoints in this task.

- [x] **Step 5: Enrich `/api/auth/me`**

Modify `apps/api/app/api/routers/auth.py` so `/api/auth/me` returns:

```json
{
  "id": "admin",
  "username": "admin@example.com",
  "display_name": "系统管理员",
  "roles": ["admin"],
  "permissions": ["system.users.manage"],
  "scope_summary": [{"scope_type": "global", "scope_id": "*", "access_level": "admin"}],
  "menu_tree": [],
  "route_permissions": {}
}
```

In this task it is acceptable for local memory tests to derive permissions from `ROLE_DEFINITIONS`; PostgreSQL runtime must prefer the new authorization repository when present.

- [x] **Step 6: Run tests**

```bash
cd apps/api
uv run pytest tests/test_rbac_foundation.py tests/test_api_contract_completion.py -q
uv run ruff check app tests
```

Expected: pass.

- [x] **Step 7: Commit**

Superseded 2026-06-09 by the consolidated RBAC implementation commit after full backend, frontend, browser, code, and documentation verification.

```bash
git add apps/api/app/core/authorization.py apps/api/app/core/repositories/authorization.py apps/api/app/api/deps.py apps/api/app/api/routers/auth.py apps/api/app/main.py apps/api/tests/test_rbac_foundation.py apps/api/tests/test_api_contract_completion.py
git commit -m "feat: add authorization snapshot"
```

## Task 3: System RBAC APIs And Audit

**Files:**
- Create: `apps/api/app/api/routers/system_rbac.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/core/repositories/authorization.py`
- Test: `apps/api/tests/test_rbac_system_api.py`
- Modify: `docs/02-specs/enterprise-ai-brain/api.md`
- Modify: `docs/changelog.md`

- [x] **Step 1: Write API tests**

Add tests for the minimum role governance loop:

```python
def test_admin_can_create_copy_update_disable_and_enable_role(client, admin_headers):
    create_response = client.post(
        "/api/system/roles",
        headers=admin_headers,
        json={"code": "frontend_reviewer", "name": "前端评审", "description": "评审前端交付物", "category": "review"},
    )
    assert create_response.status_code == 200

    role_id = create_response.json()["data"]["id"]
    update_response = client.put(
        f"/api/system/roles/{role_id}/permissions",
        headers=admin_headers,
        json={"permission_codes": ["review.read", "review.decide", "task.read"]},
    )
    assert update_response.status_code == 200
    assert "review.decide" in update_response.json()["data"]["permissions"]

    disable_response = client.post(f"/api/system/roles/{role_id}/disable", headers=admin_headers)
    assert disable_response.status_code == 200
    assert disable_response.json()["data"]["status"] == "inactive"

    enable_response = client.post(f"/api/system/roles/{role_id}/enable", headers=admin_headers)
    assert enable_response.status_code == 200
    assert enable_response.json()["data"]["status"] == "active"
```

Also cover:

- non-admin returns `403 FORBIDDEN`;
- system role delete/disable guard for the last system admin capability;
- role menu grants return updated `menu_codes`;
- every mutating call writes `role_change_events` and `audit_events`.

- [x] **Step 2: Run the failing tests**

```bash
cd apps/api
uv run pytest tests/test_rbac_system_api.py -q
```

Expected: fail because `/api/system/roles` does not exist.

- [x] **Step 3: Implement `system_rbac` router**

Implement these endpoints with `require_permissions(user, {"system.roles.manage"})` or `{"system.users.manage"}`:

- `GET /api/system/permissions`
- `GET /api/system/menus`
- `GET /api/system/roles`
- `POST /api/system/roles`
- `POST /api/system/roles/{role_id}/copy`
- `GET /api/system/roles/{role_id}`
- `PATCH /api/system/roles/{role_id}`
- `POST /api/system/roles/{role_id}/disable`
- `POST /api/system/roles/{role_id}/enable`
- `PUT /api/system/roles/{role_id}/permissions`
- `PUT /api/system/roles/{role_id}/menus`
- `PUT /api/system/roles/{role_id}/scopes`
- `GET /api/users/{user_id}/permissions`
- `PUT /api/users/{user_id}/roles`
- `PUT /api/users/{user_id}/scopes`

Keep response envelopes consistent with existing routers and include `trace_id`.

- [x] **Step 4: Register the router**

In `apps/api/app/main.py`, include the new router next to other API routers:

```python
from app.api.routers import system_rbac

app.include_router(system_rbac.router)
```

- [x] **Step 5: Document API contracts**

Update `docs/02-specs/enterprise-ai-brain/api.md` with request and response examples for role CRUD, permission list, menu list, and user grants. Add exact error codes:

- `ROLE_CODE_EXISTS`
- `SYSTEM_ROLE_PROTECTED`
- `UNSUPPORTED_PERMISSION`
- `UNSUPPORTED_MENU`
- `INVALID_SCOPE`

- [x] **Step 6: Run backend API tests**

```bash
cd apps/api
uv run pytest tests/test_rbac_system_api.py tests/test_foundation.py -q
uv run ruff check app tests
```

Expected: pass.

- [x] **Step 7: Commit**

Superseded 2026-06-09 by the consolidated RBAC implementation commit after full backend, frontend, browser, code, and documentation verification.

```bash
git add apps/api/app/api/routers/system_rbac.py apps/api/app/main.py apps/api/app/core/repositories/authorization.py apps/api/tests/test_rbac_system_api.py docs/02-specs/enterprise-ai-brain/api.md docs/changelog.md
git commit -m "feat: add rbac system APIs"
```

## Task 4: Frontend Role Governance And Dynamic Menu

**Files:**
- Modify: `apps/web/src/services/aiBrain.ts`
- Modify: `apps/web/src/pages/Roles/index.tsx`
- Modify: `apps/web/config/routes.ts`
- Modify: `apps/web/src/app.tsx`
- Test: `apps/web/tests/SystemManagementPages.test.tsx`
- Test: `apps/web/tests/RbacSystemPages.test.tsx`

- [x] **Step 1: Write frontend tests**

Add tests proving role management is no longer read-only and menu data from `/api/auth/me` drives the left navigation:

```tsx
it('renders role create and menu grant controls from RBAC APIs', async () => {
  render(<RolesPage />);

  expect(await screen.findByRole('button', { name: /新建角色/ })).toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: /新建角色/ }));

  expect(await screen.findByLabelText('角色编码')).toBeInTheDocument();
  expect(screen.getByText('功能菜单')).toBeInTheDocument();
  expect(screen.getByText('权限点')).toBeInTheDocument();
});
```

Add a route/menu test that mocks `/api/auth/me` with no `system.roles` menu and asserts the left menu does not show `角色管理`.

- [x] **Step 2: Run failing tests**

```bash
cd apps/web
npm test -- SystemManagementPages.test.tsx RbacSystemPages.test.tsx
```

Expected: fail because the role page only has detail viewing and route menu is static.

- [x] **Step 3: Add RBAC service functions**

In `apps/web/src/services/aiBrain.ts`, add typed service methods:

- `fetchPermissions()`
- `fetchMenuResources()`
- `fetchSystemRoles(query)`
- `createSystemRole(payload)`
- `copySystemRole(roleId, payload)`
- `updateSystemRole(roleId, payload)`
- `updateRolePermissions(roleId, permissionCodes)`
- `updateRoleMenus(roleId, menuCodes)`
- `updateRoleScopes(roleId, scopes)`
- `updateUserRoles(userId, grants)`
- `updateUserScopes(userId, scopes)`

Use the existing `request` helper and response normalization style already used by `fetchRoleDefinitionList`.

- [x] **Step 4: Upgrade role page**

Modify `apps/web/src/pages/Roles/index.tsx` to include:

- primary `新建角色` button;
- `复制` action for each role;
- create/edit modal with role code, name, category, description, assignable status, permissions tree/check list, menu tree, and data scopes;
- disable/enable action with confirmation;
- detail drawer explaining effective permissions and menus.

- [x] **Step 5: Use `menu_tree` for navigation**

Add route `menuCode` metadata in `apps/web/config/routes.ts` and transform `/api/auth/me.menu_tree` into Ant Design Pro menu entries in `apps/web/src/app.tsx`. Preserve the existing route paths and hidden redirects.

- [x] **Step 6: Run frontend verification**

```bash
cd apps/web
npm test -- SystemManagementPages.test.tsx RbacSystemPages.test.tsx
npm test
npm run build
```

Expected: pass.

- [x] **Step 7: Browser smoke**

Verified 2026-06-09 with the PostgreSQL-backed API runtime and real web app at `http://localhost:8000` and `http://localhost:5173`. Logged in as `admin@example.com`, opened `/system/roles`, opened the `product_owner` role configuration modal, and confirmed menu-first checkbox configuration with menu-specific permissions. Logged in as `qa_product_owner@example.com`, confirmed the left menu hides system management, user management, role management, model gateway, log monitoring, and audit entries while keeping authorized product owner entries visible. A direct visit to `/system/roles` as product owner returned `FORBIDDEN` with an empty data table and no console/runtime errors.

Start the real services with PostgreSQL runtime, log in as `admin@example.com`, and validate:

- `http://127.0.0.1:5173/system/roles` renders non-blank;
- `新建角色` opens a modal with permissions and menu configuration;
- creating or copying a role refreshes the table;
- disabling a custom role removes it from assignable options;
- no relevant console/runtime errors appear.

- [x] **Step 8: Commit**

Completed 2026-06-09 as part of the consolidated RBAC implementation after automated verification, browser validation, and code/document review.

```bash
git add apps/web/src/services/aiBrain.ts apps/web/src/pages/Roles/index.tsx apps/web/config/routes.ts apps/web/src/app.tsx apps/web/tests/SystemManagementPages.test.tsx apps/web/tests/RbacSystemPages.test.tsx
git commit -m "feat: add rbac role management UI"
```

## Task 5: Departments, External Identities, Users, And Product Members

**Files:**
- Modify: `apps/api/app/api/routers/system_rbac.py`
- Modify: `apps/api/app/api/routers/users.py`
- Modify: `apps/api/app/api/routers/products.py`
- Modify: `apps/api/app/core/repositories/authorization.py`
- Create: `apps/web/src/pages/Departments/index.tsx`
- Modify: `apps/web/src/pages/Users/index.tsx`
- Modify: `apps/web/src/pages/Products/index.tsx`
- Modify: `apps/web/config/routes.ts`
- Test: `apps/api/tests/test_rbac_system_api.py`
- Test: `apps/api/tests/test_rbac_scope_enforcement.py`
- Test: `apps/web/tests/RbacSystemPages.test.tsx`

- [ ] **Step 1: Write backend scope tests**

Add tests proving product members create effective product/module/version scope, and SSO identities do nothing unless bound to an active internal user.

```python
def test_product_member_grant_adds_product_scope_to_snapshot(client, admin_headers):
    response = client.post(
        "/api/products/product_001/members",
        headers=admin_headers,
        json={"user_id": "user_tester", "member_role": "tester", "scope_type": "product", "scope_id": "product_001"},
    )
    assert response.status_code == 200

    permissions = client.get("/api/users/user_tester/permissions", headers=admin_headers).json()["data"]
    assert {"scope_type": "product", "scope_id": "product_001", "access_level": "write"} in permissions["scopes"]


def test_unbound_external_identity_has_no_default_authorization(client, admin_headers):
    response = client.post(
        "/api/system/external-identities",
        headers=admin_headers,
        json={"provider": "oidc", "external_subject": "subject-001", "external_email": "new.user@example.com"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["user_id"] is None
```

- [ ] **Step 2: Run failing backend tests**

```bash
cd apps/api
uv run pytest tests/test_rbac_system_api.py tests/test_rbac_scope_enforcement.py -q
```

Expected: fail because department, external identity, and product member endpoints are incomplete.

- [ ] **Step 3: Implement APIs**

Add endpoints:

- `GET/POST/PATCH /api/system/departments`
- `PUT /api/system/departments/{department_id}/members`
- `GET/POST/PATCH /api/system/external-identities`
- `POST /api/system/external-identities/{identity_id}/bind`
- `POST /api/system/external-identities/{identity_id}/unbind`
- `GET/POST /api/products/{product_id}/members`
- `PATCH/DELETE /api/products/{product_id}/members/{member_id}`

Rules:

- one active primary department per user;
- unbound external identity has `user_id=null` and no authorization;
- product member roles derive product scopes but do not grant global system permissions;
- all changes write audit events.

- [ ] **Step 4: Add frontend pages**

Add a `部门管理` menu under `系统管理`, update user management to show department membership and external identities, and add product member management in product detail or a product members drawer.

- [ ] **Step 5: Run tests and browser validation**

```bash
cd apps/api
uv run pytest tests/test_rbac_system_api.py tests/test_rbac_scope_enforcement.py -q
uv run ruff check app tests
cd ../web
npm test -- RbacSystemPages.test.tsx
npm run build
```

Browser smoke:

- `/system/departments`: create child department and assign a user as primary member;
- `/system/users`: verify the user shows department and role grant source;
- `/assets/products`: add tester/developer/product owner members and verify product member list persists after refresh.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/api/routers/system_rbac.py apps/api/app/api/routers/users.py apps/api/app/api/routers/products.py apps/api/app/core/repositories/authorization.py apps/api/tests/test_rbac_system_api.py apps/api/tests/test_rbac_scope_enforcement.py apps/web/src/pages/Departments/index.tsx apps/web/src/pages/Users/index.tsx apps/web/src/pages/Products/index.tsx apps/web/config/routes.ts apps/web/tests/RbacSystemPages.test.tsx
git commit -m "feat: add departments and product members"
```

## Task 6: Knowledge Spaces And Knowledge Permission Enforcement

**Files:**
- Modify: `apps/api/app/api/routers/knowledge.py`
- Modify: `apps/api/app/services/knowledge_documents.py`
- Modify: `apps/api/app/services/knowledge_search.py`
- Modify: `apps/api/app/core/repositories/knowledge.py`
- Modify: `apps/api/app/core/repositories/knowledge_writes.py`
- Modify: `apps/api/app/core/repositories/authorization.py`
- Modify: `apps/web/src/pages/Knowledge/index.tsx`
- Test: `apps/api/tests/test_knowledge_governance.py`
- Test: `apps/api/tests/test_rbac_scope_enforcement.py`
- Test: `apps/web/tests/KnowledgePage.test.tsx`

- [ ] **Step 1: Write knowledge-space tests**

Add tests covering the new permission boundary:

```python
def test_knowledge_search_filters_by_authorized_space_before_keyword_match(client, admin_headers, viewer_headers):
    create_space = client.post(
        "/api/knowledge/spaces",
        headers=admin_headers,
        json={"code": "payments", "name": "支付知识空间", "description": "支付产品研发资料"},
    )
    assert create_space.status_code == 200
    space_id = create_space.json()["data"]["id"]

    create_doc = client.post(
        "/api/knowledge/documents",
        headers=admin_headers,
        json={"title": "支付异常处理", "content": "支付失败排查步骤", "doc_type": "runbook", "knowledge_space_id": space_id},
    )
    assert create_doc.status_code == 200

    denied = client.post("/api/knowledge/search", headers=viewer_headers, json={"query": "支付失败"})
    assert denied.status_code == 200
    assert denied.json()["data"]["results"] == []
```

- [ ] **Step 2: Run failing tests**

```bash
cd apps/api
uv run pytest tests/test_knowledge_governance.py tests/test_rbac_scope_enforcement.py -q
```

Expected: fail because knowledge documents still use role arrays as the primary boundary.

- [ ] **Step 3: Implement knowledge space APIs**

Add endpoints:

- `GET/POST /api/knowledge/spaces`
- `GET/PATCH /api/knowledge/spaces/{space_id}`
- `PUT /api/knowledge/spaces/{space_id}/products`
- `PUT /api/knowledge/spaces/{space_id}/members`

Require `knowledge_space.manage` for space management and `knowledge.manage` for document write operations.

- [ ] **Step 4: Enforce space filtering**

Update document creation so new documents require `knowledge_space_id`. Update repository search so SQL filters by authorized `knowledge_space_id` before keyword or vector scoring. Keep `permission_roles` as a compatibility fallback only for migrated legacy documents that have no `knowledge_space_id`.

- [ ] **Step 5: Update Knowledge UI**

Add a knowledge space selector and a space management drawer. The document form must require knowledge space selection for new documents, while legacy documents without a space show a migration warning text in the detail view.

- [ ] **Step 6: Run tests and browser validation**

```bash
cd apps/api
uv run pytest tests/test_knowledge_governance.py tests/test_rbac_scope_enforcement.py -q
uv run ruff check app tests
cd ../web
npm test -- KnowledgePage.test.tsx
npm run build
```

Browser smoke:

- `/assets/knowledge`: create a knowledge space;
- create a document inside that space;
- remove the current user's space membership in admin view;
- search for the document title and verify it no longer appears for that user.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/api/routers/knowledge.py apps/api/app/services/knowledge_documents.py apps/api/app/services/knowledge_search.py apps/api/app/core/repositories/knowledge.py apps/api/app/core/repositories/knowledge_writes.py apps/api/app/core/repositories/authorization.py apps/api/tests/test_knowledge_governance.py apps/api/tests/test_rbac_scope_enforcement.py apps/web/src/pages/Knowledge/index.tsx apps/web/tests/KnowledgePage.test.tsx
git commit -m "feat: enforce knowledge space permissions"
```

## Task 7: Business Endpoint Permission Migration

**Files:**
- Modify: `apps/api/app/api/routers/model_gateway.py`
- Modify: `apps/api/app/api/routers/audit.py`
- Modify: `apps/api/app/api/routers/products.py`
- Modify: `apps/api/app/api/routers/product_versions.py`
- Modify: `apps/api/app/api/routers/product_modules.py`
- Modify: `apps/api/app/api/routers/product_git_repositories.py`
- Modify: `apps/api/app/api/routers/requirements.py`
- Modify: `apps/api/app/api/routers/tasks.py`
- Modify: `apps/api/app/api/routers/knowledge.py`
- Modify: `apps/api/app/api/routers/bugs.py`
- Modify: `apps/api/app/api/routers/devops_metrics.py`
- Modify: `apps/api/app/api/routers/user_insights.py`
- Modify: affected services under `apps/api/app/services/`
- Test: affected backend domain tests plus `apps/api/tests/test_rbac_scope_enforcement.py`

- [ ] **Step 1: Create a migration checklist test**

Add a test that scans production code and fails if new business endpoints add fresh `require_roles` calls outside the compatibility adapter.

```python
from pathlib import Path


def test_no_new_business_require_roles_calls_after_rbac_migration():
    allowed_files = {
        Path("app/api/deps.py"),
        Path("app/api/routers/auth.py"),
    }
    offenders = []
    for path in Path("app").rglob("*.py"):
        if path in allowed_files:
            continue
        text = path.read_text(encoding="utf-8")
        if "require_roles(" in text:
            offenders.append(str(path))

    assert offenders == []
```

Keep this test marked or introduced only after the domain list below has been migrated, so it functions as a final guardrail for the task.

- [ ] **Step 2: Migrate system and platform endpoints**

Replace role checks with permission checks:

- model gateway write: `system.model_gateway.manage`;
- audit read: `audit.read`;
- user and role governance: `system.users.manage`, `system.roles.manage`;
- assistant chat: `assistant.chat`.

Run:

```bash
cd apps/api
uv run pytest tests/test_model_gateway.py tests/test_audit.py tests/test_rbac_system_api.py -q
```

- [ ] **Step 3: Migrate product and delivery endpoints**

Replace product, version, module, Git resource, requirement, task, review, and writeback role checks with permission checks plus product/version/module scope checks:

- product config: `product.manage`, `product.member.manage`;
- requirement create/read/approve/task generation: `requirement.create`, `requirement.read`, `requirement.approve`, `requirement.task_generate`;
- task lifecycle: `task.read`, `task.create`, `task.execute`, `task.cancel`, `task.retry`;
- review decision: `review.decide`;
- Git review read: `devops.read` or the reviewed Git permission code retained in seeds.

Run:

```bash
cd apps/api
uv run pytest tests/test_product_config_persistence.py tests/test_requirement_task_persistence.py tests/test_workflow_runtime_persistence.py tests/test_rbac_scope_enforcement.py -q
```

- [ ] **Step 4: Migrate Bug, testing, release, DevOps, insights, and dashboard**

Replace role checks:

- Bug read/manage: `bug.read`, `bug.manage`;
- tester verification: `test.bug.verify`;
- testing execution: `test.execution.manage`;
- release readiness and decision: `release.readiness.manage`, `release.decide`;
- DevOps metrics: `devops.read`, `devops.metrics.manage`;
- feedback and planning: `insight.read`, `insight.feedback.manage`, `planning.decide`;
- dashboard read: `workspace.read` plus product scope.

Run:

```bash
cd apps/api
uv run pytest tests/test_bug_persistence.py tests/test_operational_collection_persistence.py tests/test_insight_planning_api_persistence.py tests/test_lifecycle_dashboard_persistence.py tests/test_rbac_scope_enforcement.py -q
```

- [ ] **Step 5: Run full backend gate**

```bash
cd apps/api
uv run pytest
uv run ruff check app tests
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app apps/api/tests
git commit -m "feat: migrate business APIs to rbac permissions"
```

## Task 8: Compatibility Cleanup, Full Verification, And Release Evidence

**Files:**
- Modify: `docs/02-specs/enterprise-ai-brain/rbac-redesign.md`
- Modify: `docs/02-specs/enterprise-ai-brain/api.md`
- Modify: `docs/02-specs/enterprise-ai-brain/test-case.md`
- Modify: `docs/02-specs/enterprise-ai-brain/spec.md`
- Modify: `docs/changelog.md`
- Modify: compatibility code and tests identified by Task 7

- [ ] **Step 1: Decide compatibility end state for v1.2**

Keep these as read-only projections in v1.2 unless a separate removal plan is approved:

- `/api/auth/roles`;
- `role_definitions`;
- `users.roles`;
- `knowledge_documents.permission_roles`.

Document that writes go through RBAC tables and projections are compatibility-only.

- [ ] **Step 2: Update acceptance tests**

Update `docs/02-specs/enterprise-ai-brain/test-case.md` with P0 cases:

- admin creates custom role and assigns permissions;
- role menu grant changes `/api/auth/me.menu_tree`;
- department primary membership is unique;
- external identity without `users.id` binding has no role or scope;
- product member grants product scope;
- knowledge search does not return unauthorized knowledge spaces;
- tester can verify Bug in authorized product but cannot approve requirements;
- disabled role immediately removes permissions.

- [ ] **Step 3: Run full automated gate**

```bash
cd apps/api
uv run pytest
uv run ruff check app tests
cd ../web
npm test
npm run build
```

Expected: all pass.

- [ ] **Step 4: Run real browser validation**

Use PostgreSQL-backed API runtime and the real web service. Validate these pages and flows with `admin@example.com`:

- `/system/roles`: create/copy/edit/disable role; configure menu and permissions;
- `/system/users`: assign a custom role and view effective permissions;
- `/system/departments`: assign a primary department;
- `/assets/products`: configure product members;
- `/assets/knowledge`: configure knowledge space, create document, search with allowed and denied users;
- `/delivery/bugs`: verify tester access within product scope;
- direct URL access to an unauthorized menu route returns a guarded page or API `403`.

Record URL, role, command, and result in the final implementation summary before committing.

- [ ] **Step 5: Update docs and changelog**

Set RBAC implementation status in `rbac-redesign.md`, API contracts, technical spec, test cases, and `docs/changelog.md`. The docs must state which compatibility projections remain and which source tables are authoritative.

- [ ] **Step 6: Commit**

```bash
git add docs/02-specs/enterprise-ai-brain/rbac-redesign.md docs/02-specs/enterprise-ai-brain/api.md docs/02-specs/enterprise-ai-brain/test-case.md docs/02-specs/enterprise-ai-brain/spec.md docs/changelog.md apps/api apps/web
git commit -m "docs: record rbac implementation evidence"
```

## Acceptance Checklist

- [ ] System admin can create, copy, edit, disable, and enable custom roles.
- [ ] Roles can be configured with permissions, menu resources, and data scopes.
- [ ] `/api/auth/me` returns legacy `roles`, effective `permissions`, `scope_summary`, `menu_tree`, and `route_permissions`.
- [ ] Left navigation renders from `menu_tree`.
- [ ] Backend still rejects direct API calls without required permission and data scope.
- [ ] Users belong to departments, with one active primary department.
- [ ] Product members configured in product management derive product/version/module scope.
- [ ] Knowledge documents belong to knowledge spaces, and search filters by authorized spaces before ranking.
- [ ] External SSO identities only participate in authorization when bound to an active internal `users.id`.
- [ ] Role/user/scope/menu/department/product-member/knowledge-space changes are audited.
- [ ] Existing MVP six-role behavior remains compatible during v1.2 rollout.
- [ ] Full backend tests, frontend tests, production build, and real browser smoke pass.
