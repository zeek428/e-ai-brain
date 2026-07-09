from __future__ import annotations

import re
from pathlib import Path

from app.core.authorization import AuthorizationSnapshot, build_menu_tree, has_permission
from app.core.repositories import authorization as authorization_repository
from app.core.repositories.authorization_defaults import (
    COMPATIBILITY_MENU_RESOURCES,
    COMPATIBILITY_ROLE_MENU_GRANTS,
)
from app.core.roles import ROLE_DEFINITIONS

MIGRATION = Path("app/db/migrations/031_rbac_foundation.sql")
LEGACY_ROLE_BACKFILL_MIGRATION = Path("app/db/migrations/033_backfill_legacy_user_roles.sql")
RD_TASK_MENU_MOVE_MIGRATION = Path("app/db/migrations/052_move_rd_tasks_menu.sql")
VIEWER_TASK_BOUNDARY_MIGRATION = Path("app/db/migrations/083_viewer_menu_task_boundary.sql")
VIEWER_ASSISTANT_BOUNDARY_MIGRATION = Path(
    "app/db/migrations/084_viewer_assistant_menu_boundary.sql"
)
VIEWER_PRODUCT_READ_MENU_MIGRATION = Path("app/db/migrations/085_viewer_product_read_menu.sql")
ROLE_BOUNDARY_CLEANUP_MIGRATION = Path("app/db/migrations/090_role_boundary_cleanup.sql")


def _role_permissions(role_code: str) -> set[str]:
    return next(
        set(role["permissions"])
        for role in ROLE_DEFINITIONS
        if role["code"] == role_code
    )


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


def test_rbac_migration_seeds_current_menu_codes():
    sql = MIGRATION.read_text(encoding="utf-8")

    for menu_code in [
        "workspace.dashboard",
        "system.roles",
        "system.users",
        "product.assets",
        "delivery.requirements",
        "delivery.bugs",
        "task.center",
        "knowledge.center",
        "knowledge.search",
        "audit.events",
    ]:
        assert f"'{menu_code}'" in sql

    assert "'group'" in sql
    assert "'page'" in sql
    assert "'hidden_page'" in sql


def test_task_center_menu_resource_is_rd_task_under_delivery():
    resources = {
        resource["code"]: resource
        for resource in authorization_repository.COMPATIBILITY_MENU_RESOURCES
    }

    assert resources["task.center"] == {
        "code": "task.center",
        "name": "研发任务",
        "path": "/delivery/rd-tasks",
        "parent_code": "delivery",
        "menu_type": "page",
        "sort_order": 35,
        "required_permissions": ["task.read"],
        "status": "active",
    }
    assert all(
        resource["code"] != "task.center"
        for resource in resources.values()
        if resource["parent_code"] == "task"
    )


def test_rbac_menu_move_migration_moves_rd_tasks_under_delivery():
    sql = RD_TASK_MENU_MOVE_MIGRATION.read_text(encoding="utf-8")

    assert "UPDATE menu_resources" in sql
    assert "name = '研发任务'" in sql
    assert "path = '/delivery/rd-tasks'" in sql
    assert "parent_code = 'delivery'" in sql
    assert "code = 'task.center'" in sql


def test_rbac_migration_declares_uniqueness_and_timestamps():
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
        create_table = sql.split(f"CREATE TABLE IF NOT EXISTS {table}", maxsplit=1)[1]
        create_table = create_table.split(");", maxsplit=1)[0]
        assert "created_at timestamptz NOT NULL DEFAULT now()" in create_table
        assert "updated_at timestamptz NOT NULL DEFAULT now()" in create_table

    for expected in [
        "code text NOT NULL UNIQUE",
        "code text PRIMARY KEY",
        "UNIQUE (role_id, permission_code)",
        "UNIQUE (role_id, menu_code)",
        "UNIQUE (user_id, role_id, status)",
        "UNIQUE (role_id, scope_type, scope_id, access_level)",
        "UNIQUE (user_id, scope_type, scope_id, access_level, status)",
        "UNIQUE (product_id, user_id, member_role, scope_type, scope_id)",
        "UNIQUE (knowledge_space_id, product_id)",
        "UNIQUE (knowledge_space_id, user_id, space_role)",
    ]:
        assert expected in sql

    assert "idx_user_departments_primary" in sql
    assert "idx_user_roles_active_unique" in sql


def test_rbac_migration_conflict_targets_have_declared_uniqueness():
    sql = MIGRATION.read_text(encoding="utf-8")

    for conflict_target in [
        "(code)",
        "(role_id, permission_code)",
        "(role_id, menu_code)",
        "(role_id, scope_type, scope_id, access_level)",
        "(user_id, role_id, status)",
    ]:
        assert f"ON CONFLICT {conflict_target}" in sql
        assert (
            f"UNIQUE {conflict_target}" in sql
            or "PRIMARY KEY" in sql
            and conflict_target == "(code)"
        )


def test_rbac_migration_backfills_legacy_user_roles():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "INSERT INTO user_roles" in sql
    assert "jsonb_array_elements_text" in sql
    assert "to_jsonb(u.roles)::jsonb" in sql
    assert "JOIN roles r ON r.code = legacy_roles.role_code" in sql
    assert "ON CONFLICT (user_id, role_id, status) DO UPDATE" in sql


def test_rbac_migration_updates_legacy_admin_role_definition_permissions():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "UPDATE role_definitions" in sql
    for permission_code in [
        "system.roles.read",
        "system.roles.manage",
        "system.menus.read",
        "system.menus.manage",
    ]:
        assert permission_code in sql
    assert "WHERE code = 'admin'" in sql


def test_role_definitions_keep_new_roles_within_reviewed_defaults():
    assert {"system.roles.read", "system.roles.manage"} <= _role_permissions("admin")

    expected_permissions = {
        "developer": {
            "task.read",
            "task.create",
            "task.execute",
            "bug.read",
            "knowledge.search",
            "assistant.chat",
            "workspace.read",
        },
        "test_owner": {
            "task.read",
            "task.create",
            "review.decide",
            "bug.read",
            "deployment.read",
            "deployment.create",
            "test.case.manage",
            "test.execution.manage",
            "test.bug.verify",
            "assistant.chat",
            "system.scheduled_jobs.run",
            "workspace.read",
        },
        "tester": {
            "task.read",
            "bug.read",
            "deployment.read",
            "test.read",
            "test.execution.manage",
            "test.bug.verify",
            "assistant.chat",
            "system.scheduled_jobs.run",
            "workspace.read",
        },
        "release_owner": {
            "task.read",
            "bug.read",
            "release.readiness.manage",
            "release.decide",
            "devops.read",
            "deployment.read",
            "deployment.create",
            "deployment.execute",
            "deployment.cancel",
            "assistant.chat",
            "system.scheduled_jobs.run",
            "workspace.read",
        },
    }
    for role_code, permissions in expected_permissions.items():
        assert _role_permissions(role_code) == permissions

    forbidden_permissions = {
        "developer": {"bug.manage", "knowledge.manage", "workspace.write"},
        "test_owner": {"bug.manage", "system.scheduled_jobs.manage", "workspace.write"},
        "tester": {
            "bug.manage",
            "task.create",
            "task.execute",
            "review.decide",
            "release.decide",
        },
        "release_owner": {
            "audit.read",
            "review.decide",
            "system.scheduled_jobs.manage",
            "workspace.write",
        },
    }
    for role_code, permissions in forbidden_permissions.items():
        assert _role_permissions(role_code).isdisjoint(permissions)


def test_default_role_menu_grants_include_required_permissions():
    repository = authorization_repository.CompatibilityAuthorizationRepository()
    resources = {
        resource["code"]: resource
        for resource in COMPATIBILITY_MENU_RESOURCES
    }

    for role_code, menu_codes in COMPATIBILITY_ROLE_MENU_GRANTS.items():
        if role_code == "admin":
            role_permissions = set(
                repository.snapshot_for_user(
                    {"id": "user_admin", "roles": ["admin"]}
                ).permissions
            )
        else:
            role_permissions = _role_permissions(role_code)
        for menu_code in menu_codes:
            required_permissions = set(resources[menu_code].get("required_permissions") or [])
            assert required_permissions <= role_permissions, (
                f"{role_code} menu {menu_code} misses "
                f"{sorted(required_permissions - role_permissions)}"
            )


def test_rbac_migration_does_not_seed_non_admin_product_wildcard_scopes():
    sql = MIGRATION.read_text(encoding="utf-8")
    role_scope_seed = re.search(
        r"WITH role_scope_seed\(.*?\)\s+AS\s+\(\s+VALUES"
        r"(?P<values>.*?)\)\s+INSERT INTO role_scope_grants",
        sql,
        flags=re.S,
    )
    assert role_scope_seed is not None

    seed_values = role_scope_seed.group("values")
    for role_code in [
        "developer",
        "tester",
        "release_owner",
        "product_owner",
        "rd_owner",
        "test_owner",
    ]:
        assert f"('{role_code}', 'product', '*'" not in seed_values

    assert "('admin', 'global', '*', 'admin')" in seed_values
    assert "('reviewer', 'review_assignment', 'self', 'write')" in seed_values
    assert "('test_owner', 'review_assignment', 'self', 'write')" in seed_values


def test_authorization_snapshot_keeps_legacy_roles_and_permission_codes():
    snapshot = AuthorizationSnapshot(
        user_id="user_001",
        roles=["tester"],
        permissions={"bug.read", "test.bug.verify", "workspace.read"},
        scopes=[
            {
                "scope_type": "product",
                "scope_id": "product_001",
                "access_level": "write",
            }
        ],
        menus=[
            {
                "code": "delivery.bugs",
                "name": "Bug 管理",
                "path": "/delivery/bugs",
                "parent_code": "delivery",
            }
        ],
    )

    assert snapshot.roles == ["tester"]
    assert has_permission(snapshot, "test.bug.verify") is True
    assert has_permission(snapshot, "system.roles.manage") is False


def test_admin_role_grants_all_permissions_without_explicit_role_configuration():
    repository = authorization_repository.CompatibilityAuthorizationRepository()
    admin_role = repository.get_role("admin")
    assert admin_role is not None

    repository.set_role_permissions(
        admin_role["id"],
        [],
        actor_id="user_admin",
        trace_id="trace_admin_permissions",
    )
    repository.set_role_menus(
        admin_role["id"],
        [],
        actor_id="user_admin",
        trace_id="trace_admin_menus",
    )

    snapshot = repository.snapshot_for_user({"id": "user_admin", "roles": ["admin"]})

    assert has_permission(snapshot, "system.roles.manage") is True
    assert set(snapshot.permissions) == {
        permission["code"] for permission in repository.list_permissions()
    }
    assert {menu["code"] for menu in snapshot.menus} == {
        menu["code"] for menu in repository.menu_resources()
    }
    assert repository.get_role("admin")["permission_codes"] == sorted(snapshot.permissions)


def test_build_menu_tree_adds_parent_chain_for_authorized_page():
    menu_tree = build_menu_tree(
        granted_codes={"delivery.bugs"},
        resources=[
            {
                "code": "delivery",
                "name": "需求交付",
                "path": "/delivery",
                "parent_code": None,
                "menu_type": "group",
                "sort_order": 20,
                "required_permissions": [],
            },
            {
                "code": "delivery.bugs",
                "name": "Bug 管理",
                "path": "/delivery/bugs",
                "parent_code": "delivery",
                "menu_type": "page",
                "sort_order": 30,
                "required_permissions": ["bug.read"],
            },
        ],
        permissions={"bug.read"},
    )

    assert menu_tree == [
        {
            "code": "delivery",
            "name": "需求交付",
            "path": "/delivery",
            "children": [
                {
                    "code": "delivery.bugs",
                    "name": "Bug 管理",
                    "path": "/delivery/bugs",
                    "children": [],
                }
            ],
        }
    ]


def test_build_menu_tree_drops_empty_authorized_group():
    menu_tree = build_menu_tree(
        granted_codes={"task"},
        resources=[
            {
                "code": "task",
                "name": "任务中心",
                "path": "/tasks",
                "parent_code": None,
                "menu_type": "group",
                "sort_order": 20,
                "required_permissions": [],
            },
            {
                "code": "system.scheduled_jobs",
                "name": "定时作业",
                "path": "/tasks/scheduled-jobs",
                "parent_code": "task",
                "menu_type": "page",
                "sort_order": 21,
                "required_permissions": ["system.scheduled_jobs.manage"],
            },
        ],
        permissions={"workspace.read"},
    )

    assert menu_tree == []


def test_viewer_task_menu_boundary_migration_removes_task_grants():
    sql = VIEWER_TASK_BOUNDARY_MIGRATION.read_text(encoding="utf-8")

    assert "DELETE FROM role_permissions" in sql
    assert "code = 'viewer'" in sql
    assert "permission_code = 'task.read'" in sql
    assert "DELETE FROM role_menu_grants" in sql
    assert "menu_code IN ('task', 'task.center')" in sql


def test_viewer_assistant_menu_boundary_migration_removes_assistant_grants():
    sql = VIEWER_ASSISTANT_BOUNDARY_MIGRATION.read_text(encoding="utf-8")

    assert "DELETE FROM role_permissions" in sql
    assert "code = 'viewer'" in sql
    assert "permission_code = 'assistant.chat'" in sql
    assert "DELETE FROM role_menu_grants" in sql
    assert "menu_code IN ('assistant.chat', 'assistant.drafts')" in sql
    assert "assistant.chat" not in COMPATIBILITY_ROLE_MENU_GRANTS["viewer"]
    assert "assistant.drafts" not in COMPATIBILITY_ROLE_MENU_GRANTS["viewer"]


def test_viewer_product_read_menu_migration_adds_product_management_read_access():
    sql = VIEWER_PRODUCT_READ_MENU_MIGRATION.read_text(encoding="utf-8")

    assert "INSERT INTO role_permissions" in sql
    assert "permissions.code = 'product.read'" in sql
    assert "roles.code = 'viewer'" in sql
    assert "INSERT INTO role_menu_grants" in sql
    assert "menu_resources.code IN ('product.assets', 'product.products')" in sql
    assert "product.read" in _role_permissions("viewer")
    assert "product.manage" not in _role_permissions("viewer")
    assert "product.products" in COMPATIBILITY_ROLE_MENU_GRANTS["viewer"]


def test_viewer_governance_boundary_migration_removes_devops_and_insight_access():
    sql = ROLE_BOUNDARY_CLEANUP_MIGRATION.read_text(encoding="utf-8")

    assert "DELETE FROM role_permissions" in sql
    assert "code = 'viewer'" in sql
    assert "permission_code IN ('devops.read', 'insight.read')" in sql
    assert "menu_code IN ('devops.metrics', 'insight.center')" in sql
    assert "devops.read" not in _role_permissions("viewer")
    assert "insight.read" not in _role_permissions("viewer")
    assert "devops.metrics" not in COMPATIBILITY_ROLE_MENU_GRANTS["viewer"]
    assert "insight.center" not in COMPATIBILITY_ROLE_MENU_GRANTS["viewer"]


def test_reviewer_audit_boundary_migration_removes_global_audit_access():
    sql = ROLE_BOUNDARY_CLEANUP_MIGRATION.read_text(encoding="utf-8")

    assert "code = 'reviewer'" in sql
    assert "permission_code = 'audit.read'" in sql
    assert "menu_code IN ('governance', 'audit.events')" in sql
    assert "audit.read" not in _role_permissions("reviewer")
    assert "audit.events" not in COMPATIBILITY_ROLE_MENU_GRANTS["reviewer"]


def test_postgres_authorization_queries_filter_user_role_effective_window():
    source = Path(authorization_repository.__file__).read_text(encoding="utf-8")

    assert "ur.effective_from <= now()" in source
    assert "ur.expires_at IS NULL OR ur.expires_at > now()" in source
    assert "fallback_roles = user.get(\"roles\") or []" in source
    assert "FROM roles" in source
    assert "WHERE code = ANY(%s)" in source
    assert "AND status = 'active'" in source


def test_legacy_role_backfill_migration_syncs_users_roles_to_user_roles():
    sql = LEGACY_ROLE_BACKFILL_MIGRATION.read_text(encoding="utf-8")

    assert "jsonb_array_elements_text" in sql
    assert "to_jsonb(u.roles)::jsonb" in sql
    assert "INSERT INTO user_roles" in sql
    assert "JOIN roles r ON r.code = legacy_roles.role_code" in sql
    assert "ON CONFLICT (user_id, role_id, status) DO UPDATE" in sql


def test_postgres_authorization_treats_admin_as_all_permissions_and_menus():
    source = Path(authorization_repository.__file__).read_text(encoding="utf-8")

    assert 'if "admin" in roles:' in source
    assert "FROM permissions" in source
    assert "FROM menu_resources" in source
    assert 'role_code == "admin"' in source
    assert "LAST_ADMIN_PERMISSION_PROTECTED" not in source
