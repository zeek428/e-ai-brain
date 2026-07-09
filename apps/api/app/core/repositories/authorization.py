from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from time import sleep
from typing import Any
from uuid import uuid4

from app.core.authorization import AuthorizationSnapshot
from app.core.db import DatabaseConnectionPool
from app.core.repositories.authorization_defaults import (
    COMPATIBILITY_MENU_RESOURCES,
    COMPATIBILITY_ROLE_MENU_GRANTS,
    COMPATIBILITY_ROLE_SCOPES,
    MENU_RESOURCE_SORT_COLUMNS,
    ROLE_METADATA_BY_CODE,
    ROLE_METADATA_FIELDS,
    ROLE_METADATA_LIST_FIELDS,
    ROLE_SUMMARY_SORT_COLUMNS,
    VALID_SCOPE_ACCESS_LEVELS,
    VALID_SCOPE_TYPES,
)
from app.core.roles import ROLE_DEFINITIONS

ROLE_PERMISSION_TEMPLATE_BY_CODE: dict[str, set[str]] = {
    str(role["code"]): {str(permission) for permission in role.get("permissions") or []}
    for role in ROLE_DEFINITIONS
}

PRODUCT_MEMBER_ROLE_LABELS: dict[str, str] = {
    "product_owner": "产品经理",
    "rd_owner": "研发负责人",
    "developer": "开发工程师",
    "test_owner": "测试负责人",
    "tester": "测试人员",
    "release_owner": "运维/发布负责人",
    "viewer": "观察者",
}

PRODUCT_MEMBER_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "product_owner": ROLE_PERMISSION_TEMPLATE_BY_CODE.get("product_owner", set())
    | {"product.read", "product.manage", "product.member.read", "product.member.manage"},
    "rd_owner": ROLE_PERMISSION_TEMPLATE_BY_CODE.get("rd_owner", set()) | {"product.read"},
    "developer": ROLE_PERMISSION_TEMPLATE_BY_CODE.get("developer", set())
    | {"product.read", "requirement.read", "bug.manage"},
    "test_owner": ROLE_PERMISSION_TEMPLATE_BY_CODE.get("test_owner", set())
    | {"product.read", "bug.manage", "test.read"},
    "tester": ROLE_PERMISSION_TEMPLATE_BY_CODE.get("tester", set())
    | {"product.read", "bug.read", "test.read"},
    "release_owner": ROLE_PERMISSION_TEMPLATE_BY_CODE.get("release_owner", set())
    | {"product.read", "release.read", "bug.read"},
    "viewer": ROLE_PERMISSION_TEMPLATE_BY_CODE.get("viewer", set()) | {"product.read"},
}

PRODUCT_MEMBER_ROLES = set(PRODUCT_MEMBER_ROLE_LABELS)
PRODUCT_MEMBER_SCOPE_TYPES = {"product"}
PRODUCT_MEMBER_STATUSES = {"active", "inactive"}


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
        self._product_members: dict[str, list[dict[str, Any]]] = {}
        self._user_role_grants: dict[str, list[str]] = {}
        self._user_scope_grants: dict[str, list[dict[str, Any]]] = {}
        self._menu_resources = [
            {**deepcopy(resource), "is_system": resource.get("is_system", True)}
            for resource in COMPATIBILITY_MENU_RESOURCES
        ]
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
                granted_codes.update(resource["code"] for resource in self._menu_resources)
            else:
                permissions.update(role.get("permissions") or [])
                granted_codes.update(self._role_menu_grants.get(role_code, set()))
            scopes.extend(deepcopy(self._role_scope_grants.get(role_code, [])))
        scopes.extend(deepcopy(self._user_scope_grants.get(str(user["id"]), [])))
        member_permissions, member_scopes = self._product_member_authorization_for_user(
            str(user["id"])
        )
        permissions.update(member_permissions)
        scopes.extend(member_scopes)

        return AuthorizationSnapshot(
            user_id=str(user["id"]),
            roles=roles,
            permissions=permissions,
            scopes=scopes,
            menus=[
                deepcopy(resource)
                for resource in self._menu_resources
                if resource["code"] in granted_codes
            ],
        )

    def get_snapshot_for_user(self, user: dict[str, Any]) -> AuthorizationSnapshot:
        return self.snapshot_for_user(user)

    def menu_resources(self) -> list[dict[str, Any]]:
        return deepcopy(
            sorted(
                self._menu_resources,
                key=lambda item: (item.get("sort_order", 0), item["code"]),
            )
        )

    def count_menu_resources(
        self,
        *,
        menu: str | None,
        menu_type: str | None,
        parent: str | None,
        path: str | None,
        permission: str | None,
        status: str | None,
    ) -> int:
        return len(
            self._filter_menu_resources(
                menu=menu,
                menu_type=menu_type,
                parent=parent,
                path=path,
                permission=permission,
                status=status,
            )
        )

    def list_menu_resources_page(
        self,
        *,
        limit: int,
        menu: str | None,
        menu_type: str | None,
        offset: int,
        parent: str | None,
        path: str | None,
        permission: str | None,
        sort_by: str,
        sort_order: str,
        status: str | None,
    ) -> list[dict[str, Any]]:
        items = self._filter_menu_resources(
            menu=menu,
            menu_type=menu_type,
            parent=parent,
            path=path,
            permission=permission,
            status=status,
        )
        reverse = sort_order == "desc"
        sorted_items = sorted(
            items,
            key=lambda item: self._menu_resource_sort_value(item, sort_by),
            reverse=reverse,
        )
        return deepcopy(sorted_items[offset : offset + limit])

    def _filter_menu_resources(
        self,
        *,
        menu: str | None,
        menu_type: str | None,
        parent: str | None,
        path: str | None,
        permission: str | None,
        status: str | None,
    ) -> list[dict[str, Any]]:
        parent_names = {
            item["code"]: item.get("name", "")
            for item in self._menu_resources
        }

        def contains(value: Any, keyword: str | None) -> bool:
            normalized = str(keyword or "").strip().lower()
            return not normalized or normalized in str(value or "").lower()

        filtered: list[dict[str, Any]] = []
        for item in self._menu_resources:
            parent_code = item.get("parent_code")
            parent_text = " ".join(
                str(value or "")
                for value in (parent_code, parent_names.get(str(parent_code or ""), ""))
            )
            permission_text = " ".join(str(code) for code in item.get("required_permissions") or [])
            if (
                contains(f"{item.get('code', '')} {item.get('name', '')}", menu)
                and contains(parent_text, parent)
                and contains(item.get("path"), path)
                and contains(permission_text, permission)
                and (not menu_type or item.get("menu_type") == menu_type)
                and (not status or item.get("status") == status)
            ):
                filtered.append(deepcopy(item))
        return filtered

    def _menu_resource_sort_value(
        self,
        item: dict[str, Any],
        sort_by: str,
    ) -> tuple[int, str | int]:
        if sort_by == "parent_code":
            value = item.get("parent_code") or ""
        elif sort_by == "sort_order":
            return (0, int(item.get("sort_order") or 0))
        else:
            value = item.get(sort_by) or ""
        return (1, str(value).lower())

    def create_menu_resource(
        self,
        payload: dict[str, Any],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        code = str(payload["code"])
        if self._find_menu_resource(code) is not None:
            raise ValueError("MENU_CODE_EXISTS")
        menu = self._normalize_menu_payload(payload, is_system=False)
        self._menu_resources.append(menu)
        self._record_menu_mutation(
            menu_code=code,
            event_type="menu.created",
            audit_event_type="system.menu.created",
            before_payload={},
            after_payload=menu,
            actor_id=actor_id,
            trace_id=trace_id,
        )
        return deepcopy(menu)

    def update_menu_resource(
        self,
        menu_code: str,
        updates: dict[str, Any],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any] | None:
        menu = self._find_menu_resource(menu_code)
        if menu is None:
            return None
        before = deepcopy(menu)
        for field in (
            "icon",
            "menu_type",
            "name",
            "parent_code",
            "path",
            "required_permissions",
            "sort_order",
            "status",
        ):
            if field in updates:
                menu[field] = updates[field]
        normalized = self._normalize_menu_payload(
            menu,
            is_system=bool(menu.get("is_system", False)),
        )
        menu.clear()
        menu.update(normalized)
        self._record_menu_mutation(
            menu_code=menu_code,
            event_type="menu.updated",
            audit_event_type="system.menu.updated",
            before_payload=before,
            after_payload=menu,
            actor_id=actor_id,
            trace_id=trace_id,
        )
        return deepcopy(menu)

    def set_menu_status(
        self,
        menu_code: str,
        status: str,
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any] | None:
        return self.update_menu_resource(
            menu_code,
            {"status": status},
            actor_id=actor_id,
            trace_id=trace_id,
        )

    def delete_menu_resource(
        self,
        menu_code: str,
        *,
        actor_id: str,
        trace_id: str,
    ) -> bool | None:
        menu = self._find_menu_resource(menu_code)
        if menu is None:
            return None
        if menu.get("is_system"):
            raise ValueError("SYSTEM_MENU_PROTECTED")
        if any(item.get("parent_code") == menu_code for item in self._menu_resources):
            raise ValueError("MENU_HAS_CHILDREN")
        before = deepcopy(menu)
        self._menu_resources = [item for item in self._menu_resources if item["code"] != menu_code]
        for grants in self._role_menu_grants.values():
            grants.discard(menu_code)
        self._record_menu_mutation(
            menu_code=menu_code,
            event_type="menu.deleted",
            audit_event_type="system.menu.deleted",
            before_payload=before,
            after_payload={},
            actor_id=actor_id,
            trace_id=trace_id,
        )
        return True

    def reorder_menu_resources(
        self,
        items: list[dict[str, Any]],
        *,
        actor_id: str,
        trace_id: str,
    ) -> list[dict[str, Any]]:
        updated: list[dict[str, Any]] = []
        for item in items:
            menu = self._find_menu_resource(str(item["code"]))
            if menu is None:
                raise ValueError("UNSUPPORTED_MENU")
            before = deepcopy(menu)
            menu["sort_order"] = int(item["sort_order"])
            self._record_menu_mutation(
                menu_code=menu["code"],
                event_type="menu.reordered",
                audit_event_type="system.menu.reordered",
                before_payload=before,
                after_payload=menu,
                actor_id=actor_id,
                trace_id=trace_id,
            )
            updated.append(deepcopy(menu))
        return updated

    def granted_menu_codes_for_roles(self, roles: list[str]) -> set[str]:
        if "admin" in roles:
            return {resource["code"] for resource in self._menu_resources}
        granted_codes: set[str] = set()
        for role_code in roles:
            granted_codes.update(self._role_menu_grants.get(role_code, set()))
        return granted_codes

    def route_permissions(self) -> dict[str, list[str]]:
        return {
            resource["path"]: list(resource.get("required_permissions") or [])
            for resource in self._menu_resources
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

    def delete_user_grants(
        self,
        user_id: str,
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        del actor_id
        removed_roles = len(self._user_role_grants.pop(user_id, []))
        removed_scopes = len(self._user_scope_grants.pop(user_id, []))
        removed_product_members = 0
        for product_id, members in list(self._product_members.items()):
            retained_members = [member for member in members if member.get("user_id") != user_id]
            removed_product_members += len(members) - len(retained_members)
            if retained_members:
                self._product_members[product_id] = retained_members
            else:
                self._product_members.pop(product_id, None)
        return {
            "removed_product_members": removed_product_members,
            "removed_roles": removed_roles,
            "removed_scopes": removed_scopes,
            "trace_id": trace_id,
            "user_id": user_id,
        }

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

    def list_product_members(
        self,
        product_id: str,
        *,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        members = self._product_members.get(product_id, [])
        return deepcopy(
            [
                member
                for member in sorted(
                    members,
                    key=lambda item: (
                        item.get("member_role", ""),
                        item.get("user_id", ""),
                        item.get("scope_type", ""),
                        item.get("scope_id", ""),
                    ),
                )
                if not active_only or member.get("status") == "active"
            ]
        )

    def set_product_members(
        self,
        product_id: str,
        members: list[dict[str, Any]],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        before = self.list_product_members(product_id, active_only=False)
        normalized_members = self._normalize_product_members(product_id, members)
        self._product_members[product_id] = normalized_members
        after = self.list_product_members(product_id, active_only=False)
        self._record_product_members_mutation(
            product_id=product_id,
            before_payload={"items": before},
            after_payload={"items": after},
            actor_id=actor_id,
            trace_id=trace_id,
        )
        return {
            "items": self.list_product_members(product_id, active_only=True),
            "product_id": product_id,
            "trace_id": trace_id,
        }

    def _normalize_product_members(
        self,
        product_id: str,
        members: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str, str]] = set()
        now = datetime.now(UTC).isoformat()
        for member in members:
            user_id = str(member.get("user_id") or "").strip()
            member_role = str(member.get("member_role") or "").strip()
            scope_type = str(member.get("scope_type") or "product").strip()
            scope_id = str(member.get("scope_id") or "*").strip()
            status = str(member.get("status") or "active").strip()
            if not user_id:
                raise ValueError("PRODUCT_MEMBER_USER_REQUIRED")
            if member_role not in PRODUCT_MEMBER_ROLES:
                raise ValueError("UNSUPPORTED_PRODUCT_MEMBER_ROLE")
            if scope_type not in PRODUCT_MEMBER_SCOPE_TYPES:
                raise ValueError("UNSUPPORTED_PRODUCT_MEMBER_SCOPE")
            if scope_type == "product" and scope_id not in {"*", product_id}:
                raise ValueError("UNSUPPORTED_PRODUCT_MEMBER_SCOPE")
            if status not in PRODUCT_MEMBER_STATUSES:
                raise ValueError("UNSUPPORTED_PRODUCT_MEMBER_STATUS")
            key = (user_id, member_role, scope_type, scope_id)
            if key in seen:
                continue
            seen.add(key)
            normalized.append(
                {
                    "created_at": now,
                    "member_role": member_role,
                    "product_id": product_id,
                    "scope_id": scope_id,
                    "scope_type": scope_type,
                    "status": status,
                    "updated_at": now,
                    "user_id": user_id,
                }
            )
        return normalized

    def _product_member_authorization_for_user(
        self,
        user_id: str,
    ) -> tuple[set[str], list[dict[str, Any]]]:
        permissions: set[str] = set()
        scopes: list[dict[str, Any]] = []
        seen_scopes: set[tuple[str, str, str]] = set()
        for product_id, members in self._product_members.items():
            for member in members:
                if member.get("status") != "active" or member.get("user_id") != user_id:
                    continue
                member_role = str(member.get("member_role") or "")
                permissions.update(PRODUCT_MEMBER_ROLE_PERMISSIONS.get(member_role, set()))
                if member.get("scope_type") != "product":
                    continue
                scope_id = str(member.get("scope_id") or "*")
                if scope_id not in {"*", product_id}:
                    continue
                access_level = "read" if member_role == "viewer" else "write"
                scope_key = ("product", product_id, access_level)
                if scope_key in seen_scopes:
                    continue
                seen_scopes.add(scope_key)
                scopes.append(
                    {
                        "access_level": access_level,
                        "scope_id": product_id,
                        "scope_type": "product",
                    }
                )
        return permissions, scopes

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
        metadata = ROLE_METADATA_BY_CODE.get(role["code"], {})
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
                {resource["code"] for resource in self._menu_resources}
                if role["code"] == "admin"
                else self._role_menu_grants.get(role["code"], set())
            ),
            "scopes": deepcopy(self._role_scope_grants.get(role["code"], [])),
            **{
                field: deepcopy(
                    role.get(
                        field,
                        metadata.get(field, [] if field in ROLE_METADATA_LIST_FIELDS else ""),
                    )
                )
                for field in ROLE_METADATA_FIELDS
            },
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
        valid_codes = {menu["code"] for menu in self._menu_resources}
        unsupported = sorted(set(menu_codes) - valid_codes)
        if unsupported:
            raise ValueError("UNSUPPORTED_MENU")

    def _find_menu_resource(self, menu_code: str) -> dict[str, Any] | None:
        return next(
            (menu for menu in self._menu_resources if menu["code"] == menu_code),
            None,
        )

    def _normalize_menu_payload(
        self,
        payload: dict[str, Any],
        *,
        is_system: bool,
    ) -> dict[str, Any]:
        code = str(payload.get("code") or "").strip()
        name = str(payload.get("name") or "").strip()
        path = str(payload.get("path") or "").strip()
        menu_type = str(payload.get("menu_type") or "page").strip()
        status = str(payload.get("status") or "active").strip()
        parent_code = payload.get("parent_code")
        parent_code = str(parent_code).strip() if parent_code is not None else None
        if not code or not name:
            raise ValueError("VALIDATION_ERROR")
        if menu_type not in {"group", "hidden_page", "page"}:
            raise ValueError("UNSUPPORTED_MENU_TYPE")
        if status not in {"active", "inactive"}:
            raise ValueError("UNSUPPORTED_MENU_STATUS")
        if parent_code:
            if parent_code == code or self._find_menu_resource(parent_code) is None:
                raise ValueError("MENU_PARENT_NOT_FOUND")
        required_permissions = [
            str(permission_code).strip()
            for permission_code in (payload.get("required_permissions") or [])
            if str(permission_code).strip()
        ]
        if len(set(required_permissions)) != len(required_permissions):
            raise ValueError("VALIDATION_ERROR")
        self._ensure_permission_codes(required_permissions)
        return {
            "code": code,
            "icon": str(payload.get("icon") or "").strip(),
            "is_system": is_system,
            "menu_type": menu_type,
            "name": name,
            "parent_code": parent_code,
            "path": path,
            "required_permissions": required_permissions,
            "sort_order": int(payload.get("sort_order") or 0),
            "status": status,
        }

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

    def _record_menu_mutation(
        self,
        *,
        menu_code: str,
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
                "role_id": None,
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
                "subject_type": "menu_resource",
                "subject_id": menu_code,
                "payload": {
                    "before": deepcopy(before_payload),
                    "after": deepcopy(after_payload),
                },
                "sequence": len(self.audit_events) + 1,
                "created_at": now,
                "updated_at": now,
            }
        )

    def _record_product_members_mutation(
        self,
        *,
        product_id: str,
        before_payload: dict[str, Any],
        after_payload: dict[str, Any],
        actor_id: str,
        trace_id: str,
    ) -> None:
        del trace_id
        now = datetime.now(UTC).isoformat()
        self.audit_events.append(
            {
                "id": f"audit_event_{uuid4().hex}",
                "event_type": "product.members.updated",
                "actor_id": actor_id,
                "ai_task_id": None,
                "subject_type": "product",
                "subject_id": product_id,
                "payload": {
                    "after": deepcopy(after_payload),
                    "before": deepcopy(before_payload),
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
        member_permissions, member_scopes = self._product_member_authorization_for_user(
            str(user["id"])
        )
        permissions.update(member_permissions)
        scopes.extend(member_scopes)
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
                    SELECT code, name, path, parent_code, menu_type, icon, sort_order,
                           required_permissions, is_system, status
                    FROM menu_resources
                    ORDER BY sort_order, code
                    """
                )
                rows = cursor.fetchall()
        return [self._postgres_menu_resource_from_row(row) for row in rows]

    def count_menu_resources(
        self,
        *,
        menu: str | None,
        menu_type: str | None,
        parent: str | None,
        path: str | None,
        permission: str | None,
        status: str | None,
    ) -> int:
        where_sql, params = self._menu_resource_where(
            menu=menu,
            menu_type=menu_type,
            parent=parent,
            path=path,
            permission=permission,
            status=status,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT count(*)
                    FROM menu_resources m
                    LEFT JOIN menu_resources parent ON parent.code = m.parent_code
                    WHERE {where_sql}
                    """,
                    params,
                )
                row = cursor.fetchone()
        return int(row[0] if row else 0)

    def list_menu_resources_page(
        self,
        *,
        limit: int,
        menu: str | None,
        menu_type: str | None,
        offset: int,
        parent: str | None,
        path: str | None,
        permission: str | None,
        sort_by: str,
        sort_order: str,
        status: str | None,
    ) -> list[dict[str, Any]]:
        where_sql, params = self._menu_resource_where(
            menu=menu,
            menu_type=menu_type,
            parent=parent,
            path=path,
            permission=permission,
            status=status,
        )
        sort_expression = MENU_RESOURCE_SORT_COLUMNS.get(
            sort_by,
            MENU_RESOURCE_SORT_COLUMNS["sort_order"],
        )
        direction = "ASC" if sort_order == "asc" else "DESC"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT m.code, m.name, m.path, m.parent_code, m.menu_type, m.icon,
                           m.sort_order, m.required_permissions, m.is_system, m.status
                    FROM menu_resources m
                    LEFT JOIN menu_resources parent ON parent.code = m.parent_code
                    WHERE {where_sql}
                    ORDER BY {sort_expression} {direction}, m.code ASC
                    LIMIT %s OFFSET %s
                    """,
                    [*params, limit, offset],
                )
                rows = cursor.fetchall()
        return [self._postgres_menu_resource_from_row(row) for row in rows]

    def _menu_resource_where(
        self,
        *,
        menu: str | None,
        menu_type: str | None,
        parent: str | None,
        path: str | None,
        permission: str | None,
        status: str | None,
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = ["TRUE"]
        params: list[Any] = []
        if menu:
            pattern = f"%{menu}%"
            clauses.append("(m.code ILIKE %s OR m.name ILIKE %s)")
            params.extend([pattern, pattern])
        if parent:
            pattern = f"%{parent}%"
            clauses.append("(m.parent_code ILIKE %s OR parent.name ILIKE %s)")
            params.extend([pattern, pattern])
        if path:
            clauses.append("m.path ILIKE %s")
            params.append(f"%{path}%")
        if permission:
            clauses.append(
                """
                EXISTS (
                  SELECT 1
                  FROM jsonb_array_elements_text(
                    COALESCE(m.required_permissions, '[]'::jsonb)
                  ) AS permission_code(value)
                  WHERE permission_code.value ILIKE %s
                )
                """
            )
            params.append(f"%{permission}%")
        if menu_type:
            clauses.append("m.menu_type = %s")
            params.append(menu_type)
        if status:
            clauses.append("m.status = %s")
            params.append(status)
        return " AND ".join(clauses), params

    def create_menu_resource(
        self,
        payload: dict[str, Any],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    menu = self._postgres_normalize_menu_payload(cursor, payload, is_system=False)
                    cursor.execute(
                        """
                        INSERT INTO menu_resources (
                          code, name, path, parent_code, menu_type, icon, sort_order,
                          required_permissions, is_system, status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, false, %s)
                        """,
                        (
                            menu["code"],
                            menu["name"],
                            menu["path"],
                            menu["parent_code"],
                            menu["menu_type"],
                            menu["icon"],
                            menu["sort_order"],
                            json.dumps(menu["required_permissions"], ensure_ascii=False),
                            menu["status"],
                        ),
                    )
                    after = self._postgres_menu_resource_from_row(
                        self._postgres_menu_resource_row(cursor, menu["code"])
                    )
                    self._insert_menu_mutation(
                        cursor,
                        menu_code=menu["code"],
                        event_type="menu.created",
                        audit_event_type="system.menu.created",
                        before_payload={},
                        after_payload=after,
                        actor_id=actor_id,
                        trace_id=trace_id,
                    )
                    return after
        except Exception as exc:
            if getattr(exc, "sqlstate", "") == "23505":
                raise ValueError("MENU_CODE_EXISTS") from exc
            raise

    def update_menu_resource(
        self,
        menu_code: str,
        updates: dict[str, Any],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                row = self._postgres_menu_resource_row(cursor, menu_code)
                if row is None:
                    return None
                before = self._postgres_menu_resource_from_row(row)
                merged = {**before, **updates}
                menu = self._postgres_normalize_menu_payload(
                    cursor,
                    merged,
                    is_system=before["is_system"],
                )
                cursor.execute(
                    """
                    UPDATE menu_resources
                    SET name = %s,
                        path = %s,
                        parent_code = %s,
                        menu_type = %s,
                        icon = %s,
                        sort_order = %s,
                        required_permissions = %s::jsonb,
                        status = %s,
                        updated_at = now()
                    WHERE code = %s
                    """,
                    (
                        menu["name"],
                        menu["path"],
                        menu["parent_code"],
                        menu["menu_type"],
                        menu["icon"],
                        menu["sort_order"],
                        json.dumps(menu["required_permissions"], ensure_ascii=False),
                        menu["status"],
                        menu_code,
                    ),
                )
                after = self._postgres_menu_resource_from_row(
                    self._postgres_menu_resource_row(cursor, menu_code)
                )
                self._insert_menu_mutation(
                    cursor,
                    menu_code=menu_code,
                    event_type="menu.updated",
                    audit_event_type="system.menu.updated",
                    before_payload=before,
                    after_payload=after,
                    actor_id=actor_id,
                    trace_id=trace_id,
                )
                return after

    def set_menu_status(
        self,
        menu_code: str,
        status: str,
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any] | None:
        return self.update_menu_resource(
            menu_code,
            {"status": status},
            actor_id=actor_id,
            trace_id=trace_id,
        )

    def delete_menu_resource(
        self,
        menu_code: str,
        *,
        actor_id: str,
        trace_id: str,
    ) -> bool | None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                row = self._postgres_menu_resource_row(cursor, menu_code)
                if row is None:
                    return None
                before = self._postgres_menu_resource_from_row(row)
                if before["is_system"]:
                    raise ValueError("SYSTEM_MENU_PROTECTED")
                cursor.execute(
                    "SELECT 1 FROM menu_resources WHERE parent_code = %s LIMIT 1",
                    (menu_code,),
                )
                if cursor.fetchone() is not None:
                    raise ValueError("MENU_HAS_CHILDREN")
                cursor.execute("DELETE FROM menu_resources WHERE code = %s", (menu_code,))
                self._insert_menu_mutation(
                    cursor,
                    menu_code=menu_code,
                    event_type="menu.deleted",
                    audit_event_type="system.menu.deleted",
                    before_payload=before,
                    after_payload={},
                    actor_id=actor_id,
                    trace_id=trace_id,
                )
                return True

    def reorder_menu_resources(
        self,
        items: list[dict[str, Any]],
        *,
        actor_id: str,
        trace_id: str,
    ) -> list[dict[str, Any]]:
        updated: list[dict[str, Any]] = []
        with self._connect() as connection:
            with connection.cursor() as cursor:
                for item in items:
                    menu_code = str(item["code"])
                    row = self._postgres_menu_resource_row(cursor, menu_code)
                    if row is None:
                        raise ValueError("UNSUPPORTED_MENU")
                    before = self._postgres_menu_resource_from_row(row)
                    cursor.execute(
                        """
                        UPDATE menu_resources
                        SET sort_order = %s, updated_at = now()
                        WHERE code = %s
                        """,
                        (int(item["sort_order"]), menu_code),
                    )
                    after = self._postgres_menu_resource_from_row(
                        self._postgres_menu_resource_row(cursor, menu_code)
                    )
                    self._insert_menu_mutation(
                        cursor,
                        menu_code=menu_code,
                        event_type="menu.reordered",
                        audit_event_type="system.menu.reordered",
                        before_payload=before,
                        after_payload=after,
                        actor_id=actor_id,
                        trace_id=trace_id,
                    )
                    updated.append(after)
        return updated

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

    def count_role_summaries(
        self,
        *,
        business_role: str | None,
        category: str | None,
        menu_scope: str | None,
        permission: str | None,
        role: str | None,
        status: str | None,
    ) -> int:
        where_sql, params = self._role_summary_where(
            business_role=business_role,
            category=category,
            menu_scope=menu_scope,
            permission=permission,
            role=role,
            status=status,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT count(*) FROM roles r WHERE {where_sql}",
                    params,
                )
                row = cursor.fetchone()
        return int(row[0] if row else 0)

    def list_role_summaries_page(
        self,
        *,
        business_role: str | None,
        category: str | None,
        limit: int,
        menu_scope: str | None,
        offset: int,
        permission: str | None,
        role: str | None,
        sort_by: str,
        sort_order: str,
        status: str | None,
    ) -> list[dict[str, Any]]:
        where_sql, params = self._role_summary_where(
            business_role=business_role,
            category=category,
            menu_scope=menu_scope,
            permission=permission,
            role=role,
            status=status,
        )
        sort_expression = ROLE_SUMMARY_SORT_COLUMNS.get(
            sort_by,
            ROLE_SUMMARY_SORT_COLUMNS["sort_order"],
        )
        direction = "ASC" if sort_order == "asc" else "DESC"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT r.id, r.code, r.name, r.description, r.category, r.is_system,
                           r.is_assignable, r.status, r.sort_order
                    FROM roles r
                    WHERE {where_sql}
                    ORDER BY {sort_expression} {direction}, r.code ASC
                    LIMIT %s OFFSET %s
                    """,
                    [*params, limit, offset],
                )
                rows = cursor.fetchall()
                return [self._postgres_role_detail_from_row(row, cursor=cursor) for row in rows]

    def _role_summary_where(
        self,
        *,
        business_role: str | None,
        category: str | None,
        menu_scope: str | None,
        permission: str | None,
        role: str | None,
        status: str | None,
    ) -> tuple[str, list[Any]]:
        clauses: list[str] = ["TRUE"]
        params: list[Any] = []
        if category:
            clauses.append("r.category = %s")
            params.append(category)
        if status:
            clauses.append("r.status = %s")
            params.append(status)
        if role:
            pattern = f"%{role}%"
            clauses.append("(r.code ILIKE %s OR r.name ILIKE %s OR r.description ILIKE %s)")
            params.extend([pattern, pattern, pattern])
        if business_role:
            business_role_codes = self._role_metadata_matching_codes(
                "business_roles",
                business_role,
            )
            self._append_role_code_filter(clauses, params, business_role_codes)
        if menu_scope:
            pattern = f"%{menu_scope}%"
            menu_scope_codes = self._role_metadata_matching_codes("menu_scope", menu_scope)
            menu_clauses = [
                (
                    "EXISTS (SELECT 1 FROM role_menu_grants rmg "
                    "WHERE rmg.role_id = r.id AND rmg.menu_code ILIKE %s)"
                ),
                (
                    "r.code = 'admin' AND EXISTS (SELECT 1 FROM menu_resources mr "
                    "WHERE mr.code ILIKE %s)"
                ),
            ]
            menu_params: list[Any] = [pattern, pattern]
            if menu_scope_codes:
                placeholders = ", ".join(["%s"] * len(menu_scope_codes))
                menu_clauses.append(f"r.code IN ({placeholders})")
                menu_params.extend(menu_scope_codes)
            clauses.append(f"({' OR '.join(menu_clauses)})")
            params.extend(menu_params)
        if permission:
            pattern = f"%{permission}%"
            clauses.append(
                "("
                "EXISTS (SELECT 1 FROM role_permissions rp "
                "WHERE rp.role_id = r.id AND rp.permission_code ILIKE %s) "
                "OR (r.code = 'admin' AND EXISTS (SELECT 1 FROM permissions p "
                "WHERE p.status = 'active' AND p.code ILIKE %s))"
                ")"
            )
            params.extend([pattern, pattern])
        return " AND ".join(clauses), params

    def _role_metadata_matching_codes(self, field: str, keyword: str) -> list[str]:
        normalized = str(keyword or "").strip().lower()
        if not normalized:
            return []
        codes: list[str] = []
        for code, metadata in ROLE_METADATA_BY_CODE.items():
            value = metadata.get(field)
            values = value if isinstance(value, list) else [value]
            haystack = " ".join(str(item or "").lower() for item in values)
            if normalized in haystack:
                codes.append(code)
        return sorted(codes)

    def _append_role_code_filter(
        self,
        clauses: list[str],
        params: list[Any],
        role_codes: list[str],
    ) -> None:
        if not role_codes:
            clauses.append("FALSE")
            return
        placeholders = ", ".join(["%s"] * len(role_codes))
        clauses.append(f"r.code IN ({placeholders})")
        params.extend(role_codes)

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

    def delete_user_grants(
        self,
        user_id: str,
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        del actor_id, trace_id
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM user_roles WHERE user_id = %s", (user_id,))
                removed_roles = cursor.rowcount
                cursor.execute(
                    """
                    UPDATE user_scope_grants
                    SET status = 'revoked', updated_at = now()
                    WHERE user_id = %s AND status = 'active'
                    """,
                    (user_id,),
                )
                removed_scopes = cursor.rowcount
                cursor.execute(
                    """
                    UPDATE product_members
                    SET status = 'inactive', updated_at = now()
                    WHERE user_id = %s AND status = 'active'
                    """,
                    (user_id,),
                )
                removed_product_members = cursor.rowcount
        return {
            "removed_product_members": removed_product_members,
            "removed_roles": removed_roles,
            "removed_scopes": removed_scopes,
            "user_id": user_id,
        }

    def effective_permissions_for_user(self, user: dict[str, Any]) -> dict[str, Any]:
        snapshot = self.snapshot_for_user(user)
        return {
            "user_id": str(user["id"]),
            "role_codes": snapshot.roles,
            "permission_codes": sorted(snapshot.permissions),
            "scopes": snapshot.scopes,
            "menu_codes": sorted(menu["code"] for menu in snapshot.menus),
        }

    def list_product_members(
        self,
        product_id: str,
        *,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                return self._postgres_list_product_members(
                    cursor,
                    product_id=product_id,
                    active_only=active_only,
                )

    def set_product_members(
        self,
        product_id: str,
        members: list[dict[str, Any]],
        *,
        actor_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        normalized_members = self._normalize_product_members(product_id, members)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                before = self._postgres_list_product_members(
                    cursor,
                    product_id=product_id,
                    active_only=False,
                )
                cursor.execute(
                    """
                    UPDATE product_members
                    SET status = 'inactive', updated_at = now()
                    WHERE product_id = %s AND status = 'active'
                    """,
                    (product_id,),
                )
                for member in normalized_members:
                    cursor.execute(
                        """
                        INSERT INTO product_members (
                          product_id, user_id, member_role, scope_type, scope_id,
                          status, granted_by
                        )
                        VALUES (%s, %s, %s, %s, %s, 'active', %s)
                        ON CONFLICT (product_id, user_id, member_role, scope_type, scope_id)
                        DO UPDATE SET
                          status = 'active',
                          granted_by = EXCLUDED.granted_by,
                          updated_at = now()
                        """,
                        (
                            member["product_id"],
                            member["user_id"],
                            member["member_role"],
                            member["scope_type"],
                            member["scope_id"],
                            actor_id,
                        ),
                    )
                after = self._postgres_list_product_members(
                    cursor,
                    product_id=product_id,
                    active_only=False,
                )
                self._insert_product_members_audit(
                    cursor,
                    product_id=product_id,
                    before_payload={"items": before},
                    after_payload={"items": after},
                    actor_id=actor_id,
                    trace_id=trace_id,
                )
        return {
            "items": self.list_product_members(product_id, active_only=True),
            "product_id": product_id,
        }

    def _postgres_list_product_members(
        self,
        cursor,
        *,
        product_id: str,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        where_sql = "product_id = %s"
        params: list[Any] = [product_id]
        if active_only:
            where_sql += " AND status = 'active'"
        cursor.execute(
            f"""
            SELECT product_id, user_id, member_role, scope_type, scope_id,
                   status, granted_by, created_at, updated_at
            FROM product_members
            WHERE {where_sql}
            ORDER BY member_role, user_id, scope_type, scope_id
            """,
            tuple(params),
        )
        return [self._postgres_product_member_from_row(row) for row in cursor.fetchall()]

    def _product_member_authorization_for_user(
        self,
        user_id: str,
    ) -> tuple[set[str], list[dict[str, Any]]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT product_id, member_role, scope_type, scope_id
                    FROM product_members
                    WHERE user_id = %s AND status = 'active'
                    ORDER BY product_id, member_role, scope_type, scope_id
                    """,
                    (user_id,),
                )
                rows = cursor.fetchall()
        permissions: set[str] = set()
        scopes: list[dict[str, Any]] = []
        seen_scopes: set[tuple[str, str, str]] = set()
        for product_id, member_role, scope_type, scope_id in rows:
            member_role = str(member_role)
            permissions.update(PRODUCT_MEMBER_ROLE_PERMISSIONS.get(member_role, set()))
            if scope_type != "product" or str(scope_id) not in {"*", str(product_id)}:
                continue
            access_level = "read" if member_role == "viewer" else "write"
            scope_key = ("product", str(product_id), access_level)
            if scope_key in seen_scopes:
                continue
            seen_scopes.add(scope_key)
            scopes.append(
                {
                    "access_level": access_level,
                    "scope_id": str(product_id),
                    "scope_type": "product",
                }
            )
        return permissions, scopes

    def _postgres_product_member_from_row(self, row: tuple[Any, ...]) -> dict[str, Any]:
        (
            product_id,
            user_id,
            member_role,
            scope_type,
            scope_id,
            status,
            granted_by,
            created_at,
            updated_at,
        ) = row
        return {
            "created_at": created_at.isoformat() if created_at else None,
            "granted_by": granted_by,
            "member_role": member_role,
            "product_id": product_id,
            "scope_id": scope_id,
            "scope_type": scope_type,
            "status": status,
            "updated_at": updated_at.isoformat() if updated_at else None,
            "user_id": user_id,
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
        metadata = ROLE_METADATA_BY_CODE.get(code, {})
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
            **{
                field: deepcopy(
                    metadata.get(field, [] if field in ROLE_METADATA_LIST_FIELDS else "")
                )
                for field in ROLE_METADATA_FIELDS
            },
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

    def _postgres_menu_resource_row(self, cursor, menu_code: str):
        cursor.execute(
            """
            SELECT code, name, path, parent_code, menu_type, icon, sort_order,
                   required_permissions, is_system, status
            FROM menu_resources
            WHERE code = %s
            """,
            (menu_code,),
        )
        return cursor.fetchone()

    def _postgres_menu_resource_from_row(self, row) -> dict[str, Any]:
        (
            code,
            name,
            path,
            parent_code,
            menu_type,
            icon,
            sort_order,
            required_permissions,
            is_system,
            status,
        ) = row
        return {
            "code": code,
            "icon": icon,
            "is_system": bool(is_system),
            "menu_type": menu_type,
            "name": name,
            "parent_code": parent_code,
            "path": path,
            "required_permissions": list(required_permissions or []),
            "sort_order": int(sort_order or 0),
            "status": status,
        }

    def _postgres_normalize_menu_payload(
        self,
        cursor,
        payload: dict[str, Any],
        *,
        is_system: bool,
    ) -> dict[str, Any]:
        code = str(payload.get("code") or "").strip()
        name = str(payload.get("name") or "").strip()
        path = str(payload.get("path") or "").strip()
        menu_type = str(payload.get("menu_type") or "page").strip()
        status = str(payload.get("status") or "active").strip()
        parent_code = payload.get("parent_code")
        parent_code = str(parent_code).strip() if parent_code is not None else None
        if not code or not name:
            raise ValueError("VALIDATION_ERROR")
        if menu_type not in {"group", "hidden_page", "page"}:
            raise ValueError("UNSUPPORTED_MENU_TYPE")
        if status not in {"active", "inactive"}:
            raise ValueError("UNSUPPORTED_MENU_STATUS")
        if parent_code:
            if parent_code == code:
                raise ValueError("MENU_PARENT_NOT_FOUND")
            cursor.execute("SELECT 1 FROM menu_resources WHERE code = %s", (parent_code,))
            if cursor.fetchone() is None:
                raise ValueError("MENU_PARENT_NOT_FOUND")
        required_permissions = [
            str(permission_code).strip()
            for permission_code in (payload.get("required_permissions") or [])
            if str(permission_code).strip()
        ]
        if len(set(required_permissions)) != len(required_permissions):
            raise ValueError("VALIDATION_ERROR")
        self._postgres_ensure_permission_codes(cursor, required_permissions)
        return {
            "code": code,
            "icon": str(payload.get("icon") or "").strip(),
            "is_system": is_system,
            "menu_type": menu_type,
            "name": name,
            "parent_code": parent_code,
            "path": path,
            "required_permissions": required_permissions,
            "sort_order": int(payload.get("sort_order") or 0),
            "status": status,
        }

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

    def _insert_menu_mutation(
        self,
        cursor,
        *,
        menu_code: str,
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
            VALUES (%s, NULL, %s, %s::jsonb, %s::jsonb, %s, %s)
            """,
            (
                f"role_change_{uuid4().hex}",
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
            VALUES (%s, %s, %s, NULL, 'menu_resource', %s, %s::jsonb, 0)
            """,
            (
                f"audit_event_{uuid4().hex}",
                audit_event_type,
                actor_id,
                menu_code,
                json.dumps(
                    {"before": before_payload, "after": after_payload},
                    ensure_ascii=False,
                ),
            ),
        )

    def _insert_product_members_audit(
        self,
        cursor,
        *,
        product_id: str,
        before_payload: dict[str, Any],
        after_payload: dict[str, Any],
        actor_id: str,
        trace_id: str,
    ) -> None:
        del trace_id
        cursor.execute(
            """
            INSERT INTO audit_events (
              id, event_type, actor_id, ai_task_id, subject_type, subject_id, payload, sequence
            )
            VALUES (%s, 'product.members.updated', %s, NULL, 'product', %s, %s::jsonb, 0)
            """,
            (
                f"audit_event_{uuid4().hex}",
                actor_id,
                product_id,
                json.dumps(
                    {"after": after_payload, "before": before_payload},
                    ensure_ascii=False,
                ),
            ),
        )
