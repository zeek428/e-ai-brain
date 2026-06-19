from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from app.api.deps import api_error

STANDARD_ASSISTANT_ROLE_QUICK_TASK_GROUPS = [
    {
        "enabled": True,
        "key": "product",
        "label": "产品快捷任务",
        "roles": ["product_owner"],
        "sort_order": 10,
        "tasks": [
            {
                "analytics_key": "product.requirement_progress",
                "enabled": True,
                "key": "requirement_progress",
                "label": "需求进展",
                "permissions": [],
                "prompt": "请按产品视角总结当前需求进展、阻塞和下一步推进建议。",
                "sort_order": 10,
                "target_draft_type": None,
            },
            {
                "analytics_key": "product.feedback_insights",
                "enabled": True,
                "key": "feedback_insights",
                "label": "反馈洞察",
                "permissions": ["system.scheduled_jobs.manage"],
                "prompt": (
                    "请帮我生成每周用户反馈洞察定时作业草案，"
                    "并说明数据来源、AI处理、结果动作和调度策略。"
                ),
                "sort_order": 20,
                "target_draft_type": "create_scheduled_job",
            },
            {
                "analytics_key": "product.version_risk",
                "enabled": True,
                "key": "version_risk",
                "label": "版本风险",
                "permissions": [],
                "prompt": (
                    "请生成发布风险分析草案，"
                    "基于需求、缺陷、发布记录和用户反馈评估当前版本风险。"
                ),
                "sort_order": 30,
                "target_draft_type": "create_analysis_draft",
            },
        ],
    },
    {
        "enabled": True,
        "key": "engineering",
        "label": "研发快捷任务",
        "roles": ["rd_owner"],
        "sort_order": 20,
        "tasks": [
            {
                "analytics_key": "engineering.task_blockers",
                "enabled": True,
                "key": "task_blockers",
                "label": "任务阻塞",
                "permissions": [],
                "prompt": "请列出当前研发任务阻塞、待确认项和建议处理顺序。",
                "sort_order": 10,
                "target_draft_type": None,
            },
            {
                "analytics_key": "engineering.code_inspection",
                "enabled": True,
                "key": "code_inspection",
                "label": "代码巡检",
                "permissions": ["system.scheduled_jobs.manage"],
                "prompt": (
                    "请帮我生成或检查代码巡检任务草案，"
                    "并说明数据连接、AI处理和结果动作依赖。"
                ),
                "sort_order": 20,
                "target_draft_type": "create_scheduled_job",
            },
            {
                "analytics_key": "engineering.defect_fix",
                "enabled": True,
                "key": "defect_fix",
                "label": "缺陷修复",
                "permissions": [],
                "prompt": "请按严重度梳理待修复缺陷，给出修复优先级和关联需求/任务。",
                "sort_order": 30,
                "target_draft_type": None,
            },
        ],
    },
    {
        "enabled": True,
        "key": "testing",
        "label": "测试快捷任务",
        "roles": ["reviewer", "test_owner", "tester", "release_owner"],
        "sort_order": 30,
        "tasks": [
            {
                "analytics_key": "testing.test_defects",
                "enabled": True,
                "key": "test_defects",
                "label": "测试缺陷",
                "permissions": [],
                "prompt": "请汇总当前测试缺陷、复现状态、阻塞发布的问题和建议责任归属。",
                "sort_order": 10,
                "target_draft_type": None,
            },
            {
                "analytics_key": "testing.automated_tests",
                "enabled": True,
                "key": "automated_tests",
                "label": "自动化测试",
                "permissions": [],
                "prompt": "请检查自动化测试相关任务、失败原因和可生成的测试草案。",
                "sort_order": 20,
                "target_draft_type": "create_rd_task",
            },
            {
                "analytics_key": "testing.release_risk",
                "enabled": True,
                "key": "release_risk",
                "label": "发布风险",
                "permissions": [],
                "prompt": (
                    "请生成发布风险分析草案，"
                    "基于测试结果、未关闭缺陷和发布记录评估当前发布风险。"
                ),
                "sort_order": 30,
                "target_draft_type": "create_analysis_draft",
            },
        ],
    },
    {
        "enabled": True,
        "key": "knowledge",
        "label": "知识快捷任务",
        "roles": ["knowledge_owner"],
        "sort_order": 40,
        "tasks": [
            {
                "analytics_key": "knowledge.knowledge_base_inspection",
                "enabled": True,
                "key": "knowledge_base_inspection",
                "label": "知识库巡检",
                "permissions": [],
                "prompt": (
                    "请生成知识库巡检草案，"
                    "检查索引失败、权限异常、过期知识和待处理知识沉淀。"
                ),
                "sort_order": 10,
                "target_draft_type": "create_analysis_draft",
            },
            {
                "analytics_key": "knowledge.knowledge_deposits",
                "enabled": True,
                "key": "knowledge_deposits",
                "label": "知识沉淀",
                "permissions": [],
                "prompt": "请汇总待处理知识沉淀候选，按来源任务、价值和风险给出处理优先级。",
                "sort_order": 20,
                "target_draft_type": None,
            },
            {
                "analytics_key": "knowledge.knowledge_permissions",
                "enabled": True,
                "key": "knowledge_permissions",
                "label": "知识权限",
                "permissions": [],
                "prompt": "请检查知识空间、目录和文档的权限风险，指出需要调整或复核的对象。",
                "sort_order": 30,
                "target_draft_type": None,
            },
        ],
    },
    {
        "enabled": True,
        "key": "admin",
        "label": "管理员快捷任务",
        "roles": ["admin"],
        "sort_order": 50,
        "tasks": [
            {
                "analytics_key": "admin.plugin_connections",
                "enabled": True,
                "key": "plugin_connections",
                "label": "插件连接",
                "permissions": ["system.plugins.manage"],
                "prompt": "请检查插件连接配置状态，指出失败连接和可生成的连接草案。",
                "sort_order": 10,
                "target_draft_type": "create_plugin_connection",
            },
            {
                "analytics_key": "admin.ai_capabilities",
                "enabled": True,
                "key": "ai_capabilities",
                "label": "AI能力",
                "permissions": ["system.ai_capabilities.manage"],
                "prompt": "我要新增 AI能力配置",
                "sort_order": 20,
                "target_draft_type": "create_ai_skill",
            },
            {
                "analytics_key": "admin.scheduled_jobs",
                "enabled": True,
                "key": "scheduled_jobs",
                "label": "定时作业",
                "permissions": ["system.scheduled_jobs.manage"],
                "prompt": "请汇总定时作业配置、运行健康和需要补齐的依赖。",
                "sort_order": 30,
                "target_draft_type": "create_scheduled_job",
            },
            {
                "analytics_key": "admin.run_failures",
                "enabled": True,
                "key": "run_failures",
                "label": "运行失败",
                "permissions": ["system.scheduled_jobs.run"],
                "prompt": (
                    "请诊断最近失败的定时作业运行，"
                    "按数据连接、AI处理、结果动作给出原因和修复建议。"
                ),
                "sort_order": 40,
                "target_draft_type": "repair_scheduled_job_run",
            },
        ],
    },
]


def list_assistant_role_quick_task_configs_response(
    *,
    current_store: Any | None = None,
) -> dict[str, Any]:
    items = [
        _public_role_quick_task_config(row)
        for row in _role_quick_task_config_rows(current_store)
    ]
    return {"items": items, "total": len(items)}


def create_assistant_role_quick_task_config_response(
    *,
    current_store: Any,
    payload: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    now = _now_iso()
    config_id = str(payload.get("id") or current_store.new_id("assistant_role_quick_task"))
    if _get_role_quick_task_config(current_store, config_id=config_id) is not None:
        raise api_error(409, "ASSISTANT_ROLE_QUICK_TASK_EXISTS", "Role quick task config exists")
    record = _normalized_role_quick_task_config(
        {
            **payload,
            "created_at": now,
            "created_by": user["id"],
            "id": config_id,
            "updated_at": now,
            "updated_by": user["id"],
        }
    )
    _ensure_role_quick_task_scope_unique(current_store, record)
    audit_event = current_store.audit(
        event_type="assistant_role_quick_task.created",
        actor_id=user["id"],
        subject_type="assistant_role_quick_task",
        subject_id=config_id,
        payload=_role_quick_task_audit_payload(record, changed_fields=sorted(record.keys())),
    )
    _save_role_quick_task_config(current_store, record, audit_event=audit_event)
    return _public_role_quick_task_config(record)


def patch_assistant_role_quick_task_config_response(
    *,
    config_id: str,
    current_store: Any,
    payload: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    existing = _require_role_quick_task_config(current_store, config_id=config_id)
    now = _now_iso()
    patch = dict(payload)
    patch.pop("id", None)
    changed_fields = sorted(patch.keys())
    record = _normalized_role_quick_task_config(
        {
            **existing,
            **patch,
            "id": existing["id"],
            "created_at": existing.get("created_at") or now,
            "created_by": existing.get("created_by"),
            "updated_at": now,
            "updated_by": user["id"],
        }
    )
    _ensure_role_quick_task_scope_unique(current_store, record)
    audit_event = current_store.audit(
        event_type="assistant_role_quick_task.updated",
        actor_id=user["id"],
        subject_type="assistant_role_quick_task",
        subject_id=config_id,
        payload=_role_quick_task_audit_payload(record, changed_fields=changed_fields),
    )
    _save_role_quick_task_config(current_store, record, audit_event=audit_event)
    return _public_role_quick_task_config(record)


def set_assistant_role_quick_task_status_response(
    *,
    config_id: str,
    current_store: Any,
    enabled: bool,
    group_enabled: bool | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    updates: dict[str, Any] = {"enabled": enabled}
    if group_enabled is not None:
        updates["group_enabled"] = group_enabled
    record = patch_assistant_role_quick_task_config_response(
        config_id=config_id,
        current_store=current_store,
        payload=updates,
        user=user,
    )
    audit_event = current_store.audit(
        event_type="assistant_role_quick_task.status_changed",
        actor_id=user["id"],
        subject_type="assistant_role_quick_task",
        subject_id=config_id,
        payload={
            "enabled": enabled,
            "group_enabled": group_enabled,
        },
    )
    _persist_audit_event(current_store, audit_event)
    return record


def update_assistant_role_quick_task_rollout_response(
    *,
    config_id: str,
    current_store: Any,
    enterprise_id: str | None,
    rollout_json: dict[str, Any],
    template_version: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    record = patch_assistant_role_quick_task_config_response(
        config_id=config_id,
        current_store=current_store,
        payload={
            "enterprise_id": enterprise_id,
            "rollout_json": rollout_json,
            "template_version": template_version,
        },
        user=user,
    )
    audit_event = current_store.audit(
        event_type="assistant_role_quick_task.rollout_changed",
        actor_id=user["id"],
        subject_type="assistant_role_quick_task",
        subject_id=config_id,
        payload={
            "enterprise_id": enterprise_id,
            "rollout_json": rollout_json,
            "template_version": template_version,
        },
    )
    _persist_audit_event(current_store, audit_event)
    return record


def delete_assistant_role_quick_task_config_response(
    *,
    config_id: str,
    current_store: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    existing = _require_role_quick_task_config(current_store, config_id=config_id)
    audit_event = current_store.audit(
        event_type="assistant_role_quick_task.deleted",
        actor_id=user["id"],
        subject_type="assistant_role_quick_task",
        subject_id=config_id,
        payload=_role_quick_task_audit_payload(existing, changed_fields=[]),
    )
    repository = getattr(current_store, "repository", None)
    delete_record = getattr(repository, "delete_assistant_role_quick_task_record", None)
    if callable(delete_record):
        delete_record(config_id, audit_event=audit_event)
    else:
        getattr(current_store, "assistant_role_quick_tasks", {}).pop(config_id, None)
    return _public_role_quick_task_config(existing)


def list_assistant_role_quick_tasks_response(
    *,
    current_store: Any | None = None,
    user: dict[str, Any],
) -> dict[str, Any]:
    user_roles = set(user.get("roles") or [])
    user_permissions = set(user.get("permissions") or [])
    is_admin = "admin" in user_roles
    configured_rows = _role_quick_task_config_rows(current_store)
    if configured_rows:
        source_groups = _configured_role_quick_task_groups(configured_rows, user=user)
    else:
        source_groups = deepcopy(STANDARD_ASSISTANT_ROLE_QUICK_TASK_GROUPS)
    groups: list[dict[str, Any]] = []
    for group in source_groups:
        if not group.get("enabled", True):
            continue
        group_roles = set(group.get("roles") or [])
        if not is_admin and group_roles and not user_roles.intersection(group_roles):
            continue
        tasks = []
        for task in group.get("tasks") or []:
            if not task.get("enabled", True):
                continue
            permissions = set(task.get("permissions") or [])
            if not is_admin and permissions and not permissions.issubset(user_permissions):
                continue
            tasks.append(task)
        if not tasks:
            continue
        group["tasks"] = sorted(tasks, key=lambda item: int(item.get("sort_order") or 0))
        groups.append(group)
    groups.sort(key=lambda item: int(item.get("sort_order") or 0))
    return {"items": groups, "total": len(groups)}


def _configured_role_quick_task_groups(
    rows: list[dict[str, Any]],
    *,
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    visible_rows = [
        row
        for row in rows
        if _role_quick_task_rollout_matches_user(row, user=user)
    ]
    if not visible_rows:
        return []
    return _role_quick_task_groups_from_rows(visible_rows)


def _role_quick_task_config_rows(current_store: Any | None) -> list[dict[str, Any]]:
    repository = getattr(current_store, "repository", None) if current_store is not None else None
    list_tasks = getattr(repository, "list_assistant_role_quick_tasks", None)
    if callable(list_tasks):
        rows = [dict(row) for row in list_tasks() if isinstance(row, dict)]
        if rows:
            return rows
    configured = (
        getattr(current_store, "assistant_role_quick_tasks", {})
        if current_store is not None
        else {}
    )
    if isinstance(configured, dict):
        return [dict(row) for row in configured.values() if isinstance(row, dict)]
    if isinstance(configured, list):
        return [dict(row) for row in configured if isinstance(row, dict)]
    return []


def _role_quick_task_groups_from_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    dedupe_keys: set[tuple[str, str]] = set()
    sorted_rows = sorted(
        rows,
        key=lambda item: (
            int(item.get("group_sort_order") or 0),
            str(item.get("group_key") or ""),
            int(item.get("sort_order") or 0),
            str(item.get("template_version") or ""),
            str(item.get("id") or ""),
        ),
    )
    for row in sorted_rows:
        group_key = str(row.get("group_key") or "").strip()
        task_key = str(row.get("task_key") or "").strip()
        if not group_key or not task_key:
            continue
        dedupe_key = (group_key, task_key)
        if dedupe_key in dedupe_keys:
            continue
        dedupe_keys.add(dedupe_key)
        group = grouped.setdefault(
            group_key,
            {
                "enabled": bool(row.get("group_enabled", True)),
                **({"enterprise_id": row.get("enterprise_id")} if row.get("enterprise_id") else {}),
                "key": group_key,
                "label": str(row.get("group_label") or group_key),
                "roles": list(row.get("group_roles") or []),
                "sort_order": int(row.get("group_sort_order") or 0),
                "tasks": [],
            },
        )
        group["enabled"] = group["enabled"] and bool(row.get("group_enabled", True))
        group["tasks"].append(
            {
                "analytics_key": row.get("analytics_key"),
                "enabled": bool(row.get("enabled", True)),
                "key": task_key,
                "label": str(row.get("label") or row.get("title") or task_key),
                "permissions": list(row.get("permissions") or []),
                "prompt": str(row.get("prompt") or ""),
                "sort_order": int(row.get("sort_order") or 0),
                "target_draft_type": row.get("target_draft_type"),
                **({"enterprise_id": row.get("enterprise_id")} if row.get("enterprise_id") else {}),
                **(
                    {"template_version": str(row["template_version"])}
                    if row.get("template_version") is not None
                    else {}
                ),
            }
        )
    return sorted(grouped.values(), key=lambda item: int(item.get("sort_order") or 0))


def _normalized_role_quick_task_config(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "analytics_key": _optional_text(payload.get("analytics_key")),
        "created_at": payload.get("created_at"),
        "created_by": _optional_text(payload.get("created_by")),
        "enabled": bool(payload.get("enabled", True)),
        "enterprise_id": _optional_text(payload.get("enterprise_id")),
        "group_enabled": bool(payload.get("group_enabled", True)),
        "group_key": _required_text(payload.get("group_key"), "group_key"),
        "group_label": _required_text(payload.get("group_label"), "group_label"),
        "group_roles": _clean_string_list(payload.get("group_roles")),
        "group_sort_order": int(payload.get("group_sort_order") or 0),
        "id": _required_text(payload.get("id"), "id"),
        "metadata_json": _clean_object(payload.get("metadata_json")),
        "permissions": _clean_string_list(payload.get("permissions")),
        "prompt": _required_text(payload.get("prompt"), "prompt"),
        "rollout_json": _clean_object(payload.get("rollout_json")),
        "sort_order": int(payload.get("sort_order") or 0),
        "target_draft_type": _optional_text(payload.get("target_draft_type")),
        "task_key": _required_text(payload.get("task_key"), "task_key"),
        "template_version": _optional_text(payload.get("template_version")),
        "title": _required_text(payload.get("title"), "title"),
        "updated_at": payload.get("updated_at"),
        "updated_by": _optional_text(payload.get("updated_by")),
    }


def _public_role_quick_task_config(row: dict[str, Any]) -> dict[str, Any]:
    config = _normalized_role_quick_task_config(row)
    return {
        key: value
        for key, value in config.items()
        if value is not None
        or key in {
            "analytics_key",
            "enterprise_id",
            "target_draft_type",
            "template_version",
        }
    }


def _get_role_quick_task_config(
    current_store: Any,
    *,
    config_id: str,
) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    get_config = getattr(repository, "get_assistant_role_quick_task", None)
    if callable(get_config):
        config = get_config(config_id=config_id)
        return dict(config) if isinstance(config, dict) else None
    config = getattr(current_store, "assistant_role_quick_tasks", {}).get(config_id)
    return dict(config) if isinstance(config, dict) else None


def _require_role_quick_task_config(current_store: Any, *, config_id: str) -> dict[str, Any]:
    config = _get_role_quick_task_config(current_store, config_id=config_id)
    if config is None:
        raise api_error(
            404,
            "ASSISTANT_ROLE_QUICK_TASK_NOT_FOUND",
            "Role quick task config not found",
        )
    return config


def _ensure_role_quick_task_scope_unique(current_store: Any, record: dict[str, Any]) -> None:
    scope_key = _role_quick_task_scope_key(record)
    for existing in _role_quick_task_config_rows(current_store):
        if str(existing.get("id") or "") == str(record.get("id") or ""):
            continue
        if _role_quick_task_scope_key(existing) == scope_key:
            raise api_error(
                409,
                "ASSISTANT_ROLE_QUICK_TASK_SCOPE_EXISTS",
                "Role quick task config scope exists",
            )


def _role_quick_task_scope_key(record: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        _optional_text(record.get("enterprise_id")) or "",
        _optional_text(record.get("group_key")) or "",
        _optional_text(record.get("task_key")) or "",
        _optional_text(record.get("template_version")) or "",
    )


def _save_role_quick_task_config(
    current_store: Any,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any],
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, "save_assistant_role_quick_task_record", None)
    if callable(save_record):
        save_record(record, audit_event=audit_event)
        return
    current_store.assistant_role_quick_tasks[record["id"]] = record


def _persist_audit_event(current_store: Any, audit_event: dict[str, Any]) -> None:
    repository = getattr(current_store, "repository", None)
    save_events = getattr(repository, "save_audit_events", None)
    if callable(save_events):
        save_events({"audit_events": [audit_event]})


def _role_quick_task_audit_payload(
    record: dict[str, Any],
    *,
    changed_fields: list[str],
) -> dict[str, Any]:
    return {
        "changed_fields": changed_fields,
        "enabled": record.get("enabled"),
        "enterprise_id": record.get("enterprise_id"),
        "group_enabled": record.get("group_enabled"),
        "group_key": record.get("group_key"),
        "task_key": record.get("task_key"),
        "template_version": record.get("template_version"),
    }


def _role_quick_task_rollout_matches_user(row: dict[str, Any], *, user: dict[str, Any]) -> bool:
    rollout = _clean_object(row.get("rollout_json"))
    if rollout.get("enabled") is False:
        return False
    user_id = str(user.get("id") or "")
    user_roles = {str(role) for role in user.get("roles") or []}
    user_enterprise_id = _user_enterprise_id(user)
    enterprise_id = _optional_text(row.get("enterprise_id"))
    if enterprise_id and enterprise_id != user_enterprise_id:
        return False
    rollout_enterprise_ids = set(_clean_string_list(rollout.get("enterprise_ids")))
    if rollout_enterprise_ids and user_enterprise_id not in rollout_enterprise_ids:
        return False
    allowed_user_ids = set(
        _clean_string_list(rollout.get("user_ids") or rollout.get("allow_user_ids"))
    )
    if allowed_user_ids and user_id not in allowed_user_ids:
        return False
    denied_user_ids = set(
        _clean_string_list(
            rollout.get("deny_user_ids") or rollout.get("excluded_user_ids")
        )
    )
    if user_id in denied_user_ids:
        return False
    allowed_roles = set(_clean_string_list(rollout.get("roles") or rollout.get("role_allowlist")))
    if allowed_roles and not user_roles.intersection(allowed_roles):
        return False
    denied_roles = set(
        _clean_string_list(rollout.get("excluded_roles") or rollout.get("role_denylist"))
    )
    if denied_roles and user_roles.intersection(denied_roles):
        return False
    allowed_versions = set(
        _clean_string_list(
            rollout.get("template_versions")
            or rollout.get("allowed_template_versions")
            or rollout.get("active_template_versions")
        )
    )
    row_template_version = _optional_text(row.get("template_version"))
    user_template_version = _user_template_version(user)
    if allowed_versions:
        candidate_version = user_template_version or row_template_version
        if candidate_version not in allowed_versions:
            return False
    denied_versions = set(
        _clean_string_list(
            rollout.get("disabled_template_versions")
            or rollout.get("excluded_template_versions")
        )
    )
    if row_template_version and row_template_version in denied_versions:
        return False
    if not _rollout_time_window_matches(rollout):
        return False
    percentage = rollout.get("percentage", rollout.get("rollout_percentage"))
    if percentage is not None and not _rollout_percentage_matches(
        percentage,
        seed=f"{user_id}:{row.get('id') or row.get('group_key')}:{row.get('task_key')}",
    ):
        return False
    return True


def _user_enterprise_id(user: dict[str, Any]) -> str | None:
    for key in ("enterprise_id", "tenant_id", "company_id", "organization_id"):
        value = _optional_text(user.get(key))
        if value:
            return value
    scope_summary = user.get("scope_summary")
    if isinstance(scope_summary, dict):
        for key in ("enterprise_id", "tenant_id", "company_id", "organization_id"):
            value = _optional_text(scope_summary.get(key))
            if value:
                return value
    return None


def _user_template_version(user: dict[str, Any]) -> str | None:
    for key in ("assistant_template_version", "template_version"):
        value = _optional_text(user.get(key))
        if value:
            return value
    return None


def _rollout_time_window_matches(rollout: dict[str, Any]) -> bool:
    now = datetime.now(UTC)
    starts_at = _parse_datetime(rollout.get("starts_at") or rollout.get("effective_from"))
    ends_at = _parse_datetime(rollout.get("ends_at") or rollout.get("effective_to"))
    if starts_at is not None and now < starts_at:
        return False
    if ends_at is not None and now > ends_at:
        return False
    return True


def _rollout_percentage_matches(value: Any, *, seed: str) -> bool:
    try:
        percentage = float(value)
    except (TypeError, ValueError):
        return True
    if percentage <= 0:
        return False
    if percentage >= 100:
        return True
    bucket = int(sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % 100
    return bucket < percentage


def _parse_datetime(value: Any) -> datetime | None:
    text = _optional_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _clean_object(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _clean_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = _optional_text(item)
        if text and text not in items:
            items.append(text)
    return items


def _required_text(value: Any, field_name: str) -> str:
    text = _optional_text(value)
    if not text:
        raise api_error(400, "VALIDATION_ERROR", f"{field_name} is required")
    return text


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
