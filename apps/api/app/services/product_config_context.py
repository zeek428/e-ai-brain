from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from pydantic import BaseModel

from app.api.deps import api_error
from app.core.listing import list_datetime_timestamp, normalize_list_text
from app.core.store import MemoryStore


class ProductConfigRequestContext:
    def __init__(self, repository: Any) -> None:
        self.repository = repository
        self.products: dict[str, dict[str, Any]] = {}
        self.product_versions: dict[str, dict[str, Any]] = {}
        self.product_version_branch_configs: dict[str, dict[str, Any]] = {}
        self.product_modules: dict[str, dict[str, Any]] = {}
        self.product_git_repositories: dict[str, dict[str, Any]] = {}
        self.related_systems: dict[str, dict[str, Any]] = {}
        self.requirements: dict[str, dict[str, Any]] = {}
        self.ai_tasks: dict[str, dict[str, Any]] = {}
        self.bugs: dict[str, dict[str, Any]] = {}
        self.audit_events: list[dict[str, Any]] = []
        self.counters: dict[str, int] = {}

    def new_id(self, prefix: str) -> str:
        next_id = getattr(self.repository, "next_id", None)
        if callable(next_id):
            allocated_id = next_id(prefix)
            suffix = allocated_id.removeprefix(f"{prefix}_")
            if suffix.isdigit():
                self.counters[prefix] = max(self.counters.get(prefix, 0), int(suffix))
            return allocated_id
        next_value = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = next_value
        return f"{prefix}_{next_value:03d}"


def request_started_at(request: Request) -> float | None:
    started_at = getattr(request.state, "started_at", None)
    return started_at if isinstance(started_at, float) else None


def runtime_repository(current_store: Any) -> Any | None:
    return getattr(current_store, "repository", None)


def uses_repository_context(current_store: Any) -> bool:
    return runtime_repository(current_store) is not None


def product_config_query_repository(current_store: Any) -> Any | None:
    repository = runtime_repository(current_store)
    if repository is None:
        return None
    required_methods = [
        "get_product",
        "list_product_git_repositories",
        "list_product_modules",
        "list_product_versions",
        "list_products",
        "list_related_systems",
    ]
    if all(getattr(repository, method_name, None) is not None for method_name in required_methods):
        return repository
    return None


def product_list_query_repository(current_store: Any) -> Any | None:
    repository = runtime_repository(current_store)
    if repository is None:
        return None
    count_products = getattr(repository, "count_product_summaries", None)
    list_products = getattr(repository, "list_product_summaries", None)
    if callable(count_products) and callable(list_products):
        return repository
    return None


def product_version_list_query_repository(current_store: Any) -> Any | None:
    repository = runtime_repository(current_store)
    if repository is None:
        return None
    count_versions = getattr(repository, "count_product_version_summaries", None)
    list_versions = getattr(repository, "list_product_version_summaries_page", None)
    if callable(count_versions) and callable(list_versions):
        return repository
    return None


def product_version_summary_repository(current_store: Any) -> Any | None:
    repository = runtime_repository(current_store)
    list_versions = getattr(repository, "list_product_version_summaries", None)
    if callable(list_versions):
        return repository
    return None


def payload_collection(payload: dict[str, Any] | None, key: str) -> dict[str, dict[str, Any]]:
    return {str(item_id): dict(item) for item_id, item in (payload or {}).get(key, {}).items()}


def product_config_source_store(repository: Any) -> ProductConfigRequestContext:
    source_store = ProductConfigRequestContext(repository)
    products = repository.list_products(active_only=False)
    source_store.products = {
        str(product["id"]): dict(product)
        for product in products
        if product.get("id") is not None
    }
    for product in products:
        product_id = str(product["id"])
        for version in repository.list_product_versions(product_id, active_only=False):
            source_store.product_versions[str(version["id"])] = dict(version)
            list_branch_configs = getattr(repository, "list_product_version_branch_configs", None)
            if callable(list_branch_configs):
                for branch_config in list_branch_configs(str(version["id"])):
                    source_store.product_version_branch_configs[str(branch_config["id"])] = dict(
                        branch_config
                    )
        for module in repository.list_product_modules(product_id, active_only=False):
            source_store.product_modules[str(module["id"])] = dict(module)
        for git_repository in repository.list_product_git_repositories(
            product_id,
            active_only=False,
        ):
            source_store.product_git_repositories[str(git_repository["id"])] = dict(
                git_repository
            )
    source_store.related_systems = {
        str(system["id"]): dict(system)
        for system in repository.list_related_systems(active_only=False)
        if system.get("id") is not None
    }
    load_requirements = getattr(repository, "load_requirements", None)
    if callable(load_requirements):
        source_store.requirements = payload_collection(load_requirements(), "requirements")
    load_ai_tasks = getattr(repository, "load_ai_tasks", None)
    if callable(load_ai_tasks):
        source_store.ai_tasks = payload_collection(load_ai_tasks(), "ai_tasks")
    load_bugs = getattr(repository, "load_bugs", None)
    if callable(load_bugs):
        source_store.bugs = payload_collection(load_bugs(), "bugs")
    return source_store


def product_config_write_store(current_store: MemoryStore) -> Any:
    repository = product_config_query_repository(current_store)
    if repository is None:
        return current_store
    return product_config_source_store(repository)


def save_product_config_record(
    current_store: Any,
    collection_name: str,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = runtime_repository(current_store)
    save_record = getattr(repository, "save_product_config_record", None)
    if save_record is not None:
        save_record(collection_name, record, audit_event=audit_event)


def delete_product_config_record(
    current_store: Any,
    collection_name: str,
    record_id: str,
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = runtime_repository(current_store)
    delete_record = getattr(repository, "delete_product_config_record", None)
    if delete_record is not None:
        delete_record(collection_name, record_id, audit_event=audit_event)


def save_requirement_record(
    current_store: Any,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = runtime_repository(current_store)
    save_record = getattr(repository, "save_requirement_record", None)
    if save_record is not None:
        save_record(record, audit_event=audit_event)


def record_audit_event(
    current_store: Any,
    *,
    event_type: str,
    actor_id: str,
    subject_type: str | None = None,
    subject_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not uses_repository_context(current_store):
        return current_store.audit(
            event_type=event_type,
            actor_id=actor_id,
            subject_type=subject_type,
            subject_id=subject_id,
            payload=payload,
        )
    return {
        "id": current_store.new_id("audit"),
        "event_type": event_type,
        "actor_id": actor_id,
        "ai_task_id": None,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "payload": payload or {},
        "sequence": len(getattr(current_store, "audit_events", [])) + 1,
        "created_at": datetime.now(UTC).isoformat(),
    }


def payload_updates(payload: BaseModel) -> dict[str, Any]:
    return payload.model_dump(exclude_unset=True)


def ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def ensure_enum(value: str | None, allowed_values: set[str], field: str) -> None:
    if value is not None and value not in allowed_values:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported {field}")


def ensure_unique_value(
    collection: dict[str, dict[str, Any]],
    *,
    field: str,
    value: str,
    conflict_code: str,
    message: str,
    exclude_id: str | None = None,
    scope: dict[str, Any] | None = None,
) -> None:
    for item_id, item in collection.items():
        if exclude_id is not None and item_id == exclude_id:
            continue
        if scope and any(
            item.get(scope_key) != scope_value for scope_key, scope_value in scope.items()
        ):
            continue
        if item.get(field) == value:
            raise api_error(409, conflict_code, message)


def product_current_version_for_list(
    current_store: Any,
    product_id: str,
) -> dict[str, Any] | None:
    status_order = {"active": 0, "testing": 1, "released": 2, "planning": 3, "archived": 4}
    versions = [
        version
        for version in current_store.product_versions.values()
        if version.get("product_id") == product_id
    ]
    if not versions:
        return None
    return sorted(
        versions,
        key=lambda version: (
            status_order.get(str(version.get("status") or ""), 9),
            -list_datetime_timestamp(version.get("updated_at") or version.get("created_at")),
            normalize_list_text(version.get("code")),
        ),
    )[0]


def product_list_projection(item: dict[str, Any], current_store: Any) -> dict[str, Any]:
    product_id = str(item.get("id") or "")
    current_version = (
        None
        if item.get("current_version_name") and item.get("current_version_code")
        else product_current_version_for_list(current_store, product_id)
    )
    module_count = item.get("module_count")
    if module_count is None:
        module_count = sum(
            1
            for module in current_store.product_modules.values()
            if module.get("product_id") == product_id and module.get("status") == "active"
        )
    return {
        **item,
        "current_version_code": item.get("current_version_code")
        or (current_version or {}).get("code"),
        "current_version_name": item.get("current_version_name")
        or (current_version or {}).get("name"),
        "module_count": module_count,
    }


def product_version_summary_projection(
    version: dict[str, Any],
    current_store: Any,
) -> dict[str, Any]:
    product = current_store.products.get(version.get("product_id"), {})
    return {
        **version,
        "product_code": product.get("code"),
        "product_name": product.get("name"),
    }
