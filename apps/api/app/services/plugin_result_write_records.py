from __future__ import annotations

from typing import Any

from app.core.listing import add_list_observability, sort_list_items
from app.services.plugin_result_mapping import result_write_preview
from app.services.product_scope import product_scope_filter
from app.services.result_write_targets import result_write_target_label

RESULT_WRITE_RECORD_STATUSES = {"cancelled", "failed", "not_run", "running", "succeeded"}
RESULT_WRITE_RECORD_SORT_FIELDS = {
    "created_at",
    "id",
    "plugin_action_id",
    "plugin_invocation_log_id",
    "records_imported",
    "scheduled_job_id",
    "scheduled_job_run_id",
    "source_type",
    "status",
    "updated_at",
    "write_target",
}


def _read_memory_dict(current_store: Any, collection_name: str) -> dict[str, dict[str, Any]]:
    collection = getattr(current_store, collection_name, None)
    if isinstance(collection, dict):
        return collection
    return {}


def _read_memory_record(
    current_store: Any,
    collection_name: str,
    record_id: str | None,
) -> dict[str, Any] | None:
    if not record_id:
        return None
    return _read_memory_dict(current_store, collection_name).get(record_id)


def result_write_record_summary_fields(
    *,
    feedback: dict[str, Any],
    preview: dict[str, Any],
) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for key in (
        "candidate_count",
        "delivery_id",
        "delivery_status",
        "preview_value",
        "report_preview",
        "sample_records",
        "source_row_count",
        "subject",
    ):
        if key in feedback:
            fields[key] = feedback[key]
        elif key in preview:
            fields[key] = preview[key]
    return fields


def result_write_record_from_scheduled_run(
    current_store: Any,
    run: dict[str, Any],
) -> dict[str, Any] | None:
    result_summary = (
        run.get("result_summary")
        if isinstance(run.get("result_summary"), dict)
        else {}
    )
    execution_nodes = (
        result_summary.get("execution_nodes")
        if isinstance(result_summary.get("execution_nodes"), dict)
        else {}
    )
    result_action = (
        execution_nodes.get("result_action")
        if isinstance(execution_nodes.get("result_action"), dict)
        else {}
    )
    if not result_action:
        return None
    feedback = (
        result_action.get("feedback")
        if isinstance(result_action.get("feedback"), dict)
        else {}
    )
    preview = (
        feedback.get("write_preview")
        if isinstance(feedback.get("write_preview"), dict)
        else {}
    )
    write_target = str(
        result_action.get("write_target")
        or feedback.get("write_target")
        or preview.get("write_target")
        or result_summary.get("write_target")
        or "scheduled_job_result",
    )
    snapshot = (
        run.get("resolved_plugin_snapshot")
        if isinstance(run.get("resolved_plugin_snapshot"), dict)
        else {}
    )
    snapshot_plugin = snapshot.get("plugin") if isinstance(snapshot.get("plugin"), dict) else {}
    snapshot_connection = (
        snapshot.get("connection") if isinstance(snapshot.get("connection"), dict) else {}
    )
    snapshot_action = snapshot.get("action") if isinstance(snapshot.get("action"), dict) else {}
    scheduled_job_id = run.get("scheduled_job_id")
    job = _read_memory_record(current_store, "scheduled_jobs", str(scheduled_job_id))
    return {
        "created_at": run.get("finished_at") or run.get("started_at"),
        "feedback": feedback,
        "id": f"result_write_record_{run['id']}",
        "plugin_action_id": (
            result_action.get("action_id")
            or snapshot_action.get("id")
            or run.get("plugin_action_id")
        ),
        "plugin_code": snapshot_plugin.get("code"),
        "plugin_connection_id": (
            snapshot_connection.get("id")
            or run.get("plugin_connection_id")
        ),
        "plugin_id": snapshot_plugin.get("id"),
        "plugin_invocation_log_id": (
            feedback.get("plugin_invocation_log_id")
            or run.get("plugin_invocation_log_id")
        ),
        "preview": preview,
        "records_imported": (
            result_action.get("records_imported")
            or feedback.get("records_imported")
            or preview.get("records_imported")
            or run.get("records_imported")
            or 0
        ),
        "scheduled_job_id": scheduled_job_id,
        "scheduled_job_name": job.get("name") if isinstance(job, dict) else None,
        "scheduled_job_run_id": run.get("id"),
        "source_type": "scheduled_job_run",
        "status": result_action.get("status") or run.get("status"),
        "summary_fields": result_write_record_summary_fields(
            feedback=feedback,
            preview=preview,
        ),
        "updated_at": run.get("finished_at") or run.get("updated_at"),
        "write_target": write_target,
        "write_target_label": (
            result_action.get("write_target_label")
            or preview.get("write_target_label")
            or result_write_target_label(write_target)
        ),
    }


def result_write_record_from_invocation_log(
    current_store: Any,
    log: dict[str, Any],
) -> dict[str, Any] | None:
    if log.get("scheduled_job_run_id"):
        return None
    action = _read_memory_record(current_store, "plugin_actions", str(log.get("action_id")))
    if not isinstance(action, dict):
        return None
    mapping = action.get("result_mapping") if isinstance(action.get("result_mapping"), dict) else {}
    response_summary = (
        log.get("response_summary") if isinstance(log.get("response_summary"), dict) else {}
    )
    preview = result_write_preview(response_summary, mapping)
    write_target = str(
        preview.get("write_target")
        or mapping.get("write_target")
        or "scheduled_job_result",
    )
    plugin = _read_memory_record(current_store, "integration_plugins", str(log.get("plugin_id")))
    return {
        "created_at": log.get("created_at"),
        "feedback": {
            "plugin_invocation_log_id": log.get("id"),
            "response_summary": response_summary,
            "write_preview": preview,
        },
        "id": f"result_write_record_{log['id']}",
        "plugin_action_id": log.get("action_id"),
        "plugin_code": plugin.get("code") if isinstance(plugin, dict) else None,
        "plugin_connection_id": log.get("connection_id"),
        "plugin_id": log.get("plugin_id"),
        "plugin_invocation_log_id": log.get("id"),
        "preview": preview,
        "records_imported": preview.get("records_imported") or 0,
        "scheduled_job_id": log.get("scheduled_job_id"),
        "scheduled_job_name": None,
        "scheduled_job_run_id": None,
        "source_type": "plugin_invocation_log",
        "status": log.get("status"),
        "summary_fields": result_write_record_summary_fields(
            feedback={},
            preview=preview,
        ),
        "updated_at": log.get("updated_at") or log.get("created_at"),
        "write_target": write_target,
        "write_target_label": preview.get("write_target_label")
        or result_write_target_label(write_target),
    }


def _record_product_id_from_job_reference(
    current_store: Any,
    *,
    scheduled_job_id: Any = None,
    scheduled_job_run_id: Any = None,
) -> str | None:
    job_id = scheduled_job_id
    if not job_id and scheduled_job_run_id:
        run = _read_memory_record(
            current_store,
            "scheduled_job_runs",
            str(scheduled_job_run_id),
        )
        job_id = run.get("scheduled_job_id") if isinstance(run, dict) else None
    job = _read_memory_record(current_store, "scheduled_jobs", str(job_id))
    product_id = job.get("product_id") if isinstance(job, dict) else None
    return str(product_id) if product_id else None


def _result_write_record_matches_product_scope(
    current_store: Any,
    record: dict[str, Any],
    product_scope_ids: set[str] | None,
) -> bool:
    if product_scope_ids is None:
        return True
    product_id = _record_product_id_from_job_reference(
        current_store,
        scheduled_job_id=record.get("scheduled_job_id"),
        scheduled_job_run_id=record.get("scheduled_job_run_id"),
    )
    return product_id is not None and product_id in product_scope_ids


def list_result_write_records_payload(
    *,
    current_store: Any,
    page: int | None = None,
    page_size: int | None = None,
    plugin_action_id: str | None,
    scheduled_job_id: str | None,
    scheduled_job_run_id: str | None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    started_at: float | None = None,
    status: str | None,
    user: dict[str, Any],
    write_target: str | None,
) -> dict[str, Any]:
    resolved_sort_by = sort_by or "created_at"
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    with_pagination = page is not None or page_size is not None
    scoped_product_ids = product_scope_filter(user)
    scoped_product_id_set = set(scoped_product_ids) if scoped_product_ids is not None else None
    records: list[dict[str, Any]] = []
    for run in _read_memory_dict(current_store, "scheduled_job_runs").values():
        record = result_write_record_from_scheduled_run(current_store, run)
        if record is not None:
            records.append(record)
    for log in _read_memory_dict(current_store, "plugin_invocation_logs").values():
        record = result_write_record_from_invocation_log(current_store, log)
        if record is not None:
            records.append(record)

    filtered = []
    for record in records:
        if not _result_write_record_matches_product_scope(
            current_store,
            record,
            scoped_product_id_set,
        ):
            continue
        if write_target is not None and record.get("write_target") != write_target:
            continue
        if status is not None and record.get("status") != status:
            continue
        if scheduled_job_id is not None and record.get("scheduled_job_id") != scheduled_job_id:
            continue
        if (
            scheduled_job_run_id is not None
            and record.get("scheduled_job_run_id") != scheduled_job_run_id
        ):
            continue
        if plugin_action_id is not None and record.get("plugin_action_id") != plugin_action_id:
            continue
        filtered.append(record)
    sorted_records = sort_list_items(
        filtered,
        allowed_fields=RESULT_WRITE_RECORD_SORT_FIELDS,
        default_sort_by="created_at",
        sort_by=resolved_sort_by,
        sort_order=sort_order,
    )
    if with_pagination:
        start_index = (resolved_page - 1) * resolved_page_size
        paged_records = sorted_records[start_index : start_index + resolved_page_size]
        return add_list_observability(
            {
                "items": paged_records,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": len(sorted_records),
            },
            filters={
                "plugin_action_id": plugin_action_id,
                "product_scope_ids": scoped_product_ids,
                "scheduled_job_id": scheduled_job_id,
                "scheduled_job_run_id": scheduled_job_run_id,
                "status": status,
                "write_target": write_target,
            },
            list_name="result_write_records",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    return {"items": sorted_records, "total": len(sorted_records)}
