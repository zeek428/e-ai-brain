from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from app.api.deps import api_error, require_permissions
from app.core.listing import add_list_observability, list_text_matches, sort_list_items
from app.services.operational_records import record_audit_event
from app.services.scheduled_job_common import ensure_enum, ensure_non_blank
from app.services.scheduled_job_store import (
    persist_record,
    put_memory_record,
    read_memory_dict,
    scheduled_jobs_query_repository,
    sync_ai_agent_store,
    sync_ai_skill_store,
    sync_reference_store,
)
from app.services.skill_packages import store_skill_package

AI_SKILL_STATUSES = {"active", "draft", "disabled"}
AI_AGENT_STATUSES = {"active", "disabled"}
AI_SKILL_SORT_FIELDS = {
    "code",
    "created_at",
    "name",
    "requires_human_review",
    "risk_level",
    "source_type",
    "status",
    "updated_at",
    "version",
}
AI_AGENT_SORT_FIELDS = {
    "brain_app_id",
    "code",
    "created_at",
    "model_gateway_config_id",
    "name",
    "status",
    "updated_at",
}


def require_ai_capabilities_manager(user: dict[str, Any]) -> None:
    require_permissions(user, {"system.ai_capabilities.manage"})


def public_skill(skill: dict[str, Any]) -> dict[str, Any]:
    return dict(skill)


def public_agent(agent: dict[str, Any]) -> dict[str, Any]:
    return dict(agent)


def list_ai_skills_response(
    *,
    code: str | None,
    current_store: Any,
    keyword: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    requires_human_review: bool | None = None,
    risk_level: str | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    source_type: str | None = None,
    started_at: float | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    if status is not None:
        ensure_enum(status, AI_SKILL_STATUSES, "status")
    if sort_order not in {"asc", "desc"}:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_order")
    resolved_sort_by = sort_by or "code"
    if resolved_sort_by not in AI_SKILL_SORT_FIELDS:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_by")
    resolved_started_at = started_at or perf_counter()
    with_pagination = page is not None or page_size is not None
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    filters = {
        "code": code,
        "keyword": keyword,
        "requires_human_review": requires_human_review,
        "risk_level": risk_level,
        "source_type": source_type,
        "status": status,
    }
    repository = scheduled_jobs_query_repository(current_store)
    if (
        repository is not None
        and with_pagination
        and callable(getattr(repository, "count_ai_skills", None))
        and callable(getattr(repository, "list_ai_skills_page", None))
    ):
        count_args = {
            "code": code,
            "keyword": keyword,
            "requires_human_review": requires_human_review,
            "risk_level": risk_level,
            "source_type": source_type,
            "status": status,
        }
        total = repository.count_ai_skills(**count_args)
        items = repository.list_ai_skills_page(
            **count_args,
            limit=resolved_page_size,
            offset=(resolved_page - 1) * resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
        )
        return add_list_observability(
            {
                "items": [public_skill(item) for item in items],
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="ai_skills",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=resolved_started_at,
        )
    sync_ai_skill_store(current_store, code=code, status=status)
    items = []
    for skill in read_memory_dict(current_store, "ai_skills").values():
        if code is not None and skill.get("code") != code:
            continue
        if status is not None and skill.get("status") != status:
            continue
        if (
            requires_human_review is not None
            and bool(skill.get("requires_human_review")) != requires_human_review
        ):
            continue
        if risk_level is not None and skill.get("risk_level") != risk_level:
            continue
        if source_type is not None and skill.get("source_type") != source_type:
            continue
        if not list_text_matches(
            skill,
            keyword,
            ("id", "code", "name", "prompt_template", "source_type", "risk_level", "version"),
        ):
            continue
        items.append(public_skill(skill))
    if with_pagination:
        sorted_items = sort_list_items(
            items,
            allowed_fields=AI_SKILL_SORT_FIELDS,
            default_sort_by="code",
            sort_by=resolved_sort_by,
            sort_order=sort_order,
        )
        start = (resolved_page - 1) * resolved_page_size
        page_items = sorted_items[start : start + resolved_page_size]
        return add_list_observability(
            {
                "items": page_items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": len(sorted_items),
            },
            filters=filters,
            list_name="ai_skills",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=resolved_started_at,
        )
    items.sort(key=lambda item: (item.get("code") or "", item.get("version") or "", item["id"]))
    return {"items": items, "total": len(items)}


def create_ai_skill_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_ai_capabilities_manager(user)
    ensure_enum(payload.status, AI_SKILL_STATUSES, "status")
    now = datetime.now(UTC).isoformat()
    skill_id = current_store.new_id("skill")
    skill = {
        "allowed_tools": payload.allowed_tools,
        "code": ensure_non_blank(payload.code, "code"),
        "created_at": now,
        "created_by": user["id"],
        "description": payload.description,
        "id": skill_id,
        "input_schema": payload.input_schema,
        "name": ensure_non_blank(payload.name, "name"),
        "output_schema": payload.output_schema,
        "manifest": {},
        "package_checksum": None,
        "package_entry": None,
        "package_files": [],
        "package_size_bytes": 0,
        "package_uri": None,
        "prompt_template": ensure_non_blank(payload.prompt_template, "prompt_template"),
        "required_context": payload.required_context,
        "requires_human_review": payload.requires_human_review,
        "risk_level": payload.risk_level,
        "source_type": "inline",
        "status": payload.status,
        "updated_at": now,
        "version": payload.version,
    }
    put_memory_record(current_store, "ai_skills", skill)
    audit_event = record_audit_event(
        current_store,
        event_type="ai_skill.created",
        actor_id=user["id"],
        subject_type="ai_skill",
        subject_id=skill_id,
        payload={"code": skill["code"], "status": skill["status"]},
    )
    persist_record(
        current_store,
        "save_ai_skill_record",
        skill,
        audit_event=audit_event,
    )
    return public_skill(skill)


def create_ai_skill_package_response(
    *,
    code: str,
    current_store: Any,
    name: str,
    package_bytes: bytes,
    requires_human_review: bool,
    risk_level: str,
    status: str,
    user: dict[str, Any],
    version: str,
) -> dict[str, Any]:
    require_ai_capabilities_manager(user)
    ensure_enum(status, AI_SKILL_STATUSES, "status")
    now = datetime.now(UTC).isoformat()
    skill_code = ensure_non_blank(code, "code")
    skill_version = ensure_non_blank(version, "version")
    skill_id = current_store.new_id("skill")
    stored_package = store_skill_package(
        package_bytes=package_bytes,
        skill_code=skill_code,
        skill_id=skill_id,
        version=skill_version,
    )
    manifest = dict(stored_package.manifest)
    skill_name = ensure_non_blank(str(manifest.get("name") or name), "name")
    skill = {
        "allowed_tools": list(manifest.get("allowed_tools") or []),
        "code": str(manifest.get("code") or skill_code),
        "created_at": now,
        "created_by": user["id"],
        "description": manifest.get("description"),
        "id": skill_id,
        "input_schema": {},
        "manifest": manifest,
        "name": skill_name,
        "output_schema": {},
        "package_checksum": stored_package.checksum,
        "package_entry": stored_package.entry,
        "package_files": stored_package.files,
        "package_size_bytes": stored_package.size_bytes,
        "package_uri": stored_package.package_uri,
        "prompt_template": stored_package.entry_content,
        "required_context": list(manifest.get("required_context") or []),
        "requires_human_review": bool(
            manifest.get("requires_human_review", requires_human_review),
        ),
        "risk_level": str(manifest.get("risk_level") or risk_level),
        "source_type": "package",
        "status": status,
        "updated_at": now,
        "version": str(manifest.get("version") or skill_version),
    }
    put_memory_record(current_store, "ai_skills", skill)
    audit_event = record_audit_event(
        current_store,
        event_type="ai_skill.package_uploaded",
        actor_id=user["id"],
        subject_type="ai_skill",
        subject_id=skill_id,
        payload={
            "checksum": skill["package_checksum"],
            "code": skill["code"],
            "file_count": len(skill["package_files"]),
            "status": skill["status"],
        },
    )
    persist_record(
        current_store,
        "save_ai_skill_record",
        skill,
        audit_event=audit_event,
    )
    return public_skill(skill)


def patch_ai_skill_response(
    *,
    current_store: Any,
    payload: Any,
    skill_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_ai_capabilities_manager(user)
    sync_ai_skill_store(current_store)
    skill = read_memory_dict(current_store, "ai_skills").get(skill_id)
    if skill is None:
        raise api_error(404, "NOT_FOUND", "AI skill not found")
    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates:
        ensure_enum(updates["status"], AI_SKILL_STATUSES, "status")
    for key in ("code", "name", "prompt_template"):
        if key in updates:
            updates[key] = ensure_non_blank(updates[key], key)
    skill = {**skill, **updates, "updated_at": datetime.now(UTC).isoformat()}
    put_memory_record(current_store, "ai_skills", skill)
    audit_event = record_audit_event(
        current_store,
        event_type="ai_skill.updated",
        actor_id=user["id"],
        subject_type="ai_skill",
        subject_id=skill_id,
        payload={"code": skill["code"], "status": skill["status"]},
    )
    persist_record(
        current_store,
        "save_ai_skill_record",
        skill,
        audit_event=audit_event,
    )
    return public_skill(skill)


def list_ai_agents_response(
    *,
    brain_app_id: str | None,
    current_store: Any,
    keyword: str | None = None,
    model_gateway_config_id: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    started_at: float | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    if status is not None:
        ensure_enum(status, AI_AGENT_STATUSES, "status")
    if sort_order not in {"asc", "desc"}:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_order")
    resolved_sort_by = sort_by or "code"
    if resolved_sort_by not in AI_AGENT_SORT_FIELDS:
        raise api_error(400, "VALIDATION_ERROR", "Unsupported sort_by")
    resolved_started_at = started_at or perf_counter()
    with_pagination = page is not None or page_size is not None
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    filters = {
        "brain_app_id": brain_app_id,
        "keyword": keyword,
        "model_gateway_config_id": model_gateway_config_id,
        "status": status,
    }
    repository = scheduled_jobs_query_repository(current_store)
    if (
        repository is not None
        and with_pagination
        and callable(getattr(repository, "count_ai_agents", None))
        and callable(getattr(repository, "list_ai_agents_page", None))
    ):
        count_args = {
            "brain_app_id": brain_app_id,
            "keyword": keyword,
            "model_gateway_config_id": model_gateway_config_id,
            "status": status,
        }
        total = repository.count_ai_agents(**count_args)
        items = repository.list_ai_agents_page(
            **count_args,
            limit=resolved_page_size,
            offset=(resolved_page - 1) * resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
        )
        return add_list_observability(
            {
                "items": [public_agent(item) for item in items],
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="ai_agents",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=resolved_started_at,
        )
    sync_ai_agent_store(current_store, brain_app_id=brain_app_id, status=status)
    items = []
    for agent in read_memory_dict(current_store, "ai_agents").values():
        if brain_app_id is not None and agent.get("brain_app_id") != brain_app_id:
            continue
        if status is not None and agent.get("status") != status:
            continue
        if (
            model_gateway_config_id is not None
            and agent.get("model_gateway_config_id") != model_gateway_config_id
        ):
            continue
        if not list_text_matches(
            agent,
            keyword,
            ("id", "brain_app_id", "code", "name", "system_prompt", "model_gateway_config_id"),
        ):
            continue
        items.append(public_agent(agent))
    if with_pagination:
        sorted_items = sort_list_items(
            items,
            allowed_fields=AI_AGENT_SORT_FIELDS,
            default_sort_by="code",
            sort_by=resolved_sort_by,
            sort_order=sort_order,
        )
        start = (resolved_page - 1) * resolved_page_size
        page_items = sorted_items[start : start + resolved_page_size]
        return add_list_observability(
            {
                "items": page_items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": len(sorted_items),
            },
            filters=filters,
            list_name="ai_agents",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=resolved_started_at,
        )
    items.sort(
        key=lambda item: (item.get("brain_app_id") or "", item.get("code") or "", item["id"]),
    )
    return {"items": items, "total": len(items)}


def ensure_active_model_gateway(current_store: Any, config_id: str | None) -> str | None:
    if config_id is None:
        return None
    sync_reference_store(current_store)
    config = read_memory_dict(current_store, "model_gateway_configs").get(config_id)
    if config is None:
        raise api_error(404, "NOT_FOUND", "Model gateway config not found")
    if config.get("status") != "active":
        raise api_error(400, "MODEL_GATEWAY_CONFIG_INACTIVE", "Model gateway config is inactive")
    return config_id


def ensure_active_skills(current_store: Any, skill_ids: list[str]) -> list[str]:
    sync_ai_skill_store(current_store)
    for skill_id in skill_ids:
        skill = read_memory_dict(current_store, "ai_skills").get(skill_id)
        if skill is None:
            raise api_error(404, "NOT_FOUND", "AI skill not found")
        if skill.get("status") != "active":
            raise api_error(400, "AI_SKILL_INACTIVE", "AI skill is inactive")
    return skill_ids


def create_ai_agent_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_ai_capabilities_manager(user)
    sync_ai_skill_store(current_store)
    sync_reference_store(current_store)
    ensure_enum(payload.status, AI_AGENT_STATUSES, "status")
    ensure_active_model_gateway(current_store, payload.model_gateway_config_id)
    ensure_active_skills(current_store, payload.default_skill_ids)
    now = datetime.now(UTC).isoformat()
    agent_id = current_store.new_id("agent")
    agent = {
        "brain_app_id": ensure_non_blank(payload.brain_app_id, "brain_app_id"),
        "code": ensure_non_blank(payload.code, "code"),
        "created_at": now,
        "created_by": user["id"],
        "default_skill_ids": list(payload.default_skill_ids),
        "description": payload.description,
        "execution_policy": payload.execution_policy,
        "id": agent_id,
        "model_gateway_config_id": payload.model_gateway_config_id,
        "name": ensure_non_blank(payload.name, "name"),
        "status": payload.status,
        "system_prompt": ensure_non_blank(payload.system_prompt, "system_prompt"),
        "tool_policy": payload.tool_policy,
        "updated_at": now,
    }
    put_memory_record(current_store, "ai_agents", agent)
    audit_event = record_audit_event(
        current_store,
        event_type="ai_agent.created",
        actor_id=user["id"],
        subject_type="ai_agent",
        subject_id=agent_id,
        payload={"code": agent["code"], "status": agent["status"]},
    )
    persist_record(
        current_store,
        "save_ai_agent_record",
        agent,
        audit_event=audit_event,
    )
    return public_agent(agent)


def patch_ai_agent_response(
    *,
    agent_id: str,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_ai_capabilities_manager(user)
    sync_ai_agent_store(current_store)
    sync_ai_skill_store(current_store)
    sync_reference_store(current_store)
    agent = read_memory_dict(current_store, "ai_agents").get(agent_id)
    if agent is None:
        raise api_error(404, "NOT_FOUND", "AI agent not found")
    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates:
        ensure_enum(updates["status"], AI_AGENT_STATUSES, "status")
    if "model_gateway_config_id" in updates:
        ensure_active_model_gateway(current_store, updates["model_gateway_config_id"])
    if "default_skill_ids" in updates:
        ensure_active_skills(current_store, updates["default_skill_ids"])
    for key in ("brain_app_id", "code", "name", "system_prompt"):
        if key in updates:
            updates[key] = ensure_non_blank(updates[key], key)
    agent = {**agent, **updates, "updated_at": datetime.now(UTC).isoformat()}
    put_memory_record(current_store, "ai_agents", agent)
    audit_event = record_audit_event(
        current_store,
        event_type="ai_agent.updated",
        actor_id=user["id"],
        subject_type="ai_agent",
        subject_id=agent_id,
        payload={"code": agent["code"], "status": agent["status"]},
    )
    persist_record(
        current_store,
        "save_ai_agent_record",
        agent,
        audit_event=audit_event,
    )
    return public_agent(agent)
