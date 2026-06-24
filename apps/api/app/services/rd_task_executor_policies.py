from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_roles
from app.core.store import DEFAULT_BRAIN_APP_ID
from app.services.ai_executor_runners import (
    create_ai_executor_task,
    find_available_runner,
    sync_ai_executor_runner_store,
)
from app.services.operational_records import record_audit_event

RD_TASK_EXECUTOR_POLICY_MANAGE_PERMISSION = "delivery.rd_executor_policies.manage"
RD_TASK_EXECUTOR_TYPES = {"claude", "codex", "openclaw"}
RD_TASK_EXECUTOR_POLICY_STATUSES = {"active", "disabled"}
TOKEN_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")


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


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


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
    runner = current_store.ai_executor_runners.get(policy.get("runner_id"))
    repository = current_store.product_git_repositories.get(policy.get("repository_id"))
    product = current_store.products.get(policy.get("product_id"))
    public["runner_name"] = runner.get("name") if runner else None
    public["repository_name"] = repository.get("name") if repository else None
    public["repository_default_branch"] = repository.get("default_branch") if repository else None
    public["product_name"] = product.get("name") if product else None
    return public


def sync_policy_resource_store(current_store: Any, policy: dict[str, Any]) -> None:
    repository = getattr(current_store, "repository", None)
    list_products = getattr(repository, "list_products", None)
    product_id = policy.get("product_id")
    if product_id and product_id not in current_store.products and callable(list_products):
        for product in list_products(active_only=False):
            _cache_product_record(current_store, product)

    list_repositories = getattr(repository, "list_product_git_repositories", None)
    repository_id = policy.get("repository_id")
    if (
        product_id
        and repository_id
        and repository_id not in current_store.product_git_repositories
        and callable(list_repositories)
    ):
        for git_repository in list_repositories(product_id, active_only=False):
            _cache_product_git_repository_record(current_store, git_repository)

    if policy.get("runner_id"):
        sync_ai_executor_runner_store(current_store)


def list_rd_task_executor_policies_response(
    *,
    current_store: Any,
    product_id: str | None,
    status: str | None,
    task_type: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_policy_manager(user)
    sync_rd_task_executor_policy_store(
        current_store,
        product_id=product_id,
        status=status,
        task_type=task_type,
    )
    policies = [
        _policy_public(current_store, policy)
        for policy in current_store.rd_task_executor_policies.values()
        if (product_id is None or policy.get("product_id") == product_id)
        and (status is None or policy.get("status") == status)
        and (task_type is None or policy.get("task_type") == task_type)
    ]
    policies.sort(
        key=lambda item: (
            int(item.get("priority") or 100),
            item.get("task_type") or "",
            item.get("id") or "",
        )
    )
    return {"items": policies, "total": len(policies)}


def _validate_resource_scope(current_store: Any, policy: dict[str, Any]) -> None:
    sync_policy_resource_store(current_store, policy)
    product_id = policy.get("product_id")
    if product_id and product_id not in current_store.products:
        raise api_error(400, "PRODUCT_NOT_FOUND", "product_id does not exist")
    repository_id = policy.get("repository_id")
    if repository_id:
        repository = current_store.product_git_repositories.get(repository_id)
        if repository is None:
            raise api_error(400, "REPOSITORY_NOT_FOUND", "repository_id does not exist")
        if product_id and repository.get("product_id") != product_id:
            raise api_error(
                400,
                "REPOSITORY_SCOPE_MISMATCH",
                "repository must belong to policy product",
            )
    runner_id = policy.get("runner_id")
    if runner_id and runner_id not in current_store.ai_executor_runners:
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
    existing = current_store.rd_task_executor_policies.get(policy_id)
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
    existing = current_store.rd_task_executor_policies.get(policy_id)
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
        for policy in current_store.rd_task_executor_policies.values()
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


def _template_context(task: dict[str, Any], policy: dict[str, Any]) -> dict[str, str]:
    product_context = (
        task.get("product_context") if isinstance(task.get("product_context"), dict) else {}
    )
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
    return {
        "branch": str(policy.get("branch") or ""),
        "module_code": str(task.get("module_code") or ""),
        "product_id": str(task.get("product_id") or ""),
        "product_name": str(product.get("name") or task.get("product_id") or ""),
        "repository_id": str(policy.get("repository_id") or ""),
        "requirement_id": str(task.get("requirement_id") or ""),
        "requirement_title": str(requirement.get("title") or ""),
        "task_id": str(task.get("id") or ""),
        "task_title": str(task.get("title") or ""),
        "task_type": str(task.get("task_type") or ""),
    }


def render_executor_instruction(task: dict[str, Any], policy: dict[str, Any]) -> str:
    context = _template_context(task, policy)

    def replace(match: re.Match[str]) -> str:
        return context.get(match.group(1), match.group(0))

    return TOKEN_PATTERN.sub(replace, str(policy.get("instruction_template") or "")).strip()


def queue_rd_task_executor_task(
    *,
    current_store: Any,
    policy: dict[str, Any],
    task: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    workspace_root = _ensure_non_blank(policy.get("workspace_root"), "workspace_root")
    instruction = render_executor_instruction(task, policy)
    if not instruction:
        raise api_error(400, "RD_EXECUTOR_INSTRUCTION_REQUIRED", "instruction_template is empty")
    runner = find_available_runner(
        current_store,
        executor_type=policy["executor_type"],
        runner_id=policy.get("runner_id"),
        workspace_root=workspace_root,
    )
    input_payload = {
        "branch": policy.get("branch"),
        "output_contract": policy.get("output_contract") or {},
        "product_context": task.get("product_context") or {},
        "repository_id": policy.get("repository_id"),
        "requirement_snapshot": task.get("requirement_snapshot") or {},
        "task": {
            "id": task["id"],
            "task_type": task["task_type"],
            "title": task["title"],
        },
    }
    request_config = {
        "branch": policy.get("branch"),
        "executor_policy_id": policy["id"],
        "output_contract": policy.get("output_contract") or {},
        "repository_id": policy.get("repository_id"),
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
