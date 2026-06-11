from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from time import sleep
from typing import Any
from uuid import uuid4

from app.core.authorization import AuthorizationSnapshot
from app.core.db import DatabaseConnectionPool
from app.core.roles import ROLE_DEFINITIONS

SYSTEM_ROLE_CODES = {role["code"] for role in ROLE_DEFINITIONS}
VALID_SCOPE_TYPES = {
    "department",
    "global",
    "knowledge_space",
    "product",
    "product_module",
    "product_version",
    "review_assignment",
    "self",
}
VALID_SCOPE_ACCESS_LEVELS = {"admin", "read", "write"}

COMPATIBILITY_MENU_RESOURCES: list[dict[str, Any]] = [
    {
        "code": "workspace.dashboard",
        "name": "团队看板",
        "path": "/welcome",
        "parent_code": None,
        "menu_type": "page",
        "sort_order": 10,
        "required_permissions": ["workspace.read"],
        "status": "active",
    },
    {
        "code": "assistant.chat",
        "name": "AI 助手",
        "path": "/assistant",
        "parent_code": None,
        "menu_type": "page",
        "sort_order": 15,
        "required_permissions": ["assistant.chat"],
        "status": "active",
    },
    {
        "code": "task",
        "name": "任务中心",
        "path": "/tasks",
        "parent_code": None,
        "menu_type": "group",
        "sort_order": 20,
        "required_permissions": [],
        "status": "active",
    },
    {
        "code": "task.center",
        "name": "任务管理",
        "path": "/tasks/management",
        "parent_code": "task",
        "menu_type": "page",
        "sort_order": 21,
        "required_permissions": ["task.read"],
        "status": "active",
    },
    {
        "code": "delivery",
        "name": "需求交付",
        "path": "/delivery",
        "parent_code": None,
        "menu_type": "group",
        "sort_order": 30,
        "required_permissions": [],
        "status": "active",
    },
    {
        "code": "delivery.requirements",
        "name": "需求管理",
        "path": "/delivery/requirements",
        "parent_code": "delivery",
        "menu_type": "page",
        "sort_order": 31,
        "required_permissions": ["requirement.read"],
        "status": "active",
    },
    {
        "code": "delivery.requirement_full_chain",
        "name": "需求全链路详情",
        "path": "/delivery/requirements/:requirementId/full-chain",
        "parent_code": "delivery",
        "menu_type": "hidden_page",
        "sort_order": 32,
        "required_permissions": ["requirement.read"],
        "status": "active",
    },
    {
        "code": "delivery.versions",
        "name": "迭代版本",
        "path": "/delivery/versions",
        "parent_code": "delivery",
        "menu_type": "page",
        "sort_order": 33,
        "required_permissions": ["product.read"],
        "status": "active",
    },
    {
        "code": "delivery.bugs",
        "name": "Bug 管理",
        "path": "/delivery/bugs",
        "parent_code": "delivery",
        "menu_type": "page",
        "sort_order": 34,
        "required_permissions": ["bug.read"],
        "status": "active",
    },
    {
        "code": "product.assets",
        "name": "产品资产",
        "path": "/assets",
        "parent_code": None,
        "menu_type": "group",
        "sort_order": 40,
        "required_permissions": [],
        "status": "active",
    },
    {
        "code": "product.products",
        "name": "产品管理",
        "path": "/assets/products",
        "parent_code": "product.assets",
        "menu_type": "page",
        "sort_order": 41,
        "required_permissions": ["product.read"],
        "status": "active",
    },
    {
        "code": "knowledge.center",
        "name": "知识中心",
        "path": "/assets/knowledge",
        "parent_code": "product.assets",
        "menu_type": "page",
        "sort_order": 42,
        "required_permissions": ["knowledge.read"],
        "status": "active",
    },
    {
        "code": "knowledge.search",
        "name": "知识检索",
        "path": "/assets/knowledge",
        "parent_code": "product.assets",
        "menu_type": "hidden_page",
        "sort_order": 43,
        "required_permissions": ["knowledge.search"],
        "status": "active",
    },
    {
        "code": "governance",
        "name": "运营治理",
        "path": "/governance",
        "parent_code": None,
        "menu_type": "group",
        "sort_order": 50,
        "required_permissions": [],
        "status": "active",
    },
    {
        "code": "devops.metrics",
        "name": "日志监控",
        "path": "/governance/devops",
        "parent_code": "governance",
        "menu_type": "page",
        "sort_order": 51,
        "required_permissions": ["devops.read"],
        "status": "active",
    },
    {
        "code": "insight.center",
        "name": "用户洞察",
        "path": "/governance/insights",
        "parent_code": "governance",
        "menu_type": "page",
        "sort_order": 52,
        "required_permissions": ["insight.read"],
        "status": "active",
    },
    {
        "code": "audit.events",
        "name": "审计与运行",
        "path": "/governance/audit",
        "parent_code": "governance",
        "menu_type": "page",
        "sort_order": 53,
        "required_permissions": ["audit.read"],
        "status": "active",
    },
    {
        "code": "code_inspection.reports",
        "name": "代码审查",
        "path": "/governance/code-inspections",
        "parent_code": "governance",
        "menu_type": "page",
        "sort_order": 54,
        "required_permissions": ["code_inspection.read"],
        "status": "active",
    },
    {
        "code": "system",
        "name": "系统管理",
        "path": "/system",
        "parent_code": None,
        "menu_type": "group",
        "sort_order": 60,
        "required_permissions": [],
        "status": "active",
    },
    {
        "code": "system.users",
        "name": "用户管理",
        "path": "/system/users",
        "parent_code": "system",
        "menu_type": "page",
        "sort_order": 61,
        "required_permissions": ["system.users.manage"],
        "status": "active",
    },
    {
        "code": "system.roles",
        "name": "角色管理",
        "path": "/system/roles",
        "parent_code": "system",
        "menu_type": "page",
        "sort_order": 62,
        "required_permissions": ["system.roles.manage"],
        "status": "active",
    },
    {
        "code": "system.model_gateway",
        "name": "模型网关",
        "path": "/system/model-gateway",
        "parent_code": "system",
        "menu_type": "page",
        "sort_order": 63,
        "required_permissions": ["system.model_gateway.manage"],
        "status": "active",
    },
    {
        "code": "system.ai_capabilities",
        "name": "AI 能力配置",
        "path": "/tasks/ai-capabilities",
        "parent_code": "task",
        "menu_type": "page",
        "sort_order": 22,
        "required_permissions": ["system.ai_capabilities.manage"],
        "status": "active",
    },
    {
        "code": "system.scheduled_jobs",
        "name": "定时作业",
        "path": "/tasks/scheduled-jobs",
        "parent_code": "task",
        "menu_type": "page",
        "sort_order": 23,
        "required_permissions": ["system.scheduled_jobs.manage"],
        "status": "active",
    },
    {
        "code": "system.plugins",
        "name": "插件管理",
        "path": "/tasks/plugins",
        "parent_code": "task",
        "menu_type": "page",
        "sort_order": 24,
        "required_permissions": ["system.plugins.manage"],
        "status": "active",
    },
    {
        "code": "org.departments",
        "name": "部门管理",
        "path": "/system/departments",
        "parent_code": "system",
        "menu_type": "hidden_page",
        "sort_order": 66,
        "required_permissions": ["org.department.manage"],
        "status": "active",
    },
]

COMPATIBILITY_ROLE_MENU_GRANTS: dict[str, set[str]] = {
    "admin": {
        "workspace.dashboard",
        "assistant.chat",
        "task",
        "task.center",
        "delivery",
        "delivery.requirements",
        "delivery.requirement_full_chain",
        "delivery.versions",
        "delivery.bugs",
        "product.assets",
        "product.products",
        "knowledge.center",
        "knowledge.search",
        "governance",
        "devops.metrics",
        "insight.center",
        "audit.events",
        "code_inspection.reports",
        "system",
        "system.users",
        "system.roles",
        "system.model_gateway",
        "system.ai_capabilities",
        "system.scheduled_jobs",
        "system.plugins",
        "org.departments",
    },
    "product_owner": {
        "workspace.dashboard",
        "assistant.chat",
        "task",
        "task.center",
        "delivery",
        "delivery.requirements",
        "delivery.requirement_full_chain",
        "delivery.versions",
        "delivery.bugs",
        "product.assets",
        "product.products",
        "knowledge.center",
        "governance",
        "insight.center",
        "code_inspection.reports",
    },
    "rd_owner": {
        "workspace.dashboard",
        "assistant.chat",
        "task",
        "task.center",
        "delivery",
        "delivery.requirements",
        "delivery.bugs",
        "product.assets",
        "knowledge.center",
        "knowledge.search",
        "governance",
        "devops.metrics",
        "code_inspection.reports",
    },
    "reviewer": {"task", "task.center", "governance", "audit.events"},
    "knowledge_owner": {
        "workspace.dashboard",
        "assistant.chat",
        "product.assets",
        "knowledge.center",
        "knowledge.search",
        "governance",
        "audit.events",
    },
    "viewer": {
        "workspace.dashboard",
        "assistant.chat",
        "task",
        "task.center",
        "delivery",
        "delivery.requirements",
        "delivery.bugs",
        "product.assets",
        "knowledge.center",
        "knowledge.search",
    },
    "developer": {
        "workspace.dashboard",
        "assistant.chat",
        "task",
        "task.center",
        "delivery",
        "delivery.bugs",
        "product.assets",
        "knowledge.search",
    },
    "test_owner": {
        "workspace.dashboard",
        "assistant.chat",
        "task",
        "task.center",
        "delivery",
        "delivery.bugs",
    },
    "tester": {
        "workspace.dashboard",
        "assistant.chat",
        "task",
        "task.center",
        "delivery",
        "delivery.bugs",
    },
    "release_owner": {
        "workspace.dashboard",
        "assistant.chat",
        "task",
        "task.center",
        "delivery",
        "delivery.bugs",
        "governance",
        "devops.metrics",
    },
}

COMPATIBILITY_ROLE_SCOPES: dict[str, list[dict[str, str]]] = {
    "admin": [{"scope_type": "global", "scope_id": "*", "access_level": "admin"}],
    "reviewer": [
        {
            "scope_type": "review_assignment",
            "scope_id": "self",
            "access_level": "write",
        }
    ],
    "test_owner": [
        {
            "scope_type": "review_assignment",
            "scope_id": "self",
            "access_level": "write",
        }
    ],
    "knowledge_owner": [
        {"scope_type": "knowledge_space", "scope_id": "*", "access_level": "admin"}
    ],
    "viewer": [{"scope_type": "self", "scope_id": "*", "access_level": "read"}],
}


class CompatibilityAuthorizationRepository:
    def __init__(self) -> None:
        self._roles = {
            role["code"]: self._normalize_role(role, is_system=True)
            for role in ROLE_DEFINITIONS
        }
        self._role_menu_grants = {
            role_code: set(menu_codes)
            for role_code, menu_codes in COMPATIBILITY_ROLE_MENU_GRANTS.items()
        }
        self._role_scope_grants = deepcopy(COMPATIBILITY_ROLE_SCOPES)
        self._user_role_grants: dict[str, list[str]] = {}
        self._user_scope_grants: dict[str, list[dict[str, Any]]] = {}
        self.role_change_events: list[dict[str, Any]] = []
        self.audit_events: list[dict[str, Any]] = []
        self._permissions = self._build_permission_catalog()

    def _normalize_role(self, role: dict[str, Any], *, is_system: bool) -> dict[str, Any]:
        normalized = deepcopy(role)
        normalized.setdefault("id", f"role_{normalized['code']}")
        normalized.setdefault("description", "")
        normalized.setdefault("category", "workspace")
        normalized.setdefault("is_assignable", True)
        normalized.setdefault("sort_order", 0)
        normalized.setdefault("status", "active")
        normalized["is_system"] = bool(normalized.get("is_system", is_system))
        return normalized

    def _build_permission_catalog(self) -> dict[str, dict[str, Any]]:
        codes = {
            permission_code
            for role in self._roles.values()
            for permission_code in role.get("permissions", [])
        }
        return {
            code: {
                "code": code,
                "name": code,
                "category": code.split(".", 1)[0],
                "description": "",
                "risk_level": "normal",
                "is_system": True,
                "status": "active",
            }
            for code in sorted(codes)
        }

    def snapshot_for_user(self, user: dict[str, Any]) -> AuthorizationSnapshot:
        roles = self.role_codes_for_user(str(user["id"]), fallback_roles=user.get("roles") or [])
        permissions: set[str] = set()
        granted_codes: set[str] = set()
        scopes: list[dict[str, Any]] = []

        for role_code in roles:
            role = self._roles.get(role_code)
            if role is None or role.get("status", "active") != "active":
                continue
            if role_code == "admin":
                permissions.update(self._permissions)
                granted_codes.update(resource["code"] for resource in COMPATIBILITY_MENU_RESOURCES)
            else:
                permissions.update(role.get("permissions") or [])
                granted_codes.update(self._role_menu_grants.get(role_code, set()))
            scopes.extend(deepcopy(self._role_scope_grants.get(role_code, [])))
        scopes.extend(deepcopy(self._user_scope_grants.get(str(user["id"]), [])))

        return AuthorizationSnapshot(
            user_id=str(user["id"]),
            roles=roles,
            permissions=permissions,
            scopes=scopes,
            menus=[
                deepcopy(resource)
                for resource in COMPATIBILITY_MENU_RESOURCES
                if resource["code"] in granted_codes
            ],
        )

    def get_snapshot_for_user(self, user: dict[str, Any]) -> AuthorizationSnapshot:
        return self.snapshot_for_user(user)

    def menu_resources(self) -> list[dict[str, Any]]:
        return deepcopy(COMPATIBILITY_MENU_RESOURCES)

    def granted_menu_codes_for_roles(self, roles: list[str]) -> set[str]:
        if "admin" in roles:
            return {resource["code"] for resource in COMPATIBILITY_MENU_RESOURCES}
        granted_codes: set[str] = set()
        for role_code in roles:
            granted_codes.update(self._role_menu_grants.get(role_code, set()))
        return granted_codes

    def route_permissions(self) -> dict[str, list[str]]:
        return {
            resource["path"]: list(resource.get("required_permissions") or [])
            for resource in COMPATIBILITY_MENU_RESOURCES
            if resource.get("menu_type") == "hidden_page" and resource.get("path")
        }

    def list_permissions(self) -> list[dict[str, Any]]:
        return deepcopy(list(self._permissions.values()))

    def list_roles(self) -> list[dict[str, Any]]:
        return [
            self._role_detail(role)
            for role in sorted(
                self._roles.values(),
                key=lambda item: (item.get("sort_order", 0), item["code"]),
            )
        ]

    def get_role(self, role_id_or_code: str) -> dict[str, Any] | None:
        role = self._find_role(role_id_or_code)
        return self._role_detail(role) if role is not None else None

    def create_role(
        self,
        payload: dict[str, Any],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        code = str(payload["code"])
        if code in self._roles:
            raise ValueError("ROLE_CODE_EXISTS")
        role = self._normalize_role(
            {
                "id": f"role_{uuid4().hex}",
                "code": code,
                "name": payload["name"],
                "description": payload.get("description", ""),
                "category": payload.get("category", "workspace"),
                "is_assignable": payload.get("is_assignable", True),
                "permissions": [],
                "sort_order": payload.get("sort_order") or self._next_sort_order(),
                "status": "active",
            },
            is_system=False,
        )
        self._roles[code] = role
        self._role_menu_grants[code] = set()
        self._role_scope_grants[code] = []
        detail = self._role_detail(role)
        self._record_role_mutation(
            role_id=role["id"],
            event_type="role.created",
            audit_event_type="system.role.created",
            before_payload={},
            after_payload=detail,
            actor_id=actor_id,
            trace_id=trace_id,
        )
        return detail

    def copy_role(
        self,
        role_id_or_code: str,
        payload: dict[str, Any],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any] | None:
        source = self._find_role(role_id_or_code)
        if source is None:
            return None
        code = str(payload["code"])
        if code in self._roles:
            raise ValueError("ROLE_CODE_EXISTS")
        role = deepcopy(source)
        role.update(
            {
                "id": f"role_{uuid4().hex}",
                "code": code,
                "name": payload.get("name") or f"{source['name']} Copy",
                "description": payload.get("description", source.get("description", "")),
                "is_system": False,
                "sort_order": self._next_sort_order(),
                "status": "active",
            }
        )
        self._roles[code] = role
        self._role_menu_grants[code] = set(self._role_menu_grants.get(source["code"], set()))
        self._role_scope_grants[code] = deepcopy(self._role_scope_grants.get(source["code"], []))
        detail = self._role_detail(role)
        self._record_role_mutation(
            role_id=role["id"],
            event_type="role.copied",
            audit_event_type="system.role.copied",
            before_payload={"source_role_id": source["id"], "source_role_code": source["code"]},
            after_payload=detail,
            actor_id=actor_id,
            trace_id=trace_id,
        )
        return detail

    def update_role(
        self,
        role_id_or_code: str,
        updates: dict[str, Any],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any] | None:
        role = self._find_role(role_id_or_code)
        if role is None:
            return None
        before = self._role_detail(role)
        for field in ("name", "description", "category", "is_assignable", "sort_order"):
            if field in updates and updates[field] is not None:
                role[field] = updates[field]
        after = self._role_detail(role)
        self._record_role_mutation(
            role_id=role["id"],
            event_type="role.updated",
            audit_event_type="system.role.updated",
            before_payload=before,
            after_payload=after,
            actor_id=actor_id,
            trace_id=trace_id,
        )
        return after

    def set_role_status(
        self,
        role_id_or_code: str,
        status: str,
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any] | None:
        role = self._find_role(role_id_or_code)
        if role is None:
            return None
        if status == "inactive" and role.get("is_system"):
            raise ValueError("SYSTEM_ROLE_PROTECTED")
        before = self._role_detail(role)
        role["status"] = status
        after = self._role_detail(role)
        action = "enabled" if status == "active" else "disabled"
        self._record_role_mutation(
            role_id=role["id"],
            event_type=f"role.{action}",
            audit_event_type=f"system.role.{action}",
            before_payload=before,
            after_payload=after,
            actor_id=actor_id,
            trace_id=trace_id,
        )
        return after

    def set_role_permissions(
        self,
        role_id_or_code: str,
        permission_codes: list[str],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any] | None:
        role = self._find_role(role_id_or_code)
        if role is None:
            return None
        self._ensure_permission_codes(permission_codes)
        before = self._role_detail(role)
        role["permissions"] = sorted(dict.fromkeys(permission_codes))
        after = self._role_detail(role)
        self._record_role_mutation(
            role_id=role["id"],
            event_type="role.permissions_updated",
            audit_event_type="system.role.permissions_updated",
            before_payload=before,
            after_payload=after,
            actor_id=actor_id,
            trace_id=trace_id,
        )
        return after

    def set_role_menus(
        self,
        role_id_or_code: str,
        menu_codes: list[str],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any] | None:
        role = self._find_role(role_id_or_code)
        if role is None:
            return None
        self._ensure_menu_codes(menu_codes)
        before = self._role_detail(role)
        self._role_menu_grants[role["code"]] = set(menu_codes)
        after = self._role_detail(role)
        self._record_role_mutation(
            role_id=role["id"],
            event_type="role.menus_updated",
            audit_event_type="system.role.menus_updated",
            before_payload=before,
            after_payload=after,
            actor_id=actor_id,
            trace_id=trace_id,
        )
        return after

    def set_role_scopes(
        self,
        role_id_or_code: str,
        scopes: list[dict[str, Any]],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any] | None:
        role = self._find_role(role_id_or_code)
        if role is None:
            return None
        normalized_scopes = self._normalize_scopes(scopes)
        before = self._role_detail(role)
        self._role_scope_grants[role["code"]] = normalized_scopes
        after = self._role_detail(role)
        self._record_role_mutation(
            role_id=role["id"],
            event_type="role.scopes_updated",
            audit_event_type="system.role.scopes_updated",
            before_payload=before,
            after_payload=after,
            actor_id=actor_id,
            trace_id=trace_id,
        )
        return after

    def role_codes_for_user(
        self,
        user_id: str,
        *,
        fallback_roles: list[str] | None = None,
    ) -> list[str]:
        return list(dict.fromkeys(self._user_role_grants.get(user_id, fallback_roles or [])))

    def set_user_roles(
        self,
        user_id: str,
        role_codes: list[str],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        self._ensure_role_codes(role_codes)
        self._user_role_grants[user_id] = list(dict.fromkeys(role_codes))
        return {
            "user_id": user_id,
            "role_codes": self._user_role_grants[user_id],
            "trace_id": trace_id,
        }

    def set_user_scopes(
        self,
        user_id: str,
        scopes: list[dict[str, Any]],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        del actor_id
        normalized_scopes = self._normalize_scopes(scopes)
        self._user_scope_grants[user_id] = normalized_scopes
        return {"user_id": user_id, "scopes": deepcopy(normalized_scopes), "trace_id": trace_id}

    def effective_permissions_for_user(
        self,
        user: dict[str, Any],
    ) -> dict[str, Any]:
        snapshot = self.snapshot_for_user(user)
        return {
            "user_id": str(user["id"]),
            "role_codes": snapshot.roles,
            "permission_codes": sorted(snapshot.permissions),
            "scopes": snapshot.scopes,
            "menu_codes": sorted(menu["code"] for menu in snapshot.menus),
        }

    def _find_role(self, role_id_or_code: str) -> dict[str, Any] | None:
        return next(
            (
                role
                for role in self._roles.values()
                if role["id"] == role_id_or_code or role["code"] == role_id_or_code
            ),
            None,
        )

    def _role_detail(self, role: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": role["id"],
            "code": role["code"],
            "name": role["name"],
            "description": role.get("description", ""),
            "category": role.get("category", "workspace"),
            "is_system": bool(role.get("is_system", False)),
            "is_assignable": bool(role.get("is_assignable", True)),
            "status": role.get("status", "active"),
            "sort_order": int(role.get("sort_order", 0)),
            "permission_codes": sorted(
                self._permissions if role["code"] == "admin" else role.get("permissions") or []
            ),
            "menu_codes": sorted(
                {resource["code"] for resource in COMPATIBILITY_MENU_RESOURCES}
                if role["code"] == "admin"
                else self._role_menu_grants.get(role["code"], set())
            ),
            "scopes": deepcopy(self._role_scope_grants.get(role["code"], [])),
        }

    def _next_sort_order(self) -> int:
        return (
            max((int(role.get("sort_order", 0)) for role in self._roles.values()), default=0)
            + 10
        )

    def _ensure_role_codes(self, role_codes: list[str]) -> None:
        unsupported = sorted(set(role_codes) - set(self._roles))
        if unsupported:
            raise ValueError("UNSUPPORTED_ROLE")

    def _ensure_permission_codes(self, permission_codes: list[str]) -> None:
        unsupported = sorted(set(permission_codes) - set(self._permissions))
        if unsupported:
            raise ValueError("UNSUPPORTED_PERMISSION")

    def _ensure_menu_codes(self, menu_codes: list[str]) -> None:
        valid_codes = {menu["code"] for menu in COMPATIBILITY_MENU_RESOURCES}
        unsupported = sorted(set(menu_codes) - valid_codes)
        if unsupported:
            raise ValueError("UNSUPPORTED_MENU")

    def _normalize_scopes(self, scopes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for scope in scopes:
            scope_type = str(scope.get("scope_type", "")).strip()
            scope_id = str(scope.get("scope_id", "")).strip()
            access_level = str(scope.get("access_level", "read")).strip()
            if (
                scope_type not in VALID_SCOPE_TYPES
                or not scope_id
                or access_level not in VALID_SCOPE_ACCESS_LEVELS
            ):
                raise ValueError("INVALID_SCOPE")
            key = (scope_type, scope_id, access_level)
            if key in seen:
                continue
            seen.add(key)
            normalized.append(
                {
                    "scope_type": scope_type,
                    "scope_id": scope_id,
                    "access_level": access_level,
                }
            )
        return normalized

    def _record_role_mutation(
        self,
        *,
        role_id: str,
        event_type: str,
        audit_event_type: str,
        before_payload: dict[str, Any],
        after_payload: dict[str, Any],
        actor_id: str,
        trace_id: str,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        self.role_change_events.append(
            {
                "id": f"role_change_{uuid4().hex}",
                "role_id": role_id,
                "event_type": event_type,
                "before_payload": deepcopy(before_payload),
                "after_payload": deepcopy(after_payload),
                "actor_id": actor_id,
                "trace_id": trace_id,
                "created_at": now,
                "updated_at": now,
            }
        )
        self.audit_events.append(
            {
                "id": f"audit_event_{uuid4().hex}",
                "event_type": audit_event_type,
                "actor_id": actor_id,
                "ai_task_id": None,
                "subject_type": "role",
                "subject_id": role_id,
                "payload": {
                    "before": deepcopy(before_payload),
                    "after": deepcopy(after_payload),
                },
                "sequence": len(self.audit_events) + 1,
                "created_at": now,
                "updated_at": now,
            }
        )


class PostgresAuthorizationRepository(CompatibilityAuthorizationRepository):
    def __init__(self, database_url: str, *, pool_max_size: int = 5) -> None:
        super().__init__()
        self.database_url = database_url
        self._pool = DatabaseConnectionPool(
            factory=self._open_connection,
            max_size=pool_max_size,
        )

    def _open_connection(self):
        import psycopg

        last_error: Exception | None = None
        for _ in range(20):
            try:
                return psycopg.connect(self.database_url)
            except psycopg.OperationalError as exc:
                last_error = exc
                sleep(0.5)
        raise last_error or RuntimeError("PostgreSQL connection failed")

    def _connect(self):
        return self._pool.connection(autocommit=True)

    def snapshot_for_user(self, user: dict[str, Any]) -> AuthorizationSnapshot:
        roles = self._role_codes_for_user(user)
        permissions = self._permissions_for_roles(roles)
        scopes = self._scopes_for_roles(roles)
        granted_codes = self.granted_menu_codes_for_roles(roles)
        resources = self.menu_resources()
        return AuthorizationSnapshot(
            user_id=str(user["id"]),
            roles=roles,
            permissions=permissions,
            scopes=scopes,
            menus=[
                deepcopy(resource)
                for resource in resources
                if resource["code"] in granted_codes
            ],
        )

    def _role_codes_for_user(self, user: dict[str, Any]) -> list[str]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT DISTINCT r.code
                    FROM user_roles ur
                    JOIN roles r ON r.id = ur.role_id
                    WHERE ur.user_id = %s
                      AND ur.status = 'active'
                      AND ur.effective_from <= now()
                      AND (ur.expires_at IS NULL OR ur.expires_at > now())
                      AND r.status = 'active'
                    ORDER BY r.code
                    """,
                    (user["id"],),
                )
                rows = cursor.fetchall()
        role_codes = [str(row[0]) for row in rows]
        if role_codes:
            return role_codes
        fallback_roles = user.get("roles") or []
        if not fallback_roles:
            return []
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT code
                    FROM roles
                    WHERE code = ANY(%s)
                      AND status = 'active'
                    ORDER BY code
                    """,
                    (list(fallback_roles),),
                )
                rows = cursor.fetchall()
        return [str(row[0]) for row in rows]

    def _permissions_for_roles(self, roles: list[str]) -> set[str]:
        if not roles:
            return set()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if "admin" in roles:
                    cursor.execute(
                        """
                        SELECT code
                        FROM permissions
                        WHERE status = 'active'
                        ORDER BY code
                        """
                    )
                    return {str(row[0]) for row in cursor.fetchall()}
                cursor.execute(
                    """
                    SELECT DISTINCT rp.permission_code
                    FROM role_permissions rp
                    JOIN roles r ON r.id = rp.role_id
                    JOIN permissions p ON p.code = rp.permission_code
                    WHERE r.code = ANY(%s)
                      AND r.status = 'active'
                      AND p.status = 'active'
                    ORDER BY rp.permission_code
                    """,
                    (roles,),
                )
                rows = cursor.fetchall()
        return {str(row[0]) for row in rows}

    def _scopes_for_roles(self, roles: list[str]) -> list[dict[str, Any]]:
        if not roles:
            return []
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT DISTINCT rsg.scope_type, rsg.scope_id, rsg.access_level
                    FROM role_scope_grants rsg
                    JOIN roles r ON r.id = rsg.role_id
                    WHERE r.code = ANY(%s)
                      AND r.status = 'active'
                    ORDER BY rsg.scope_type, rsg.scope_id, rsg.access_level
                    """,
                    (roles,),
                )
                rows = cursor.fetchall()
        return [
            {
                "scope_type": scope_type,
                "scope_id": scope_id,
                "access_level": access_level,
            }
            for scope_type, scope_id, access_level in rows
        ]

    def menu_resources(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT code, name, path, parent_code, menu_type, sort_order,
                           required_permissions, status
                    FROM menu_resources
                    ORDER BY sort_order, code
                    """
                )
                rows = cursor.fetchall()
        return [
            {
                "code": code,
                "name": name,
                "path": path,
                "parent_code": parent_code,
                "menu_type": menu_type,
                "sort_order": sort_order,
                "required_permissions": list(required_permissions or []),
                "status": status,
            }
            for (
                code,
                name,
                path,
                parent_code,
                menu_type,
                sort_order,
                required_permissions,
                status,
            ) in rows
        ]

    def granted_menu_codes_for_roles(self, roles: list[str]) -> set[str]:
        if not roles:
            return set()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if "admin" in roles:
                    cursor.execute(
                        """
                        SELECT code
                        FROM menu_resources
                        WHERE status = 'active'
                        ORDER BY code
                        """
                    )
                    return {str(row[0]) for row in cursor.fetchall()}
                cursor.execute(
                    """
                    SELECT DISTINCT rmg.menu_code
                    FROM role_menu_grants rmg
                    JOIN roles r ON r.id = rmg.role_id
                    JOIN menu_resources m ON m.code = rmg.menu_code
                    WHERE r.code = ANY(%s)
                      AND r.status = 'active'
                      AND m.status = 'active'
                    ORDER BY rmg.menu_code
                    """,
                    (roles,),
                )
                rows = cursor.fetchall()
        return {str(row[0]) for row in rows}

    def list_permissions(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT code, name, category, description, risk_level, is_system, status
                    FROM permissions
                    ORDER BY category, code
                    """
                )
                rows = cursor.fetchall()
        return [
            {
                "code": code,
                "name": name,
                "category": category,
                "description": description,
                "risk_level": risk_level,
                "is_system": is_system,
                "status": status,
            }
            for code, name, category, description, risk_level, is_system, status in rows
        ]

    def list_roles(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, code, name, description, category, is_system,
                           is_assignable, status, sort_order
                    FROM roles
                    ORDER BY sort_order, code
                    """
                )
                rows = cursor.fetchall()
        return [self._postgres_role_detail_from_row(row) for row in rows]

    def get_role(self, role_id_or_code: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                row = self._postgres_role_row(cursor, role_id_or_code)
                if row is None:
                    return None
                return self._postgres_role_detail_from_row(row, cursor=cursor)

    def create_role(
        self,
        payload: dict[str, Any],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        role_id = f"role_{uuid4().hex}"
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO roles (
                          id, code, name, description, category, is_system,
                          is_assignable, status, sort_order, created_by, updated_by
                        )
                        VALUES (%s, %s, %s, %s, %s, false, %s, 'active', %s, %s, %s)
                        """,
                        (
                            role_id,
                            payload["code"],
                            payload["name"],
                            payload.get("description", ""),
                            payload.get("category", "workspace"),
                            payload.get("is_assignable", True),
                            payload.get("sort_order") or 0,
                            actor_id,
                            actor_id,
                        ),
                    )
                    after = self._postgres_role_detail_from_row(
                        self._postgres_role_row(cursor, role_id),
                        cursor=cursor,
                    )
                    self._insert_role_mutation(
                        cursor,
                        role_id=role_id,
                        event_type="role.created",
                        audit_event_type="system.role.created",
                        before_payload={},
                        after_payload=after,
                        actor_id=actor_id,
                        trace_id=trace_id,
                    )
                    return after
        except Exception as exc:
            if getattr(exc, "sqlstate", "") == "23505":
                raise ValueError("ROLE_CODE_EXISTS") from exc
            raise

    def copy_role(
        self,
        role_id_or_code: str,
        payload: dict[str, Any],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any] | None:
        role_id = f"role_{uuid4().hex}"
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    source_row = self._postgres_role_row(cursor, role_id_or_code)
                    if source_row is None:
                        return None
                    source = self._postgres_role_detail_from_row(source_row, cursor=cursor)
                    cursor.execute(
                        """
                        INSERT INTO roles (
                          id, code, name, description, category, is_system,
                          is_assignable, status, sort_order, created_by, updated_by
                        )
                        VALUES (%s, %s, %s, %s, %s, false, %s, 'active', %s, %s, %s)
                        """,
                        (
                            role_id,
                            payload["code"],
                            payload.get("name") or f"{source['name']} Copy",
                            payload.get("description", source.get("description", "")),
                            source["category"],
                            source["is_assignable"],
                            source["sort_order"] + 10,
                            actor_id,
                            actor_id,
                        ),
                    )
                    cursor.execute(
                        """
                        INSERT INTO role_permissions (role_id, permission_code, granted_by)
                        SELECT %s, permission_code, %s
                        FROM role_permissions
                        WHERE role_id = %s
                        ON CONFLICT (role_id, permission_code) DO NOTHING
                        """,
                        (role_id, actor_id, source["id"]),
                    )
                    cursor.execute(
                        """
                        INSERT INTO role_menu_grants (role_id, menu_code, granted_by)
                        SELECT %s, menu_code, %s
                        FROM role_menu_grants
                        WHERE role_id = %s
                        ON CONFLICT (role_id, menu_code) DO NOTHING
                        """,
                        (role_id, actor_id, source["id"]),
                    )
                    cursor.execute(
                        """
                        INSERT INTO role_scope_grants (
                          role_id, scope_type, scope_id, access_level, granted_by
                        )
                        SELECT %s, scope_type, scope_id, access_level, %s
                        FROM role_scope_grants
                        WHERE role_id = %s
                        ON CONFLICT (role_id, scope_type, scope_id, access_level) DO NOTHING
                        """,
                        (role_id, actor_id, source["id"]),
                    )
                    after = self._postgres_role_detail_from_row(
                        self._postgres_role_row(cursor, role_id),
                        cursor=cursor,
                    )
                    self._insert_role_mutation(
                        cursor,
                        role_id=role_id,
                        event_type="role.copied",
                        audit_event_type="system.role.copied",
                        before_payload={
                            "source_role_id": source["id"],
                            "source_role_code": source["code"],
                        },
                        after_payload=after,
                        actor_id=actor_id,
                        trace_id=trace_id,
                    )
                    return after
        except Exception as exc:
            if getattr(exc, "sqlstate", "") == "23505":
                raise ValueError("ROLE_CODE_EXISTS") from exc
            raise

    def update_role(
        self,
        role_id_or_code: str,
        updates: dict[str, Any],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any] | None:
        fields: list[str] = []
        values: list[Any] = []
        for field in ("name", "description", "category", "is_assignable", "sort_order"):
            if field in updates and updates[field] is not None:
                fields.append(f"{field} = %s")
                values.append(updates[field])
        if not fields:
            return self.get_role(role_id_or_code)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                row = self._postgres_role_row(cursor, role_id_or_code)
                if row is None:
                    return None
                before = self._postgres_role_detail_from_row(row, cursor=cursor)
                values.extend([actor_id, before["id"]])
                cursor.execute(
                    f"""
                    UPDATE roles
                    SET {", ".join(fields)}, updated_by = %s, updated_at = now()
                    WHERE id = %s
                    """,
                    values,
                )
                after = self._postgres_role_detail_from_row(
                    self._postgres_role_row(cursor, before["id"]),
                    cursor=cursor,
                )
                self._insert_role_mutation(
                    cursor,
                    role_id=before["id"],
                    event_type="role.updated",
                    audit_event_type="system.role.updated",
                    before_payload=before,
                    after_payload=after,
                    actor_id=actor_id,
                    trace_id=trace_id,
                )
                return after

    def set_role_status(
        self,
        role_id_or_code: str,
        status: str,
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                row = self._postgres_role_row(cursor, role_id_or_code)
                if row is None:
                    return None
                before = self._postgres_role_detail_from_row(row, cursor=cursor)
                if status == "inactive" and before["is_system"]:
                    raise ValueError("SYSTEM_ROLE_PROTECTED")
                cursor.execute(
                    """
                    UPDATE roles
                    SET status = %s, updated_by = %s, updated_at = now()
                    WHERE id = %s
                    """,
                    (status, actor_id, before["id"]),
                )
                after = self._postgres_role_detail_from_row(
                    self._postgres_role_row(cursor, before["id"]),
                    cursor=cursor,
                )
                action = "enabled" if status == "active" else "disabled"
                self._insert_role_mutation(
                    cursor,
                    role_id=before["id"],
                    event_type=f"role.{action}",
                    audit_event_type=f"system.role.{action}",
                    before_payload=before,
                    after_payload=after,
                    actor_id=actor_id,
                    trace_id=trace_id,
                )
                return after

    def set_role_permissions(
        self,
        role_id_or_code: str,
        permission_codes: list[str],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                row = self._postgres_role_row(cursor, role_id_or_code)
                if row is None:
                    return None
                before = self._postgres_role_detail_from_row(row, cursor=cursor)
                self._postgres_ensure_permission_codes(cursor, permission_codes)
                cursor.execute("DELETE FROM role_permissions WHERE role_id = %s", (before["id"],))
                for permission_code in sorted(dict.fromkeys(permission_codes)):
                    cursor.execute(
                        """
                        INSERT INTO role_permissions (role_id, permission_code, granted_by)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (role_id, permission_code) DO UPDATE SET
                          granted_by = EXCLUDED.granted_by,
                          updated_at = now()
                        """,
                        (before["id"], permission_code, actor_id),
                    )
                after = self._postgres_role_detail_from_row(
                    self._postgres_role_row(cursor, before["id"]),
                    cursor=cursor,
                )
                self._insert_role_mutation(
                    cursor,
                    role_id=before["id"],
                    event_type="role.permissions_updated",
                    audit_event_type="system.role.permissions_updated",
                    before_payload=before,
                    after_payload=after,
                    actor_id=actor_id,
                    trace_id=trace_id,
                )
                return after

    def set_role_menus(
        self,
        role_id_or_code: str,
        menu_codes: list[str],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                row = self._postgres_role_row(cursor, role_id_or_code)
                if row is None:
                    return None
                before = self._postgres_role_detail_from_row(row, cursor=cursor)
                self._postgres_ensure_menu_codes(cursor, menu_codes)
                cursor.execute("DELETE FROM role_menu_grants WHERE role_id = %s", (before["id"],))
                for menu_code in sorted(dict.fromkeys(menu_codes)):
                    cursor.execute(
                        """
                        INSERT INTO role_menu_grants (role_id, menu_code, granted_by)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (role_id, menu_code) DO UPDATE SET
                          granted_by = EXCLUDED.granted_by,
                          updated_at = now()
                        """,
                        (before["id"], menu_code, actor_id),
                    )
                after = self._postgres_role_detail_from_row(
                    self._postgres_role_row(cursor, before["id"]),
                    cursor=cursor,
                )
                self._insert_role_mutation(
                    cursor,
                    role_id=before["id"],
                    event_type="role.menus_updated",
                    audit_event_type="system.role.menus_updated",
                    before_payload=before,
                    after_payload=after,
                    actor_id=actor_id,
                    trace_id=trace_id,
                )
                return after

    def set_role_scopes(
        self,
        role_id_or_code: str,
        scopes: list[dict[str, Any]],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any] | None:
        normalized_scopes = self._normalize_scopes(scopes)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                row = self._postgres_role_row(cursor, role_id_or_code)
                if row is None:
                    return None
                before = self._postgres_role_detail_from_row(row, cursor=cursor)
                cursor.execute("DELETE FROM role_scope_grants WHERE role_id = %s", (before["id"],))
                for scope in normalized_scopes:
                    cursor.execute(
                        """
                        INSERT INTO role_scope_grants (
                          role_id, scope_type, scope_id, access_level, granted_by
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (role_id, scope_type, scope_id, access_level) DO UPDATE SET
                          granted_by = EXCLUDED.granted_by,
                          updated_at = now()
                        """,
                        (
                            before["id"],
                            scope["scope_type"],
                            scope["scope_id"],
                            scope["access_level"],
                            actor_id,
                        ),
                    )
                after = self._postgres_role_detail_from_row(
                    self._postgres_role_row(cursor, before["id"]),
                    cursor=cursor,
                )
                self._insert_role_mutation(
                    cursor,
                    role_id=before["id"],
                    event_type="role.scopes_updated",
                    audit_event_type="system.role.scopes_updated",
                    before_payload=before,
                    after_payload=after,
                    actor_id=actor_id,
                    trace_id=trace_id,
                )
                return after

    def set_user_roles(
        self,
        user_id: str,
        role_codes: list[str],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        del trace_id
        with self._connect() as connection:
            with connection.cursor() as cursor:
                self._postgres_ensure_role_codes(cursor, role_codes)
                cursor.execute(
                    "DELETE FROM user_roles WHERE user_id = %s",
                    (user_id,),
                )
                for role_code in list(dict.fromkeys(role_codes)):
                    cursor.execute(
                        """
                        INSERT INTO user_roles (user_id, role_id, granted_by, grant_reason, status)
                        SELECT %s, id, %s, 'system RBAC API assignment', 'active'
                        FROM roles
                        WHERE code = %s
                        ON CONFLICT (user_id, role_id, status) DO UPDATE SET
                          granted_by = EXCLUDED.granted_by,
                          revoked_by = NULL,
                          revoked_at = NULL,
                          updated_at = now()
                        """,
                        (user_id, actor_id, role_code),
                    )
                cursor.execute(
                    "UPDATE users SET roles = %s::jsonb, updated_at = now() WHERE id = %s",
                    (json.dumps(list(dict.fromkeys(role_codes)), ensure_ascii=False), user_id),
                )
        return {"user_id": user_id, "role_codes": list(dict.fromkeys(role_codes))}

    def set_user_scopes(
        self,
        user_id: str,
        scopes: list[dict[str, Any]],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        del trace_id
        normalized_scopes = self._normalize_scopes(scopes)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE user_scope_grants
                    SET status = 'revoked', updated_at = now()
                    WHERE user_id = %s AND status = 'active'
                    """,
                    (user_id,),
                )
                for scope in normalized_scopes:
                    cursor.execute(
                        """
                        INSERT INTO user_scope_grants (
                          user_id, scope_type, scope_id, access_level, granted_by, status
                        )
                        VALUES (%s, %s, %s, %s, %s, 'active')
                        ON CONFLICT (user_id, scope_type, scope_id, access_level, status)
                        DO UPDATE SET
                          granted_by = EXCLUDED.granted_by,
                          updated_at = now()
                        """,
                        (
                            user_id,
                            scope["scope_type"],
                            scope["scope_id"],
                            scope["access_level"],
                            actor_id,
                        ),
                    )
        return {"user_id": user_id, "scopes": normalized_scopes}

    def effective_permissions_for_user(self, user: dict[str, Any]) -> dict[str, Any]:
        snapshot = self.snapshot_for_user(user)
        return {
            "user_id": str(user["id"]),
            "role_codes": snapshot.roles,
            "permission_codes": sorted(snapshot.permissions),
            "scopes": snapshot.scopes,
            "menu_codes": sorted(menu["code"] for menu in snapshot.menus),
        }

    def _postgres_role_row(self, cursor, role_id_or_code: str):
        cursor.execute(
            """
            SELECT id, code, name, description, category, is_system,
                   is_assignable, status, sort_order
            FROM roles
            WHERE id = %s OR code = %s
            """,
            (role_id_or_code, role_id_or_code),
        )
        return cursor.fetchone()

    def _postgres_role_detail_from_row(self, row, *, cursor=None) -> dict[str, Any]:
        (
            role_id,
            code,
            name,
            description,
            category,
            is_system,
            is_assignable,
            status,
            sort_order,
        ) = row
        if cursor is None:
            with self._connect() as connection:
                with connection.cursor() as local_cursor:
                    permission_codes = self._postgres_permission_codes(local_cursor, role_id, code)
                    menu_codes = self._postgres_menu_codes(local_cursor, role_id, code)
                    scopes = self._postgres_scope_grants(local_cursor, role_id)
        else:
            permission_codes = self._postgres_permission_codes(cursor, role_id, code)
            menu_codes = self._postgres_menu_codes(cursor, role_id, code)
            scopes = self._postgres_scope_grants(cursor, role_id)
        return {
            "id": role_id,
            "code": code,
            "name": name,
            "description": description,
            "category": category,
            "is_system": is_system,
            "is_assignable": is_assignable,
            "status": status,
            "sort_order": sort_order,
            "permission_codes": permission_codes,
            "menu_codes": menu_codes,
            "scopes": scopes,
        }

    def _postgres_permission_codes(self, cursor, role_id: str, role_code: str) -> list[str]:
        if role_code == "admin":
            cursor.execute(
                """
                SELECT code
                FROM permissions
                WHERE status = 'active'
                ORDER BY code
                """
            )
            return [str(row[0]) for row in cursor.fetchall()]
        cursor.execute(
            """
            SELECT permission_code
            FROM role_permissions
            WHERE role_id = %s
            ORDER BY permission_code
            """,
            (role_id,),
        )
        return [str(row[0]) for row in cursor.fetchall()]

    def _postgres_menu_codes(self, cursor, role_id: str, role_code: str) -> list[str]:
        if role_code == "admin":
            cursor.execute(
                """
                SELECT code
                FROM menu_resources
                WHERE status = 'active'
                ORDER BY code
                """
            )
            return [str(row[0]) for row in cursor.fetchall()]
        cursor.execute(
            """
            SELECT menu_code
            FROM role_menu_grants
            WHERE role_id = %s
            ORDER BY menu_code
            """,
            (role_id,),
        )
        return [str(row[0]) for row in cursor.fetchall()]

    def _postgres_scope_grants(self, cursor, role_id: str) -> list[dict[str, Any]]:
        cursor.execute(
            """
            SELECT scope_type, scope_id, access_level
            FROM role_scope_grants
            WHERE role_id = %s
            ORDER BY scope_type, scope_id, access_level
            """,
            (role_id,),
        )
        return [
            {
                "scope_type": scope_type,
                "scope_id": scope_id,
                "access_level": access_level,
            }
            for scope_type, scope_id, access_level in cursor.fetchall()
        ]

    def _postgres_ensure_role_codes(self, cursor, role_codes: list[str]) -> None:
        if not role_codes:
            return
        cursor.execute("SELECT code FROM roles WHERE code = ANY(%s)", (role_codes,))
        existing = {str(row[0]) for row in cursor.fetchall()}
        if set(role_codes) - existing:
            raise ValueError("UNSUPPORTED_ROLE")

    def _postgres_ensure_permission_codes(self, cursor, permission_codes: list[str]) -> None:
        if not permission_codes:
            return
        cursor.execute("SELECT code FROM permissions WHERE code = ANY(%s)", (permission_codes,))
        existing = {str(row[0]) for row in cursor.fetchall()}
        if set(permission_codes) - existing:
            raise ValueError("UNSUPPORTED_PERMISSION")

    def _postgres_ensure_menu_codes(self, cursor, menu_codes: list[str]) -> None:
        if not menu_codes:
            return
        cursor.execute("SELECT code FROM menu_resources WHERE code = ANY(%s)", (menu_codes,))
        existing = {str(row[0]) for row in cursor.fetchall()}
        if set(menu_codes) - existing:
            raise ValueError("UNSUPPORTED_MENU")

    def _insert_role_mutation(
        self,
        cursor,
        *,
        role_id: str,
        event_type: str,
        audit_event_type: str,
        before_payload: dict[str, Any],
        after_payload: dict[str, Any],
        actor_id: str,
        trace_id: str,
    ) -> None:
        cursor.execute(
            """
            INSERT INTO role_change_events (
              id, role_id, event_type, before_payload, after_payload, actor_id, trace_id
            )
            VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
            """,
            (
                f"role_change_{uuid4().hex}",
                role_id,
                event_type,
                json.dumps(before_payload, ensure_ascii=False),
                json.dumps(after_payload, ensure_ascii=False),
                actor_id,
                trace_id,
            ),
        )
        cursor.execute(
            """
            INSERT INTO audit_events (
              id, event_type, actor_id, ai_task_id, subject_type, subject_id, payload, sequence
            )
            VALUES (%s, %s, %s, NULL, 'role', %s, %s::jsonb, 0)
            """,
            (
                f"audit_event_{uuid4().hex}",
                audit_event_type,
                actor_id,
                role_id,
                json.dumps(
                    {"before": before_payload, "after": after_payload},
                    ensure_ascii=False,
                ),
            ),
        )
