from __future__ import annotations

from time import perf_counter
from typing import Any

from app.services.operational_records import record_audit_event
from app.services.plugin_invocation_runtime import _invoke_action, plugin_action_request_preview
from app.services.plugin_result_mapping import result_mapping_hits, result_write_preview
from app.services.plugin_store_helpers import persist_audit_event, require_admin
from app.services.plugins import ensure_active_plugin_action
from app.services.scheduled_job_sample_reuse_wizard import action_trial_reuse_wizard


def trial_plugin_action_response(
    *,
    action_id: str,
    connection_id: str | None,
    current_store: Any,
    input_payload: dict[str, Any] | None,
    sample_response_summary: dict[str, Any] | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    require_admin(user)
    plugin, connection, action = ensure_active_plugin_action(
        current_store,
        action_id,
        connection_id=connection_id,
    )
    payload = input_payload or {}
    sample_response = sample_response_summary if isinstance(sample_response_summary, dict) else None
    sample_source = (
        "connection_test_response" if sample_response is not None else "action_trial_response"
    )
    start = perf_counter()
    response_summary: dict[str, Any] = sample_response or {}
    error_code = None
    error_detail: dict[str, Any] | None = None
    error_message = None
    status = "succeeded"
    request_preview = plugin_action_request_preview(plugin, connection, action, payload)
    if sample_response is None:
        try:
            response_summary = _invoke_action(
                plugin,
                connection,
                action,
                payload,
                current_store=current_store,
                user=user,
            )
        except Exception as exc:
            status = "failed"
            error_code = exc.__class__.__name__
            error_message = str(exc)
            if hasattr(exc, "detail") and isinstance(exc.detail, dict):
                error_detail = dict(exc.detail)
                error_code = exc.detail.get("code", error_code)
                error_message = exc.detail.get("message", error_message)
    latency_ms = int((perf_counter() - start) * 1000)
    mapping_hits = result_mapping_hits(response_summary, action.get("result_mapping") or {})
    write_preview = result_write_preview(response_summary, action.get("result_mapping") or {})
    reuse_wizard = action_trial_reuse_wizard(
        has_response_summary=bool(response_summary),
        has_write_preview=bool(write_preview),
        sample_source=sample_source,
        trial_status=status,
    )
    audit_event = record_audit_event(
        current_store,
        event_type=f"plugin_action.trial_{status}",
        actor_id=user["id"],
        subject_type="plugin_action",
        subject_id=action["id"],
        payload={
            "action_code": action.get("code"),
            "action_id": action["id"],
            "connection_environment": connection.get("environment"),
            "connection_id": connection["id"],
            "error_code": error_code,
            "input_keys": sorted(payload.keys()),
            "latency_ms": latency_ms,
            "plugin_code": plugin.get("code"),
            "plugin_id": plugin["id"],
            "sample_source": sample_source,
            "status": status,
            "write_target": (action.get("result_mapping") or {}).get(
                "write_target",
                "scheduled_job_result",
            ),
        },
    )
    persist_audit_event(current_store, audit_event)
    return {
        "action_id": action["id"],
        "connection_id": connection["id"],
        "error_code": error_code,
        "error_detail": error_detail,
        "error_message": error_message,
        "latency_ms": latency_ms,
        "mapping_hits": mapping_hits,
        "plugin_id": plugin["id"],
        "request_preview": request_preview,
        "response_summary": response_summary,
        "sample_source": sample_source,
        "scheduled_job_dry_run_seed": {
            "connection_id": connection["id"],
            "input_payload": payload,
            "plugin_action_id": action["id"],
            "plugin_connection_id": connection["id"],
            "plugin_input_mapping": payload,
            "plugin_output_mapping": action.get("result_mapping") or {},
            "response_summary": response_summary,
            "reuse_wizard": reuse_wizard,
            "sample_source": sample_source,
            "write_preview": write_preview,
        },
        "status": status,
        "write_preview": write_preview,
    }
