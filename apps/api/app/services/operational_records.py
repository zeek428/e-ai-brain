from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from app.api.deps import api_error, require_any_permission_or_roles
from app.services.product_config_context import product_config_source_store

COLLECTOR_TYPES = {
    "code_inspection",
        "dashboard_snapshot_refresh",
        "deployment_request",
        "gitlab_daily_code_metric",
    "iteration_plan_suggestion",
    "jenkins_release",
    "lifecycle_context_refresh",
    "online_log_metric",
    "pending_attribution_retry",
    "plugin_action_invoke",
    "user_feedback",
    "user_usage_metric",
}
COLLECTOR_RUN_STATUSES = {"cancelled", "failed", "running", "succeeded"}
COLLECTOR_TERMINAL_STATUSES = {"cancelled", "failed", "succeeded"}
PENDING_ATTRIBUTION_SOURCE_TYPES = COLLECTOR_TYPES
PENDING_ATTRIBUTION_STATUSES = {"ignored", "pending", "resolved"}
PENDING_ATTRIBUTION_RESOLUTION_ACTIONS = {"ignore_as_noise", "link_existing_context"}
GITLAB_DAILY_METRIC_STATUSES = {"collected", "failed", "partial"}
JENKINS_RELEASE_STATUSES = {"canceled", "failed", "running", "success"}


def uses_repository_context(current_store: Any) -> bool:
    return getattr(current_store, "repository", None) is not None


def operational_query_repository(current_store: Any) -> Any | None:
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    required_methods = (
        "list_collector_runs",
        "list_gitlab_daily_code_metrics",
        "list_jenkins_release_records",
        "list_online_log_metrics",
        "list_pending_attribution_items",
    )
    if not all(
        callable(getattr(repository, method_name, None))
        for method_name in required_methods
    ):
        return None
    return repository


def operational_write_store(current_store: Any) -> Any:
    repository = operational_query_repository(current_store)
    if repository is None:
        return current_store
    source_store = product_config_source_store(repository)
    collection_loaders = {
        "collector_runs": lambda: repository.list_collector_runs(),
        "gitlab_daily_code_metrics": lambda: repository.list_gitlab_daily_code_metrics(),
        "jenkins_release_records": lambda: repository.list_jenkins_release_records(),
        "online_log_metrics": lambda: repository.list_online_log_metrics(),
        "pending_attribution_items": lambda: repository.list_pending_attribution_items(),
    }
    if callable(getattr(repository, "list_deployment_requests", None)):
        collection_loaders["deployment_requests"] = lambda: repository.list_deployment_requests()
    if callable(getattr(repository, "list_deployment_runs", None)):
        collection_loaders["deployment_runs"] = lambda: repository.list_deployment_runs()
    for collection_name, loader in collection_loaders.items():
        setattr(
            source_store,
            collection_name,
            {
                str(item["id"]): dict(item)
                for item in loader()
                if item.get("id") is not None
            },
        )
    return source_store


def save_single_repository_record(
    current_store: Any,
    method_name: str,
    record: dict[str, Any],
    *,
    audit_event: dict[str, Any] | None = None,
) -> None:
    repository = getattr(current_store, "repository", None)
    save_record = getattr(repository, method_name, None)
    if callable(save_record):
        save_record(record, audit_event=audit_event)


def _memory_list(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, list):
        collection = []
        setattr(current_store, collection_name, collection)
    return collection


def read_memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if not isinstance(collection, dict):
        collection = {}
        setattr(current_store, collection_name, collection)
    return collection


def read_memory_records(current_store: Any, collection_name: str) -> list[dict[str, Any]]:
    return list(read_memory_dict(current_store, collection_name).values())


def _audit_events_collection(current_store: Any) -> list[dict[str, Any]]:
    return _memory_list(current_store, "audit_events")


def record_audit_event(
    current_store: Any,
    *,
    event_type: str,
    actor_id: str,
    subject_type: str,
    subject_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    audit = getattr(current_store, "audit", None)
    if callable(audit):
        return audit(
            event_type=event_type,
            actor_id=actor_id,
            subject_type=subject_type,
            subject_id=subject_id,
            payload=payload,
        )
    now = datetime.now(UTC).isoformat()
    event = {
        "id": current_store.new_id("audit_event"),
        "event_type": event_type,
        "actor_id": actor_id,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "payload": payload or {},
        "created_at": now,
    }
    _audit_events_collection(current_store).append(event)
    return event


def ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def ensure_enum(value: str | None, allowed_values: set[str], field: str) -> None:
    if value is None:
        return
    if value not in allowed_values:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported {field}")


def payload_updates(payload: BaseModel) -> dict[str, Any]:
    return payload.model_dump(exclude_unset=True)


def parse_optional_time(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    text = ensure_non_blank(value, field_name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise api_error(400, "VALIDATION_ERROR", f"Invalid {field_name}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat()


def require_collector_run_write_role(user: dict[str, Any]) -> None:
    require_any_permission_or_roles(user, {"devops.read"}, {"product_owner", "rd_owner"})


def validate_collector_product_context(current_store: Any, *, product_id: str | None) -> None:
    if product_id is None:
        return
    product = read_memory_dict(current_store, "products").get(product_id)
    if product is None:
        raise api_error(404, "NOT_FOUND", "Product not found")
    if product["status"] != "active":
        raise api_error(400, "PRODUCT_INACTIVE", "Inactive product cannot be used")


def validate_collector_run_request(current_store: Any, payload: Any) -> tuple[str, str | None]:
    ensure_enum(payload.collector_type, COLLECTOR_TYPES, "collector_type")
    ensure_enum(payload.status, COLLECTOR_RUN_STATUSES, "status")
    source_system = ensure_non_blank(payload.source_system, "source_system")
    if payload.records_imported < 0:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "records_imported must be greater than or equal to 0",
        )
    validate_collector_product_context(current_store, product_id=payload.product_id)
    if payload.status == "failed":
        ensure_non_blank(payload.error_message, "error_message")
    started_at = parse_optional_time(payload.started_at, "started_at")
    return source_system, started_at


def collector_run_patch_updates(run: dict[str, Any], payload: Any) -> dict[str, Any]:
    requested = payload_updates(payload)
    if requested.get("status") is None:
        requested.pop("status", None)
    if "payload_summary" in requested and requested["payload_summary"] is None:
        raise api_error(400, "VALIDATION_ERROR", "payload_summary must be an object")
    if "records_imported" in requested and requested["records_imported"] is None:
        raise api_error(400, "VALIDATION_ERROR", "records_imported is required")
    status = requested.get("status", run["status"])
    ensure_enum(status, COLLECTOR_RUN_STATUSES, "status")
    if run["status"] in COLLECTOR_TERMINAL_STATUSES and status != run["status"]:
        raise api_error(
            409,
            "COLLECTOR_RUN_STATE_INVALID",
            "Terminal collector run cannot change status",
        )
    if requested.get("records_imported") is not None and requested["records_imported"] < 0:
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "records_imported must be greater than or equal to 0",
        )

    finished_at = parse_optional_time(requested.get("finished_at"), "finished_at")
    if status == "running" and finished_at is not None:
        raise api_error(400, "VALIDATION_ERROR", "running collector run cannot have finished_at")

    error_message = requested.get("error_message", run.get("error_message"))
    if status == "failed":
        ensure_non_blank(error_message, "error_message")

    updates = {}
    for key in ("error_message", "payload_summary", "records_imported", "status"):
        if key in requested:
            updates[key] = requested[key]
    if finished_at is not None:
        updates["finished_at"] = finished_at
    elif status in COLLECTOR_TERMINAL_STATUSES and not run.get("finished_at"):
        updates["finished_at"] = datetime.now(UTC).isoformat()
    if status == "running":
        updates["finished_at"] = None
    return updates


def list_collector_runs_response(
    *,
    collector_type: str | None,
    current_store: Any,
    product_id: str | None,
    source_system: str | None,
    status: str | None,
) -> dict[str, Any]:
    ensure_enum(collector_type, COLLECTOR_TYPES, "collector_type")
    ensure_enum(status, COLLECTOR_RUN_STATUSES, "status")
    source_system = ensure_non_blank(source_system, "source_system") if source_system else None
    repository = operational_query_repository(current_store)
    list_runs = getattr(repository, "list_collector_runs", None)
    if callable(list_runs):
        items = list_runs(
            collector_type=collector_type,
            product_id=product_id,
            status=status,
            source_system=source_system,
        )
        return {"items": items, "total": len(items)}
    items = []
    for run in read_memory_records(current_store, "collector_runs"):
        if collector_type is not None and run.get("collector_type") != collector_type:
            continue
        if product_id is not None and run.get("product_id") != product_id:
            continue
        if status is not None and run.get("status") != status:
            continue
        if source_system is not None and run.get("source_system") != source_system:
            continue
        items.append(run)
    items.sort(
        key=lambda item: (
            item.get("started_at") or "",
            item.get("updated_at") or item.get("created_at") or "",
            item["id"],
        ),
        reverse=True,
    )
    return {"items": items, "total": len(items)}


def create_collector_run_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_collector_run_write_role(user)
    write_store = operational_write_store(current_store)
    source_system, started_at = validate_collector_run_request(write_store, payload)
    now = datetime.now(UTC).isoformat()
    status = payload.status
    run_id = write_store.new_id("collector_run")
    run = {
        "collector_type": payload.collector_type,
        "created_at": now,
        "created_by": user["id"],
        "error_message": payload.error_message,
        "finished_at": now if status in COLLECTOR_TERMINAL_STATUSES else None,
        "id": run_id,
        "payload_summary": payload.payload_summary,
        "product_id": payload.product_id,
        "records_imported": payload.records_imported,
        "source_system": source_system,
        "started_at": started_at or now,
        "status": status,
        "updated_at": now,
    }
    if not uses_repository_context(write_store):
        write_store.collector_runs[run_id] = run
    audit_event = record_audit_event(
        write_store,
        event_type="collector_run.created",
        actor_id=user["id"],
        subject_type="collector_run",
        subject_id=run_id,
        payload={
            "collector_type": run["collector_type"],
            "product_id": run["product_id"],
            "source_system": run["source_system"],
            "status": run["status"],
        },
    )
    save_single_repository_record(
        write_store,
        "save_collector_run_record",
        run,
        audit_event=audit_event,
    )
    return run


def patch_collector_run_response(
    *,
    current_store: Any,
    payload: Any,
    run_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_collector_run_write_role(user)
    write_store = operational_write_store(current_store)
    run = write_store.collector_runs.get(run_id)
    if run is None:
        raise api_error(404, "NOT_FOUND", "Collector run not found")
    updates = collector_run_patch_updates(run, payload)
    if updates:
        run = {**run, **updates, "updated_at": datetime.now(UTC).isoformat()}
        if not uses_repository_context(write_store):
            write_store.collector_runs[run_id] = run
    audit_event = record_audit_event(
        write_store,
        event_type="collector_run.updated",
        actor_id=user["id"],
        subject_type="collector_run",
        subject_id=run_id,
        payload={
            "collector_type": run["collector_type"],
            "records_imported": run["records_imported"],
            "status": run["status"],
        },
    )
    save_single_repository_record(
        write_store,
        "save_collector_run_record",
        run,
        audit_event=audit_event,
    )
    return run
