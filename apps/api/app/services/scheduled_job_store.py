from __future__ import annotations

from typing import Any

from app.services.operational_records import save_single_repository_record


def uses_repository_context(current_store: Any) -> bool:
    return getattr(current_store, "repository", None) is not None


def scheduled_jobs_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    required_methods = (
        "list_ai_agents",
        "list_ai_skills",
        "list_scheduled_job_runs",
        "list_scheduled_jobs",
    )
    if all(callable(getattr(repository, method_name, None)) for method_name in required_methods):
        return repository
    return None


def replace_collection(
    current_store: Any,
    collection_name: str,
    items: list[dict[str, Any]],
) -> None:
    setattr(
        current_store,
        collection_name,
        {str(item["id"]): dict(item) for item in items if item.get("id") is not None},
    )


def read_memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, {})
    return collection if isinstance(collection, dict) else {}


def memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def put_memory_record(
    current_store: Any,
    collection_name: str,
    record: dict[str, Any],
) -> None:
    memory_dict(current_store, collection_name)[str(record["id"])] = record


def delete_memory_record(current_store: Any, collection_name: str, record_id: str) -> None:
    memory_dict(current_store, collection_name).pop(record_id, None)


def sync_ai_skill_store(
    current_store: Any,
    *,
    code: str | None = None,
    status: str | None = None,
) -> None:
    repository = scheduled_jobs_query_repository(current_store)
    if repository is None:
        return
    replace_collection(
        current_store,
        "ai_skills",
        repository.list_ai_skills(code=code, status=status),
    )


def sync_ai_agent_store(
    current_store: Any,
    *,
    brain_app_id: str | None = None,
    status: str | None = None,
) -> None:
    repository = scheduled_jobs_query_repository(current_store)
    if repository is None:
        return
    replace_collection(
        current_store,
        "ai_agents",
        repository.list_ai_agents(brain_app_id=brain_app_id, status=status),
    )


def sync_scheduled_job_store(
    current_store: Any,
    *,
    enabled: bool | None = None,
    job_type: str | None = None,
    status: str | None = None,
) -> None:
    repository = scheduled_jobs_query_repository(current_store)
    if repository is None:
        return
    replace_collection(
        current_store,
        "scheduled_jobs",
        repository.list_scheduled_jobs(enabled=enabled, job_type=job_type, status=status),
    )


def sync_scheduled_job_run_store(
    current_store: Any,
    *,
    run_ids: list[str] | None = None,
    scheduled_job_id: str | None = None,
    status: str | None = None,
) -> None:
    repository = scheduled_jobs_query_repository(current_store)
    if repository is None:
        return
    replace_collection(
        current_store,
        "scheduled_job_runs",
        repository.list_scheduled_job_runs(
            run_ids=run_ids,
            scheduled_job_id=scheduled_job_id,
            status=status,
        ),
    )


def sync_reference_store(current_store: Any) -> None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return
    list_products = getattr(repository, "list_products", None)
    if callable(list_products):
        replace_collection(current_store, "products", list_products(active_only=False))
    list_model_gateway_configs = getattr(repository, "list_model_gateway_configs", None)
    if callable(list_model_gateway_configs):
        replace_collection(
            current_store,
            "model_gateway_configs",
            list_model_gateway_configs(),
        )


def persist_record(
    current_store: Any,
    method_name: str,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    save_single_repository_record(
        current_store,
        method_name,
        record,
        audit_event=audit_event,
    )


def snapshot(current_store: Any, value: Any) -> Any:
    snapshot_fn = getattr(current_store, "snapshot", None)
    if callable(snapshot_fn) and isinstance(value, dict):
        return snapshot_fn(value)
    if isinstance(value, dict):
        return {key: snapshot(current_store, item) for key, item in value.items()}
    if isinstance(value, list):
        return [snapshot(current_store, item) for item in value]
    return value
