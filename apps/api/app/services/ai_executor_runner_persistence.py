from __future__ import annotations

from typing import Any

from app.services.operational_records import save_single_repository_record

RUNNER_RECORD_METHOD_COLLECTIONS = {
    "save_ai_executor_approval_request_record": "ai_executor_approval_requests",
    "save_ai_executor_runner_record": "ai_executor_runners",
    "save_ai_executor_task_record": "ai_executor_tasks",
    "save_collector_run_record": "collector_runs",
    "save_plugin_invocation_log_record": "plugin_invocation_logs",
    "save_scheduled_job_record": "scheduled_jobs",
    "save_scheduled_job_run_record": "scheduled_job_runs",
}


def _repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    required = (
        "list_ai_executor_runners",
        "list_ai_executor_tasks",
        "save_ai_executor_runner_record",
        "save_ai_executor_task_record",
    )
    if repository is not None and all(
        callable(getattr(repository, name, None)) for name in required
    ):
        return repository
    return None


def _read_collection(
    current_store: Any,
    collection_name: str,
) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, {})
    return collection if isinstance(collection, dict) else {}


def _read_record(
    current_store: Any,
    collection_name: str,
    record_id: str | None,
) -> dict[str, Any] | None:
    if record_id is None:
        return None
    item = _read_collection(current_store, collection_name).get(str(record_id))
    return item if isinstance(item, dict) else None


def _memory_collection(
    current_store: Any,
    collection_name: str,
) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name)
    if not isinstance(collection, dict):
        raise TypeError(f"Runner record collection is not mutable: {collection_name}")
    return collection


def _memory_collection_for_method(
    current_store: Any,
    method_name: str,
) -> dict[str, dict[str, Any]]:
    collection_name = RUNNER_RECORD_METHOD_COLLECTIONS.get(method_name)
    if collection_name is None:
        raise ValueError(f"Unsupported runner record save method: {method_name}")
    return _memory_collection(current_store, collection_name)


def _replace_collection(
    current_store: Any,
    collection_name: str,
    items: list[dict[str, Any]],
) -> None:
    setattr(
        current_store,
        collection_name,
        {str(item["id"]): dict(item) for item in items if item.get("id") is not None},
    )


def sync_ai_executor_runner_store(current_store: Any, *, status: str | None = None) -> None:
    repository = _repository(current_store)
    if repository is None:
        return
    _replace_collection(
        current_store,
        "ai_executor_runners",
        repository.list_ai_executor_runners(status=status),
    )


def sync_ai_executor_task_store(
    current_store: Any,
    *,
    ai_task_id: str | None = None,
    product_scope_ids: list[str] | None = None,
    runner_id: str | None = None,
    scheduled_job_run_id: str | None = None,
    status: str | None = None,
) -> None:
    repository = _repository(current_store)
    if repository is None:
        return
    _replace_collection(
        current_store,
        "ai_executor_tasks",
        repository.list_ai_executor_tasks(
            ai_task_id=ai_task_id,
            product_scope_ids=product_scope_ids,
            runner_id=runner_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
        ),
    )


def _persist_record(
    current_store: Any,
    method_name: str,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, method_name, None)
    if callable(save_record):
        save_single_repository_record(current_store, method_name, record, audit_event=audit_event)
        return
    if repository is None:
        _memory_collection_for_method(current_store, method_name)[record["id"]] = record


def _delete_runner_record(
    current_store: Any,
    *,
    audit_event: dict[str, Any] | None = None,
    collection_name: str,
    method_name: str,
    record_id: str,
) -> None:
    repository = getattr(current_store, "repository", None)
    delete_record = getattr(repository, method_name, None)
    if callable(delete_record):
        delete_record(record_id, audit_event=audit_event)
        return
    if repository is None:
        collection = getattr(current_store, collection_name)
        if isinstance(collection, dict):
            collection.pop(record_id, None)


def _persist_task_state_records(
    current_store: Any,
    *,
    audit_events: list[dict[str, Any]],
    reviews: list[dict[str, Any]] | None,
    task: dict[str, Any],
) -> None:
    repository = getattr(current_store, "repository", None)
    save_records = getattr(repository, "save_task_state_records", None)
    if callable(save_records):
        save_records(task=task, audit_events=audit_events, reviews=reviews)
        return
    if repository is None:
        _memory_collection(current_store, "ai_tasks")[task["id"]] = task
        for review in reviews or []:
            _memory_collection(current_store, "human_reviews")[review["id"]] = review


def _existing_pending_review(
    current_store: Any,
    ai_task_id: str,
    stage: str,
) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    load_workflow_runtime = getattr(repository, "load_workflow_runtime", None)
    if callable(load_workflow_runtime):
        payload = load_workflow_runtime()
        for review in payload.get("human_reviews", {}).values():
            if (
                review.get("ai_task_id") == ai_task_id
                and review.get("stage") == stage
                and review.get("status") == "pending"
            ):
                return review
    for review in _read_collection(current_store, "human_reviews").values():
        if (
            review.get("ai_task_id") == ai_task_id
            and review.get("stage") == stage
            and review.get("status") == "pending"
        ):
            return review
    return None
