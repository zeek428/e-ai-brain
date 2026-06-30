from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.scheduled_job_store import read_memory_dict


def with_action_permission_preview(
    preview: dict[str, Any],
    *,
    action: str,
    user: dict[str, Any] | None,
) -> dict[str, Any]:
    append_action_permission_validation(preview["validation"], action=action, user=user)
    finalize_validation(preview["validation"])
    return preview


def append_action_permission_validation(
    validation: dict[str, Any],
    *,
    action: str,
    user: dict[str, Any] | None,
) -> None:
    if user is None:
        return
    if action in {"create_ai_agent", "create_ai_skill"}:
        if not user_has_permission(user, "system.ai_capabilities.manage"):
            add_issue(
                validation,
                "permission",
                "error",
                "system.ai_capabilities.manage is required to confirm this draft",
            )
        return
    if action == "create_scheduled_job":
        if not user_has_permission(user, "system.scheduled_jobs.manage"):
            add_issue(
                validation,
                "permission",
                "error",
                "system.scheduled_jobs.manage is required to confirm this draft",
            )
        return
    if action in {"create_plugin_action", "create_plugin_connection"}:
        if not user_has_permission(user, "system.plugins.manage"):
            add_issue(
                validation,
                "permission",
                "error",
                "system.plugins.manage is required to confirm this draft",
            )
        return
    if action == "create_rd_task":
        roles = set(user.get("roles") or [])
        if "admin" not in roles and not roles.intersection({"product_owner", "rd_owner"}):
            add_issue(
                validation,
                "permission",
                "error",
                "product_owner or rd_owner role is required to confirm this draft",
            )


def user_has_permission(user: dict[str, Any], permission: str) -> bool:
    roles = set(user.get("roles") or [])
    permissions = set(user.get("permissions") or [])
    return "admin" in roles or "system.admin" in permissions or permission in permissions


def generic_create_draft_preview(
    draft: dict[str, Any],
    *,
    diff_fields: list[tuple[str, str]],
    required_fields: list[str],
    resource_type: str,
    source_payload: dict[str, Any] | None = None,
    source_resource: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = draft.get("payload") or {}
    validation = {"issues": [], "status": "passed"}
    for field in required_fields:
        if nested_value(payload, field) in (None, "", []):
            add_issue(validation, field, "error", f"{field} is required")
    diffs = []
    for field, label in diff_fields:
        proposed = nested_value(payload, field)
        if proposed in (None, "", []):
            continue
        current = nested_value(source_payload, field) if source_payload else None
        if source_payload is not None and current == proposed:
            continue
        change_type = (
            "update" if source_payload is not None and current not in (None, "", []) else "create"
        )
        diffs.append(
            {
                "change_type": change_type,
                "current": deepcopy(current),
                "field": field,
                "label": label,
                "proposed": deepcopy(proposed),
            }
        )
    target = {
        "operation": "create",
        "resource_id": None,
        "resource_type": resource_type,
    }
    if source_resource:
        target["source_resource"] = preview_source_resource(source_resource)
    preview = {
        "diffs": diffs,
        "target": target,
        "validation": validation,
    }
    finalize_validation(validation)
    return preview


def draft_source_resource(
    draft: dict[str, Any],
    *,
    expected_type: str,
) -> dict[str, Any] | None:
    metadata_json = (
        draft.get("metadata_json") if isinstance(draft.get("metadata_json"), dict) else {}
    )
    source_resource = metadata_json.get("source_resource")
    if not isinstance(source_resource, dict):
        return None
    if str(source_resource.get("type") or "") != expected_type:
        return None
    if not str(source_resource.get("id") or "").strip():
        return None
    return source_resource


def draft_source_plugin_action(
    current_store: Any,
    *,
    source_resource: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not source_resource:
        return None
    action_id = str(source_resource.get("id") or "").strip()
    return read_memory_dict(current_store, "plugin_actions").get(action_id)


def preview_source_resource(source_resource: dict[str, Any]) -> dict[str, Any]:
    return {
        "resource_id": str(source_resource.get("id") or ""),
        "resource_type": str(source_resource.get("type") or ""),
        "title": str(source_resource.get("title") or source_resource.get("id") or ""),
    }


def validate_collection_ref(
    collection: dict[str, dict[str, Any]],
    item_id: str,
    *,
    field: str,
    label: str,
    validation: dict[str, Any],
) -> None:
    item = collection.get(item_id)
    if item is None:
        add_issue(validation, field, "error", f"{label} not found: {item_id}")
        return
    if item.get("status") and item.get("status") != "active":
        add_issue(validation, field, "error", f"{label} is inactive: {item_id}")


def validate_plugin_connection_ref(
    current_store: Any,
    item_id: str,
    *,
    field: str,
    validation: dict[str, Any],
) -> None:
    item = read_memory_dict(current_store, "plugin_connections").get(item_id)
    if item is None:
        add_issue(validation, field, "error", f"Plugin connection not found: {item_id}")
        return
    if item.get("status") and item.get("status") != "active":
        add_issue(validation, field, "error", f"Plugin connection is inactive: {item_id}")
        return
    last_test_summary = item.get("last_test_summary")
    if not isinstance(last_test_summary, dict):
        return
    if str(last_test_summary.get("status") or "").lower() not in {"failed", "error"}:
        return
    failure_message = (
        str(last_test_summary.get("error_message") or "").strip()
        or str(last_test_summary.get("error_code") or "").strip()
        or "unknown error"
    )
    add_issue(
        validation,
        field,
        "error",
        f"Plugin connection last test failed: {failure_message}",
        repair_action={
            "action": "open_plugin_connection_test",
            "field": field,
            "label": "打开连接测试",
            "resource_id": item_id,
            "resource_type": "plugin_connection",
        },
    )


def validate_enum(
    validation: dict[str, Any],
    field: str,
    value: Any,
    allowed_values: set[str],
) -> None:
    if value not in allowed_values:
        add_issue(validation, field, "error", f"Unsupported {field}")


def add_issue(
    validation: dict[str, Any],
    field: str,
    severity: str,
    message: str,
    *,
    repair_action: dict[str, Any] | None = None,
) -> None:
    issue = {
        "field": field,
        "message": message,
        "severity": severity,
    }
    resolved_repair_action = repair_action or default_repair_action(field)
    if resolved_repair_action is not None:
        issue["repair_action"] = resolved_repair_action
    validation.setdefault("issues", []).append(issue)


def default_repair_action(field: str) -> dict[str, Any] | None:
    if field in {"cron_expression", "interval_seconds"}:
        return {
            "action": "edit_field",
            "field": field,
            "label": "修正 Cron 表达式" if field == "cron_expression" else "修正间隔时间",
        }
    if field in {"plugin_action_id", "plugin_action_ids"}:
        return {
            "action": "generate_plugin_action_draft",
            "field": field,
            "label": "生成结果动作草案",
        }
    if field in {"plugin_connection_id", "plugin_connection_ids", "connection_id"}:
        return {
            "action": "generate_connection_draft",
            "field": field,
            "label": "生成连接草案",
        }
    if field == "model_gateway_config_id":
        return {
            "action": "select_model_gateway",
            "field": field,
            "label": "选择模型网关",
        }
    if field == "agent_id":
        return {
            "action": "generate_ai_agent_draft",
            "field": field,
            "label": "生成AI角色草案",
        }
    if field == "skill_ids":
        return {
            "action": "generate_ai_skill_draft",
            "field": field,
            "label": "生成Skill草案",
        }
    if field == "permission":
        return {
            "action": "request_permission",
            "field": field,
            "label": "申请权限",
        }
    return None


def finalize_validation(validation: dict[str, Any]) -> None:
    issues = validation.get("issues") or []
    if any(issue.get("severity") == "error" for issue in issues):
        validation["status"] = "blocked"
    elif issues:
        validation["status"] = "warning"
    else:
        validation["status"] = "passed"


def nested_value(payload: dict[str, Any] | None, field: str) -> Any:
    value: Any = payload or {}
    for part in field.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def string_ids(value: Any) -> list[str]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    result = []
    for item in values:
        item_id = str(item).strip()
        if item_id:
            result.append(item_id)
    return result
