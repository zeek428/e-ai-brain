from __future__ import annotations

import re
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from app.api.deps import api_error, require_roles
from app.core.listing import (
    add_list_observability,
    ensure_list_enum,
    list_text_matches,
    sort_list_items,
)
from app.core.store import DEFAULT_BRAIN_APP_ID
from app.services.ai_executor_runners import (
    create_ai_executor_task,
    find_available_runner,
    sync_ai_executor_runner_store,
)
from app.services.knowledge_documents import (
    knowledge_query_repository,
    knowledge_repository_access_args,
)
from app.services.knowledge_search import memory_knowledge_search_candidates
from app.services.operational_records import record_audit_event

RD_TASK_EXECUTOR_POLICY_MANAGE_PERMISSION = "delivery.rd_executor_policies.manage"
RD_TASK_EXECUTOR_TYPES = {"claude", "codex", "openclaw"}
RD_TASK_EXECUTOR_POLICY_STATUSES = {"active", "disabled"}
RD_TASK_KNOWLEDGE_REFERENCE_LIMIT = 6
RD_TASK_KNOWLEDGE_REFERENCE_MAX_CHARS = 1200
RD_TASK_EXECUTOR_POLICY_SORT_FIELDS = {
    "executor_type",
    "name",
    "priority",
    "product_name",
    "repository_name",
    "runner_name",
    "status",
    "task_type",
    "updated_at",
    "workspace_root",
}
TOKEN_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")
CODE_INSPECTION_CONTEXT_FIELDS = (
    "branch",
    "code_inspection_finding_id",
    "code_inspection_report_id",
    "commit_sha",
    "description",
    "file_path",
    "line_number",
    "recommendation",
    "repository_id",
    "risk_level",
    "rule_id",
    "severity",
    "title",
)


def _can_manage_policy(user: dict[str, Any]) -> bool:
    permissions = set(user.get("permissions") or [])
    roles = set(user.get("roles") or [])
    return (
        RD_TASK_EXECUTOR_POLICY_MANAGE_PERMISSION in permissions
        or "admin" in roles
        or "rd_owner" in roles
    )


def _ensure_policy_manager(user: dict[str, Any]) -> None:
    if not _can_manage_policy(user):
        require_roles(user, {"admin", "rd_owner"})


def _ensure_non_blank(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return text


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _ensure_executor_type(value: Any) -> str:
    executor_type = _ensure_non_blank(value, "executor_type").lower()
    if executor_type not in RD_TASK_EXECUTOR_TYPES:
        raise api_error(400, "VALIDATION_ERROR", "executor_type must be codex, claude or openclaw")
    return executor_type


def _ensure_status(value: Any) -> str:
    status = str(value or "active").strip().lower()
    if status not in RD_TASK_EXECUTOR_POLICY_STATUSES:
        raise api_error(400, "VALIDATION_ERROR", "status must be active or disabled")
    return status


def _repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    required = (
        "delete_rd_task_executor_policy_record",
        "list_rd_task_executor_policies",
        "save_rd_task_executor_policy_record",
    )
    if repository is not None and all(
        callable(getattr(repository, name, None)) for name in required
    ):
        return repository
    return None


def _policy_page_repository(current_store: Any) -> Any | None:
    repository = _repository(current_store)
    if repository is None:
        return None
    if callable(getattr(repository, "count_rd_task_executor_policies", None)) and callable(
        getattr(repository, "list_rd_task_executor_policy_page", None)
    ):
        return repository
    return None


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def _read_memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    return collection if isinstance(collection, dict) else {}


def _policy_collection(current_store: Any) -> dict[str, dict[str, Any]]:
    return _memory_dict(current_store, "rd_task_executor_policies")


def _replace_policies(current_store: Any, policies: list[dict[str, Any]]) -> None:
    collection = _policy_collection(current_store)
    collection.clear()
    collection.update({
        str(policy["id"]): dict(policy)
        for policy in policies
        if policy.get("id") is not None
    })


def _cache_product_record(current_store: Any, product: dict[str, Any]) -> None:
    if product.get("id") is not None:
        _memory_dict(current_store, "products")[str(product["id"])] = dict(product)


def _cache_product_git_repository_record(
    current_store: Any,
    git_repository: dict[str, Any],
) -> None:
    if git_repository.get("id") is not None:
        _memory_dict(current_store, "product_git_repositories")[
            str(git_repository["id"])
        ] = dict(git_repository)


def save_rd_task_executor_policy_record(
    current_store: Any,
    policy: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = _repository(current_store)
    if repository is not None:
        repository.save_rd_task_executor_policy_record(policy, audit_event=audit_event)
        return
    _policy_collection(current_store)[policy["id"]] = policy


def delete_rd_task_executor_policy_record(
    current_store: Any,
    policy_id: str,
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = _repository(current_store)
    if repository is not None:
        repository.delete_rd_task_executor_policy_record(policy_id, audit_event=audit_event)
        return
    _policy_collection(current_store).pop(policy_id, None)


def sync_rd_task_executor_policy_store(
    current_store: Any,
    *,
    product_id: str | None = None,
    status: str | None = None,
    task_type: str | None = None,
) -> None:
    repository = _repository(current_store)
    if repository is None:
        return
    _replace_policies(
        current_store,
        repository.list_rd_task_executor_policies(
            product_id=product_id,
            status=status,
            task_type=task_type,
        ),
    )


def _policy_public(current_store: Any, policy: dict[str, Any]) -> dict[str, Any]:
    sync_policy_resource_store(current_store, policy)
    public = dict(policy)
    runner = _read_memory_dict(current_store, "ai_executor_runners").get(
        policy.get("runner_id")
    )
    repository = _read_memory_dict(current_store, "product_git_repositories").get(
        policy.get("repository_id")
    )
    product = _read_memory_dict(current_store, "products").get(policy.get("product_id"))
    public["runner_name"] = runner.get("name") if runner else public.get("runner_name")
    public["repository_name"] = (
        repository.get("name") if repository else public.get("repository_name")
    )
    public["repository_default_branch"] = (
        repository.get("default_branch")
        if repository
        else public.get("repository_default_branch")
    )
    public["product_name"] = product.get("name") if product else public.get("product_name")
    return public


def sync_policy_resource_store(current_store: Any, policy: dict[str, Any]) -> None:
    repository = getattr(current_store, "repository", None)
    list_products = getattr(repository, "list_products", None)
    product_id = policy.get("product_id")
    if (
        product_id
        and product_id not in _read_memory_dict(current_store, "products")
        and callable(list_products)
    ):
        for product in list_products(active_only=False):
            _cache_product_record(current_store, product)

    list_repositories = getattr(repository, "list_product_git_repositories", None)
    repository_id = policy.get("repository_id")
    if (
        product_id
        and repository_id
        and repository_id not in _read_memory_dict(
            current_store,
            "product_git_repositories",
        )
        and callable(list_repositories)
    ):
        for git_repository in list_repositories(product_id, active_only=False):
            _cache_product_git_repository_record(current_store, git_repository)

    if policy.get("runner_id"):
        sync_ai_executor_runner_store(current_store)


def list_rd_task_executor_policies_response(
    *,
    current_store: Any,
    executor_type: str | None = None,
    name: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    product_id: str | None = None,
    product_name: str | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
    status: str | None = None,
    task_type: str | None = None,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_policy_manager(user)
    started_at = perf_counter()
    if executor_type is not None:
        ensure_list_enum(executor_type, RD_TASK_EXECUTOR_TYPES, "executor_type")
    if status is not None:
        ensure_list_enum(status, RD_TASK_EXECUTOR_POLICY_STATUSES, "status")
    if sort_by is not None:
        ensure_list_enum(sort_by, RD_TASK_EXECUTOR_POLICY_SORT_FIELDS, "sort_by")
    if sort_order is not None:
        ensure_list_enum(sort_order, {"asc", "desc"}, "sort_order")
    with_pagination = page is not None or page_size is not None
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    repository = _policy_page_repository(current_store)
    if with_pagination and repository is not None:
        total = repository.count_rd_task_executor_policies(
            executor_type=executor_type,
            name=name,
            product_id=product_id,
            product_name=product_name,
            status=status,
            task_type=task_type,
        )
        policies = [
            _policy_public(current_store, policy)
            for policy in repository.list_rd_task_executor_policy_page(
                executor_type=executor_type,
                limit=resolved_page_size,
                name=name,
                offset=(resolved_page - 1) * resolved_page_size,
                product_id=product_id,
                product_name=product_name,
                sort_by=sort_by,
                sort_order=sort_order,
                status=status,
                task_type=task_type,
            )
        ]
        return add_list_observability(
            {
                "items": policies,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters={
                "executor_type": executor_type,
                "name": name,
                "product_id": product_id,
                "product_name": product_name,
                "status": status,
                "task_type": task_type,
            },
            list_name="rd_task_executor_policies",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )

    sync_rd_task_executor_policy_store(
        current_store,
        product_id=product_id,
        status=status,
        task_type=task_type,
    )
    policies = [
        _policy_public(current_store, policy)
        for policy in _read_memory_dict(current_store, "rd_task_executor_policies").values()
        if (product_id is None or policy.get("product_id") == product_id)
        and (status is None or policy.get("status") == status)
        and (task_type is None or policy.get("task_type") == task_type)
        and (executor_type is None or policy.get("executor_type") == executor_type)
    ]
    policies = [
        policy
        for policy in policies
        if list_text_matches(policy, name, ("name",))
        and list_text_matches(policy, product_name, ("product_name",))
    ]
    if sort_by:
        policies = sort_list_items(
            policies,
            allowed_fields=RD_TASK_EXECUTOR_POLICY_SORT_FIELDS,
            default_sort_by="priority",
            sort_by=sort_by,
            sort_order=sort_order or "asc",
        )
    else:
        policies.sort(
            key=lambda item: (
                int(item.get("priority") or 100),
                item.get("task_type") or "",
                item.get("id") or "",
            )
        )
    total = len(policies)
    if with_pagination:
        policies = policies[
            (resolved_page - 1) * resolved_page_size : resolved_page * resolved_page_size
        ]
    payload: dict[str, Any] = {"items": policies, "total": total}
    if with_pagination:
        payload["page"] = resolved_page
        payload["page_size"] = resolved_page_size
    return add_list_observability(
        payload,
        filters={
            "executor_type": executor_type,
            "name": name,
            "product_id": product_id,
            "product_name": product_name,
            "status": status,
            "task_type": task_type,
        },
        list_name="rd_task_executor_policies",
        page=resolved_page if with_pagination else None,
        page_size=resolved_page_size if with_pagination else None,
        sort_by=sort_by,
        sort_order=sort_order,
        started_at=started_at,
    )


def _validate_resource_scope(current_store: Any, policy: dict[str, Any]) -> None:
    sync_policy_resource_store(current_store, policy)
    product_id = policy.get("product_id")
    if product_id and product_id not in _read_memory_dict(current_store, "products"):
        raise api_error(400, "PRODUCT_NOT_FOUND", "product_id does not exist")
    repository_id = policy.get("repository_id")
    if repository_id:
        repository = _read_memory_dict(
            current_store,
            "product_git_repositories",
        ).get(repository_id)
        if repository is None:
            raise api_error(400, "REPOSITORY_NOT_FOUND", "repository_id does not exist")
        if product_id and repository.get("product_id") != product_id:
            raise api_error(
                400,
                "REPOSITORY_SCOPE_MISMATCH",
                "repository must belong to policy product",
            )
    runner_id = policy.get("runner_id")
    if (
        runner_id
        and runner_id not in _read_memory_dict(current_store, "ai_executor_runners")
    ):
        raise api_error(400, "AI_EXECUTOR_RUNNER_NOT_FOUND", "runner_id does not exist")


def _policy_from_payload(
    *,
    current_store: Any,
    existing: dict[str, Any] | None,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    data = (
        payload.model_dump(exclude_unset=True)
        if hasattr(payload, "model_dump")
        else dict(getattr(payload, "__dict__", {}) or {})
    )

    def value(field: str, default: Any = None) -> Any:
        return data[field] if field in data else default

    if existing is None:
        policy_id = current_store.new_id("rd_executor_policy")
        base = {
            "brain_app_id": DEFAULT_BRAIN_APP_ID,
            "created_at": now,
            "created_by": user["id"],
            "id": policy_id,
        }
    else:
        base = dict(existing)

    policy = {
        **base,
        "branch": _optional_text(value("branch", base.get("branch"))),
        "executor_type": _ensure_executor_type(value("executor_type", base.get("executor_type"))),
        "instruction_template": _ensure_non_blank(
            value("instruction_template", base.get("instruction_template")),
            "instruction_template",
        ),
        "name": _ensure_non_blank(value("name", base.get("name")), "name"),
        "output_contract": dict(value("output_contract", base.get("output_contract") or {}) or {}),
        "priority": int(value("priority", base.get("priority", 100)) or 100),
        "product_id": _optional_text(value("product_id", base.get("product_id"))),
        "repository_id": _optional_text(value("repository_id", base.get("repository_id"))),
        "runner_id": _optional_text(value("runner_id", base.get("runner_id"))),
        "status": _ensure_status(value("status", base.get("status", "active"))),
        "task_type": _ensure_non_blank(value("task_type", base.get("task_type")), "task_type"),
        "timeout_seconds": int(value("timeout_seconds", base.get("timeout_seconds", 1800)) or 1800),
        "updated_at": now,
        "workspace_root": str(
            value("workspace_root", base.get("workspace_root", "")) or ""
        ).strip(),
    }
    if policy["timeout_seconds"] < 60 or policy["timeout_seconds"] > 24 * 60 * 60:
        raise api_error(400, "VALIDATION_ERROR", "timeout_seconds must be between 60 and 86400")
    if policy["priority"] < 1 or policy["priority"] > 10000:
        raise api_error(400, "VALIDATION_ERROR", "priority must be between 1 and 10000")
    _validate_resource_scope(current_store, policy)
    return policy


def create_rd_task_executor_policy_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_policy_manager(user)
    policy = _policy_from_payload(
        current_store=current_store,
        existing=None,
        payload=payload,
        user=user,
    )
    audit_event = record_audit_event(
        current_store,
        event_type="rd_task_executor_policy.created",
        actor_id=user["id"],
        subject_type="rd_task_executor_policy",
        subject_id=policy["id"],
        payload={
            "executor_type": policy["executor_type"],
            "runner_id": policy.get("runner_id"),
            "task_type": policy["task_type"],
        },
    )
    save_rd_task_executor_policy_record(
        current_store,
        policy,
        audit_event=audit_event,
    )
    return _policy_public(current_store, policy)


def patch_rd_task_executor_policy_response(
    *,
    current_store: Any,
    payload: Any,
    policy_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_policy_manager(user)
    sync_rd_task_executor_policy_store(current_store)
    existing = _read_memory_dict(current_store, "rd_task_executor_policies").get(policy_id)
    if existing is None:
        raise api_error(404, "NOT_FOUND", "RD task executor policy not found")
    policy = _policy_from_payload(
        current_store=current_store,
        existing=existing,
        payload=payload,
        user=user,
    )
    audit_event = record_audit_event(
        current_store,
        event_type="rd_task_executor_policy.updated",
        actor_id=user["id"],
        subject_type="rd_task_executor_policy",
        subject_id=policy_id,
        payload={
            "executor_type": policy["executor_type"],
            "runner_id": policy.get("runner_id"),
            "status": policy["status"],
            "task_type": policy["task_type"],
        },
    )
    save_rd_task_executor_policy_record(
        current_store,
        policy,
        audit_event=audit_event,
    )
    return _policy_public(current_store, policy)


def delete_rd_task_executor_policy_response(
    *,
    current_store: Any,
    policy_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_policy_manager(user)
    sync_rd_task_executor_policy_store(current_store)
    existing = _read_memory_dict(current_store, "rd_task_executor_policies").get(policy_id)
    if existing is None:
        raise api_error(404, "NOT_FOUND", "RD task executor policy not found")
    audit_event = record_audit_event(
        current_store,
        event_type="rd_task_executor_policy.deleted",
        actor_id=user["id"],
        subject_type="rd_task_executor_policy",
        subject_id=policy_id,
        payload={"task_type": existing.get("task_type")},
    )
    delete_rd_task_executor_policy_record(
        current_store,
        policy_id,
        audit_event=audit_event,
    )
    return {"deleted": True, "id": policy_id}


def _matching_policies(current_store: Any, task: dict[str, Any]) -> list[dict[str, Any]]:
    sync_rd_task_executor_policy_store(
        current_store,
        status="active",
        task_type=str(task.get("task_type") or ""),
    )
    product_id = task.get("product_id")
    brain_app_id = task.get("brain_app_id") or DEFAULT_BRAIN_APP_ID
    policies = [
        policy
        for policy in _read_memory_dict(current_store, "rd_task_executor_policies").values()
        if policy.get("status") == "active"
        and policy.get("task_type") == task.get("task_type")
        and (policy.get("brain_app_id") or DEFAULT_BRAIN_APP_ID) == brain_app_id
        and (policy.get("product_id") in {None, "", product_id})
    ]
    policies.sort(
        key=lambda policy: (
            0 if policy.get("product_id") == product_id else 1,
            int(policy.get("priority") or 100),
            policy.get("id") or "",
        ),
    )
    return policies


def resolve_rd_task_executor_policy(
    current_store: Any,
    task: dict[str, Any],
) -> dict[str, Any] | None:
    policies = _matching_policies(current_store, task)
    return policies[0] if policies else None


def _task_input(task: dict[str, Any]) -> dict[str, Any]:
    return task.get("input_json") if isinstance(task.get("input_json"), dict) else {}


def _task_product_context(task: dict[str, Any]) -> dict[str, Any]:
    product_context = (
        task.get("product_context") if isinstance(task.get("product_context"), dict) else {}
    )
    return product_context


def _task_repository(task: dict[str, Any]) -> dict[str, Any]:
    input_json = _task_input(task)
    product_context = _task_product_context(task)
    input_repository = input_json.get("repository")
    if isinstance(input_repository, dict):
        return input_repository
    context_repository = product_context.get("repository")
    return context_repository if isinstance(context_repository, dict) else {}


def _executor_branch(policy: dict[str, Any], task: dict[str, Any]) -> str:
    input_json = _task_input(task)
    repository = _task_repository(task)
    return str(
        policy.get("branch")
        or input_json.get("branch")
        or repository.get("default_branch")
        or "",
    )


def _executor_repository_id(policy: dict[str, Any], task: dict[str, Any]) -> str:
    input_json = _task_input(task)
    repository = _task_repository(task)
    return str(
        policy.get("repository_id")
        or input_json.get("repository_id")
        or repository.get("id")
        or "",
    )


def _code_inspection_context(task: dict[str, Any], policy: dict[str, Any]) -> dict[str, str]:
    input_json = _task_input(task)
    repository = _task_repository(task)
    context = {
        field: str(input_json.get(field) or "")
        for field in CODE_INSPECTION_CONTEXT_FIELDS
    }
    context["branch"] = _executor_branch(policy, task)
    context["repository_id"] = _executor_repository_id(policy, task)
    context["repository_default_branch"] = str(repository.get("default_branch") or "")
    context["repository_project_path"] = str(repository.get("project_path") or "")
    context["repository_remote_url"] = str(repository.get("remote_url") or "")
    return context


def _code_inspection_payload(task: dict[str, Any], policy: dict[str, Any]) -> dict[str, str]:
    return {
        key: value
        for key, value in _code_inspection_context(task, policy).items()
        if value
    }


def _code_inspection_instruction_block(task: dict[str, Any], policy: dict[str, Any]) -> str:
    if task.get("task_type") != "code_inspection_remediation":
        return ""
    context = _code_inspection_context(task, policy)
    if not any(context.get(key) for key in ("file_path", "rule_id", "recommendation")):
        return ""
    return "\n".join(
        [
            "代码巡检整改上下文：",
            f"- 目标文件: {context.get('file_path') or '未提供'}",
            f"- 目标行号: {context.get('line_number') or '未提供'}",
            f"- 规则 ID: {context.get('rule_id') or '未提供'}",
            f"- 严重级别: {context.get('severity') or context.get('risk_level') or '未提供'}",
            f"- 分支: {context.get('branch') or '未提供'}",
            "- 仓库: "
            f"{context.get('repository_project_path') or context.get('repository_id') or '未提供'}",
            f"- 报告 ID: {context.get('code_inspection_report_id') or '未提供'}",
            f"- Finding ID: {context.get('code_inspection_finding_id') or '未提供'}",
            f"- 问题描述: {context.get('description') or '未提供'}",
            f"- 修复建议: {context.get('recommendation') or '未提供'}",
            "",
            "执行要求：",
            "1. 优先只处理本条 finding 指向的代码位置及必要的近邻测试调整。",
            "2. 不要进行仓库级安全扫描；需要验证时只做与本条 finding 直接相关的最小检查。",
            "3. 不要输出、复制或保留真实密钥；测试数据应替换为明显的假值或运行时配置。",
            "4. 输出结构化结果，说明修改点、验证方式和剩余风险。",
        ],
    )


def _task_version_id(task: dict[str, Any]) -> str | None:
    product_context = _task_product_context(task)
    version = product_context.get("version")
    version_id = task.get("version_id")
    if not version_id and isinstance(version, dict):
        version_id = version.get("id")
    text = str(version_id or "").strip()
    return text or None


def _knowledge_candidate_matches_task(
    candidate: dict[str, Any],
    *,
    product_id: str,
    version_id: str | None,
) -> bool:
    document = candidate.get("document") if isinstance(candidate.get("document"), dict) else {}
    if str(document.get("product_id") or "").strip() != product_id:
        return False
    document_version_id = str(document.get("version_id") or "").strip()
    if version_id and document_version_id and document_version_id != version_id:
        return False
    return True


def _truncate_knowledge_content(content: Any) -> str:
    text = str(content or "").strip()
    if len(text) <= RD_TASK_KNOWLEDGE_REFERENCE_MAX_CHARS:
        return text
    return f"{text[:RD_TASK_KNOWLEDGE_REFERENCE_MAX_CHARS].rstrip()}..."


def _knowledge_reference_from_candidate(candidate: dict[str, Any]) -> dict[str, Any] | None:
    document = candidate.get("document") if isinstance(candidate.get("document"), dict) else {}
    chunk = candidate.get("chunk") if isinstance(candidate.get("chunk"), dict) else {}
    chunk_id = str(chunk.get("id") or "").strip()
    document_id = str(document.get("id") or chunk.get("document_id") or "").strip()
    content = _truncate_knowledge_content(chunk.get("content"))
    if not chunk_id or not document_id or not content:
        return None
    return {
        "chunk_id": chunk_id,
        "chunk_index": int(chunk.get("chunk_index") or 0),
        "content": content,
        "document_id": document_id,
        "doc_type": document.get("doc_type"),
        "folder_id": document.get("folder_id"),
        "knowledge_space_id": document.get("knowledge_space_id"),
        "title": document.get("title") or document_id,
    }


def _task_knowledge_reference_candidates(
    *,
    current_store: Any,
    product_id: str,
    user: dict[str, Any],
    version_id: str | None,
) -> list[dict[str, Any]]:
    repository = knowledge_query_repository(current_store)
    search_chunks = getattr(repository, "search_knowledge_chunks", None)
    if callable(search_chunks):
        access_args = knowledge_repository_access_args(user)
        search_args = {
            **access_args,
            "product_id": product_id,
            "query": None,
            "version_id": version_id,
        }
        try:
            return list(search_chunks(**search_args))
        except TypeError:
            return list(search_chunks(**access_args, query=None))
    return memory_knowledge_search_candidates(
        current_store=current_store,
        knowledge_space_id=None,
        user=user,
    )


def _task_knowledge_references(
    *,
    current_store: Any,
    task: dict[str, Any],
    user: dict[str, Any],
) -> list[dict[str, Any]]:
    product_id = str(task.get("product_id") or "").strip()
    if not product_id:
        return []
    version_id = _task_version_id(task)
    references: list[dict[str, Any]] = []
    seen_chunk_ids: set[str] = set()
    for candidate in _task_knowledge_reference_candidates(
        current_store=current_store,
        product_id=product_id,
        user=user,
        version_id=version_id,
    ):
        if not _knowledge_candidate_matches_task(
            candidate,
            product_id=product_id,
            version_id=version_id,
        ):
            continue
        reference = _knowledge_reference_from_candidate(candidate)
        if reference is None or reference["chunk_id"] in seen_chunk_ids:
            continue
        seen_chunk_ids.add(reference["chunk_id"])
        references.append(reference)
        if len(references) >= RD_TASK_KNOWLEDGE_REFERENCE_LIMIT:
            break
    return references


def _knowledge_references_instruction_block(references: list[dict[str, Any]]) -> str:
    if not references:
        return ""
    lines = ["产品知识中心上下文："]
    for index, reference in enumerate(references, start=1):
        title = reference.get("title") or reference.get("document_id") or "未命名文档"
        doc_type = reference.get("doc_type") or "文档"
        chunk_index = reference.get("chunk_index")
        chunk_label = f"片段 {chunk_index}" if chunk_index is not None else "片段"
        lines.append(
            f"{index}. {title}（{doc_type} / {chunk_label}）：{reference.get('content') or ''}"
        )
    lines.extend(
        [
            "",
            "执行要求：",
            "1. 优先遵循以上产品知识中心内容；如与任务要求冲突，请在输出摘要中说明。",
            "2. 不要把其他产品、无权限或未索引文档作为实现依据。",
        ]
    )
    return "\n".join(lines)


def _template_context(task: dict[str, Any], policy: dict[str, Any]) -> dict[str, str]:
    product_context = _task_product_context(task)
    input_json = _task_input(task)
    bug = input_json.get("bug") if isinstance(input_json.get("bug"), dict) else {}
    product = (
        product_context.get("product")
        if isinstance(product_context.get("product"), dict)
        else {}
    )
    requirement = (
        task.get("requirement_snapshot")
        if isinstance(task.get("requirement_snapshot"), dict)
        else {}
    )
    code_inspection = _code_inspection_context(task, policy)
    return {
        "branch": _executor_branch(policy, task),
        "bug_id": str(bug.get("id") or ""),
        "bug_severity": str(bug.get("severity") or ""),
        "bug_title": str(bug.get("title") or ""),
        "code_inspection_finding_id": code_inspection.get("code_inspection_finding_id", ""),
        "code_inspection_report_id": code_inspection.get("code_inspection_report_id", ""),
        "commit_sha": code_inspection.get("commit_sha", ""),
        "file_path": code_inspection.get("file_path", ""),
        "line_number": code_inspection.get("line_number", ""),
        "module_code": str(task.get("module_code") or ""),
        "product_id": str(task.get("product_id") or ""),
        "product_name": str(product.get("name") or task.get("product_id") or ""),
        "recommendation": code_inspection.get("recommendation", ""),
        "repository_id": _executor_repository_id(policy, task),
        "risk_level": code_inspection.get("risk_level", ""),
        "rule_id": code_inspection.get("rule_id", ""),
        "severity": code_inspection.get("severity", ""),
        "requirement_id": str(task.get("requirement_id") or ""),
        "requirement_title": str(requirement.get("title") or ""),
        "task_id": str(task.get("id") or ""),
        "task_title": str(task.get("title") or ""),
        "task_type": str(task.get("task_type") or ""),
    }


def render_executor_instruction(
    task: dict[str, Any],
    policy: dict[str, Any],
    *,
    knowledge_references: list[dict[str, Any]] | None = None,
) -> str:
    context = _template_context(task, policy)

    def replace(match: re.Match[str]) -> str:
        return context.get(match.group(1), match.group(0))

    instruction = TOKEN_PATTERN.sub(replace, str(policy.get("instruction_template") or "")).strip()
    code_inspection_block = _code_inspection_instruction_block(task, policy)
    if code_inspection_block:
        instruction = f"{instruction}\n\n{code_inspection_block}".strip()
    knowledge_block = _knowledge_references_instruction_block(knowledge_references or [])
    if knowledge_block:
        instruction = f"{instruction}\n\n{knowledge_block}".strip()
    return instruction


def queue_rd_task_executor_task(
    *,
    current_store: Any,
    policy: dict[str, Any],
    task: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    workspace_root = _ensure_non_blank(policy.get("workspace_root"), "workspace_root")
    knowledge_references = _task_knowledge_references(
        current_store=current_store,
        task=task,
        user=user,
    )
    instruction = render_executor_instruction(
        task,
        policy,
        knowledge_references=knowledge_references,
    )
    if not instruction:
        raise api_error(400, "RD_EXECUTOR_INSTRUCTION_REQUIRED", "instruction_template is empty")
    runner = find_available_runner(
        current_store,
        executor_type=policy["executor_type"],
        runner_id=policy.get("runner_id"),
        workspace_root=workspace_root,
    )
    branch = _executor_branch(policy, task) or None
    repository_id = _executor_repository_id(policy, task) or None
    input_payload = {
        "branch": branch,
        "bug": (task.get("input_json") or {}).get("bug") or {},
        "code_inspection": _code_inspection_payload(task, policy),
        "knowledge_references": knowledge_references,
        "output_contract": policy.get("output_contract") or {},
        "product_context": task.get("product_context") or {},
        "repository_id": repository_id,
        "requirement_snapshot": task.get("requirement_snapshot") or {},
        "task": {
            "id": task["id"],
            "task_type": task["task_type"],
            "title": task["title"],
        },
    }
    request_config = {
        "branch": branch,
        "executor_policy_id": policy["id"],
        "output_contract": policy.get("output_contract") or {},
        "repository_id": repository_id,
        "source": "rd_task_executor_policy",
    }
    return create_ai_executor_task(
        current_store,
        action_id=None,
        ai_task_id=task["id"],
        connection_id=None,
        created_by=user["id"],
        executor_type=policy["executor_type"],
        input_payload=input_payload,
        instruction=instruction,
        plugin_invocation_log_id=None,
        request_config=request_config,
        runner_id=runner["id"],
        scheduled_job_id=None,
        scheduled_job_run_id=None,
        timeout_seconds=int(policy.get("timeout_seconds") or 1800),
        workspace_root=workspace_root,
    )
