from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from pydantic import BaseModel

from app.api.deps import api_error
from app.core.listing import list_datetime_timestamp, normalize_list_text
from app.core.store import MemoryStore

PRODUCT_CONFIG_COLLECTION_ATTRS = {
    "product_git_repositories": "product_git_repositories",
    "product_modules": "product_modules",
    "product_version_branch_configs": "product_version_branch_configs",
    "product_versions": "product_versions",
    "products": "products",
    "related_systems": "related_systems",
}


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


def product_config_record_write_store(current_store: MemoryStore) -> Any:
    repository = runtime_repository(current_store)
    if repository is None:
        return current_store
    return ProductConfigRequestContext(repository)


def get_product_record(current_store: Any, product_id: str) -> dict[str, Any] | None:
    get_product = getattr(runtime_repository(current_store), "get_product", None)
    if callable(get_product):
        return get_product(product_id)
    products = getattr(current_store, "products", {})
    return products.get(product_id)


def list_product_records(
    current_store: Any,
    *,
    active_only: bool = False,
) -> list[dict[str, Any]]:
    list_products = getattr(runtime_repository(current_store), "list_products", None)
    if callable(list_products):
        return list_products(active_only=active_only)
    products = getattr(current_store, "products", {})
    return [
        dict(product)
        for product in products.values()
        if not active_only or product.get("status") == "active"
    ]


def get_product_version_record(current_store: Any, version_id: str) -> dict[str, Any] | None:
    get_version = getattr(runtime_repository(current_store), "get_product_version", None)
    if callable(get_version):
        return get_version(version_id)
    versions = getattr(current_store, "product_versions", {})
    return versions.get(version_id)


def list_product_version_records(
    current_store: Any,
    product_id: str,
    *,
    active_only: bool = False,
) -> list[dict[str, Any]]:
    list_versions = getattr(runtime_repository(current_store), "list_product_versions", None)
    if callable(list_versions):
        return list_versions(product_id, active_only=active_only)
    versions = getattr(current_store, "product_versions", {})
    return [
        dict(version)
        for version in versions.values()
        if version.get("product_id") == product_id
        and (not active_only or version.get("status") == "active")
    ]


def get_product_git_repository_record(
    current_store: Any,
    repository_id: str,
) -> dict[str, Any] | None:
    get_repository = getattr(runtime_repository(current_store), "get_product_git_repository", None)
    if callable(get_repository):
        return get_repository(repository_id)
    repositories = getattr(current_store, "product_git_repositories", {})
    return repositories.get(repository_id)


def list_product_git_repository_records(
    current_store: Any,
    product_id: str,
    *,
    active_only: bool = False,
) -> list[dict[str, Any]]:
    list_repositories = getattr(
        runtime_repository(current_store),
        "list_product_git_repositories",
        None,
    )
    if callable(list_repositories):
        return list_repositories(product_id, active_only=active_only)
    repositories = getattr(current_store, "product_git_repositories", {})
    return [
        dict(repository)
        for repository in repositories.values()
        if repository.get("product_id") == product_id
        and (not active_only or repository.get("status") == "active")
    ]


def get_product_module_record(current_store: Any, module_id: str) -> dict[str, Any] | None:
    get_module = getattr(runtime_repository(current_store), "get_product_module", None)
    if callable(get_module):
        return get_module(module_id)
    modules = getattr(current_store, "product_modules", {})
    return modules.get(module_id)


def list_product_module_records(
    current_store: Any,
    product_id: str,
    *,
    active_only: bool = False,
) -> list[dict[str, Any]]:
    list_modules = getattr(runtime_repository(current_store), "list_product_modules", None)
    if callable(list_modules):
        return list_modules(product_id, active_only=active_only)
    modules = getattr(current_store, "product_modules", {})
    return [
        dict(module)
        for module in modules.values()
        if module.get("product_id") == product_id
        and (not active_only or module.get("status") == "active")
    ]


def list_related_system_records(
    current_store: Any,
    *,
    active_only: bool = False,
    product_id: str | None = None,
) -> list[dict[str, Any]]:
    list_systems = getattr(runtime_repository(current_store), "list_related_systems", None)
    if callable(list_systems):
        return list_systems(active_only=active_only, product_id=product_id)
    systems = getattr(current_store, "related_systems", {})
    return [
        dict(system)
        for system in systems.values()
        if (product_id is None or system.get("product_id") == product_id)
        and (not active_only or system.get("status") == "active")
    ]


def product_module_has_related_records(
    current_store: Any,
    *,
    product_id: str,
    module_code: str,
) -> bool:
    has_related_records = getattr(
        runtime_repository(current_store),
        "product_module_has_related_records",
        None,
    )
    if callable(has_related_records):
        return bool(has_related_records(product_id, module_code))
    requirements = getattr(current_store, "requirements", {})
    tasks = getattr(current_store, "ai_tasks", {})
    bugs = getattr(current_store, "bugs", {})
    return any(
        item.get("product_id") == product_id and item.get("module_code") == module_code
        for item in [
            *requirements.values(),
            *tasks.values(),
            *bugs.values(),
        ]
    )


def product_has_related_records(current_store: Any, product_id: str) -> bool:
    has_related_records = getattr(
        runtime_repository(current_store),
        "product_has_related_records",
        None,
    )
    if callable(has_related_records):
        return bool(has_related_records(product_id))
    requirements = getattr(current_store, "requirements", {})
    tasks = getattr(current_store, "ai_tasks", {})
    bugs = getattr(current_store, "bugs", {})
    return any(
        item.get("product_id") == product_id
        for item in [
            *requirements.values(),
            *tasks.values(),
            *bugs.values(),
        ]
    )


def product_version_has_related_records(current_store: Any, version_id: str) -> bool:
    has_related_records = getattr(
        runtime_repository(current_store),
        "product_version_has_related_records",
        None,
    )
    if callable(has_related_records):
        return bool(has_related_records(version_id))
    requirements = getattr(current_store, "requirements", {})
    tasks = getattr(current_store, "ai_tasks", {})
    bugs = getattr(current_store, "bugs", {})
    branch_configs = getattr(current_store, "product_version_branch_configs", {})
    return (
        any(item.get("version_id") == version_id for item in requirements.values())
        or any(item.get("version_id") == version_id for item in tasks.values())
        or any(item.get("version_id") == version_id for item in bugs.values())
        or any(item.get("version_id") == version_id for item in branch_configs.values())
    )


def get_related_system_record(current_store: Any, system_id: str) -> dict[str, Any] | None:
    get_system = getattr(runtime_repository(current_store), "get_related_system", None)
    if callable(get_system):
        return get_system(system_id)
    systems = getattr(current_store, "related_systems", {})
    return systems.get(system_id)


def get_related_system_by_code(current_store: Any, code: str) -> dict[str, Any] | None:
    get_system = getattr(runtime_repository(current_store), "get_related_system_by_code", None)
    if callable(get_system):
        return get_system(code)
    systems = getattr(current_store, "related_systems", {})
    for system in systems.values():
        if system.get("code") == code:
            return system
    return None


def get_product_version_branch_config_record(
    current_store: Any,
    branch_config_id: str,
) -> dict[str, Any] | None:
    get_branch_config = getattr(
        runtime_repository(current_store),
        "get_product_version_branch_config",
        None,
    )
    if callable(get_branch_config):
        return get_branch_config(branch_config_id)
    branch_configs = getattr(current_store, "product_version_branch_configs", {})
    return branch_configs.get(branch_config_id)


def list_product_version_branch_config_records(
    current_store: Any,
    version_id: str,
) -> list[dict[str, Any]]:
    list_branch_configs = getattr(
        runtime_repository(current_store),
        "list_product_version_branch_configs",
        None,
    )
    if callable(list_branch_configs):
        return list_branch_configs(version_id)
    branch_configs = getattr(current_store, "product_version_branch_configs", {})
    return [
        dict(branch_config)
        for branch_config in branch_configs.values()
        if branch_config.get("version_id") == version_id
    ]


def list_product_child_config_records(
    current_store: Any,
    collection_name: str,
    product_id: str,
) -> list[dict[str, Any]]:
    if collection_name == "product_versions":
        return list_product_version_records(current_store, product_id, active_only=False)
    if collection_name == "product_modules":
        return list_product_module_records(current_store, product_id, active_only=False)
    if collection_name == "product_git_repositories":
        return list_product_git_repository_records(current_store, product_id, active_only=False)
    if collection_name == "related_systems":
        return list_related_system_records(current_store, product_id=product_id, active_only=False)
    raise ValueError(f"Unsupported product child collection: {collection_name}")


def get_requirement_record(current_store: Any, requirement_id: str) -> dict[str, Any] | None:
    requirements = getattr(current_store, "requirements", {})
    if requirement_id in requirements:
        return requirements[requirement_id]
    load_requirements = getattr(runtime_repository(current_store), "load_requirements", None)
    if callable(load_requirements):
        return payload_collection(load_requirements(), "requirements").get(requirement_id)
    return None


def _memory_product_config_collection(
    current_store: Any,
    collection_name: str,
) -> dict[str, dict[str, Any]]:
    attr_name = PRODUCT_CONFIG_COLLECTION_ATTRS.get(collection_name)
    if attr_name is None:
        raise ValueError(f"Unsupported product config collection: {collection_name}")
    collection = getattr(current_store, attr_name)
    if not isinstance(collection, dict):
        raise TypeError(f"Product config collection is not mutable: {collection_name}")
    return collection


def _memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def _memory_list(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, list):
        collection = []
        setattr(current_store, collection_name, collection)
    return collection


def save_product_config_record(
    current_store: Any,
    collection_name: str,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> bool:
    repository = runtime_repository(current_store)
    save_record = getattr(repository, "save_product_config_record", None)
    if callable(save_record):
        save_record(collection_name, record, audit_event=audit_event)
        return True
    if repository is None:
        _memory_product_config_collection(current_store, collection_name)[record["id"]] = record
    return False


def delete_product_config_record(
    current_store: Any,
    collection_name: str,
    record_id: str,
    *,
    audit_event: dict[str, Any] | None = None,
) -> bool:
    repository = runtime_repository(current_store)
    delete_record = getattr(repository, "delete_product_config_record", None)
    if callable(delete_record):
        delete_record(collection_name, record_id, audit_event=audit_event)
        return True
    if repository is None:
        _memory_product_config_collection(current_store, collection_name).pop(record_id, None)
    return False


def save_requirement_record(
    current_store: Any,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> bool:
    repository = runtime_repository(current_store)
    save_record = getattr(repository, "save_requirement_record", None)
    if callable(save_record):
        save_record(record, audit_event=audit_event)
        return True
    if repository is None:
        _memory_dict(current_store, "requirements")[record["id"]] = record
    return False


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
        audit = getattr(current_store, "audit", None)
        if callable(audit):
            return audit(
                event_type=event_type,
                actor_id=actor_id,
                subject_type=subject_type,
                subject_id=subject_id,
                payload=payload,
            )
        audit_events = _memory_list(current_store, "audit_events")
        event = {
            "id": current_store.new_id("audit"),
            "event_type": event_type,
            "actor_id": actor_id,
            "ai_task_id": None,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "payload": payload or {},
            "sequence": len(audit_events) + 1,
            "created_at": datetime.now(UTC).isoformat(),
        }
        audit_events.append(event)
        return event
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
    versions = list_product_version_records(current_store, product_id, active_only=False)
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
            for module in list_product_module_records(
                current_store,
                product_id,
                active_only=True,
            )
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
    product = get_product_record(current_store, str(version.get("product_id") or "")) or {}
    return {
        **version,
        "product_code": product.get("code"),
        "product_name": product.get("name"),
    }
