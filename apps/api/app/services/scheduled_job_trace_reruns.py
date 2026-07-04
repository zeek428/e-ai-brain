from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.services import scheduled_job_store as job_store
from app.services.operational_records import record_audit_event
from app.services.plugin_result_mapping import json_path_value, records_imported_from_mapping
from app.services.plugins import invoke_plugin_action_response, resolve_plugin_snapshot
from app.services.scheduled_job_access import (
    require_scheduled_job_runner,
    scheduled_job_matches_product_scope,
    scheduled_job_plugin_invocation_user,
)
from app.services.scheduled_job_ai_processing import (
    run_scheduled_job_ai_processing,
    skill_codes_for_job,
)
from app.services.scheduled_job_audit import scheduled_job_run_audit_payload
from app.services.scheduled_job_execution_engine import (
    ScheduledJobExecutionEngine as JobExecutionEngine,
)
from app.services.scheduled_job_read_models import public_scheduled_job_run
from app.services.scheduled_job_result_actions import (
    execute_generic_result_actions,
    inferred_output_record_count,
)
from app.services.scheduled_job_user_feedback import resolve_job_plugin_output_mapping

TRACE_NODE_PREVIEW_CHAR_LIMIT = 4000


def _append_audit_only_event(current_store: Any, audit_event: dict[str, Any]) -> None:
    repository = getattr(current_store, "repository", None)
    append_audit_event = getattr(repository, "append_audit_event", None)
    if callable(append_audit_event):
        append_audit_event(audit_event)


def _json_preview(value: Any) -> dict[str, Any]:
    available = value is not None and value != {}
    if not available:
        return {
            "available": False,
            "size_bytes": 0,
            "truncated": False,
            "value": None,
        }
    serialized = json.dumps(value, default=str, ensure_ascii=False)
    size_bytes = len(serialized.encode("utf-8"))
    truncated = len(serialized) > TRACE_NODE_PREVIEW_CHAR_LIMIT
    preview = (
        f"{serialized[:TRACE_NODE_PREVIEW_CHAR_LIMIT]}..."
        if truncated
        else serialized
    )
    result: dict[str, Any] = {
        "available": True,
        "preview": preview,
        "size_bytes": size_bytes,
        "truncated": truncated,
    }
    if not truncated:
        result["value"] = value
    return result


def _trace_node_full_run_request(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "scheduled_job_id": run.get("scheduled_job_id"),
        "source_run_id": run.get("id"),
        "trigger_type": "manual_rerun",
    }


def _control_label_by_key(rerun_controls: list[Any]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for control in rerun_controls:
        if not isinstance(control, dict):
            continue
        key = control.get("key")
        if not key:
            continue
        labels[str(key)] = str(control.get("label") or key)
    return labels


def _trace_node_rerun_execution_policy(
    *,
    blocked_by: list[str],
    missing_controls: list[str],
    rerun_plan: dict[str, Any],
    rerun_supported: bool,
) -> dict[str, Any]:
    mode = "single_node_ready" if rerun_supported else "protected_preview_only"
    return {
        "allowed": rerun_supported,
        "blocking_count": len(blocked_by),
        "message": (
            "单节点复跑控制项已满足，可以进入执行确认。"
            if rerun_supported
            else (
                "该节点的单节点复跑控制项未全部满足，"
                "当前以节点快照预检和整条运行记录复跑作为安全替代。"
            )
        ),
        "missing_control_count": len(missing_controls),
        "mode": mode,
        "requires_confirmation": bool(rerun_plan.get("side_effect_policy") != "none"),
        "side_effect_policy": rerun_plan.get("side_effect_policy"),
    }


def _trace_node_rerun_next_actions(
    *,
    full_run_request: dict[str, Any],
    missing_controls: list[str],
    rerun_controls: list[Any],
    rerun_plan: dict[str, Any],
    rerun_supported: bool,
) -> list[dict[str, Any]]:
    control_labels = _control_label_by_key(rerun_controls)
    actions: list[dict[str, Any]] = []
    if rerun_plan.get("can_preview_from_snapshot"):
        actions.append(
            {
                "description": "节点 input/output/error 快照可用于排障和复制给 AI 分析。",
                "key": "inspect_node_snapshot",
                "label": "查看节点快照",
                "status": "available",
            },
        )
    if rerun_supported:
        actions.append(
            {
                "description": "所有必需控制项已满足，可进入单节点执行确认。",
                "key": "confirm_single_node_rerun",
                "label": "确认单节点复跑",
                "status": "available",
            },
        )
        return actions
    if rerun_plan.get("full_run_supported") is not False:
        actions.append(
            {
                "description": "重新执行完整作业链路，保留上下游一致性和副作用保护。",
                "key": "rerun_full_scheduled_job",
                "label": "复跑整条运行记录",
                "request": full_run_request,
                "status": "recommended",
            },
        )
    if missing_controls:
        missing_labels = [control_labels.get(key, key) for key in missing_controls]
        actions.append(
            {
                "description": f"需补齐：{'、'.join(missing_labels)}。",
                "key": "complete_single_node_controls",
                "label": "补齐单节点复跑控制项",
                "missing_controls": missing_controls,
                "status": "blocked",
            },
        )
    if rerun_plan.get("side_effect_policy") not in {None, "none"}:
        actions.append(
            {
                "description": (
                    "该节点可能产生外部请求、模型成本、本地工作区修改或业务写入，"
                    "需额外确认。"
                ),
                "key": "review_side_effect_policy",
                "label": "确认副作用策略",
                "side_effect_policy": rerun_plan.get("side_effect_policy"),
                "status": "needs_review",
            },
        )
    return actions


def _trace_node_rerun_preflight(
    *,
    node: dict[str, Any],
    run: dict[str, Any],
) -> dict[str, Any]:
    rerun_plan = node.get("rerun_plan") if isinstance(node.get("rerun_plan"), dict) else {}
    snapshot_status = node.get("snapshot_status") or rerun_plan.get("snapshot_status") or {}
    blocked_by = list(rerun_plan.get("blocked_by") or [])
    required_controls = list(rerun_plan.get("required_controls") or [])
    rerun_controls = list(rerun_plan.get("rerun_controls") or [])
    missing_controls = [
        str(control.get("key"))
        for control in rerun_controls
        if isinstance(control, dict) and control.get("satisfied") is not True and control.get("key")
    ]
    if not rerun_controls:
        missing_controls = required_controls
    rerun_supported = bool(node.get("rerun_supported"))
    full_run_request = _trace_node_full_run_request(run)
    next_actions = _trace_node_rerun_next_actions(
        full_run_request=full_run_request,
        missing_controls=missing_controls,
        rerun_controls=rerun_controls,
        rerun_plan=rerun_plan,
        rerun_supported=rerun_supported,
    )
    return {
        "blocked_by": blocked_by,
        "can_preview_from_snapshot": bool(rerun_plan.get("can_preview_from_snapshot")),
        "control_summary": rerun_plan.get("control_summary") or {},
        "debug_actions": node.get("debug_actions") or [],
        "execution_policy": _trace_node_rerun_execution_policy(
            blocked_by=blocked_by,
            missing_controls=missing_controls,
            rerun_plan=rerun_plan,
            rerun_supported=rerun_supported,
        ),
        "full_run_request": full_run_request,
        "missing_controls": missing_controls,
        "next_actions": next_actions,
        "node_id": node.get("id"),
        "preflight_status": "ready" if rerun_supported else "blocked",
        "rerun_plan": rerun_plan,
        "rerun_controls": rerun_controls,
        "rerun_supported": rerun_supported,
        "run_id": run.get("id"),
        "safe_next_action": rerun_plan.get("safe_next_action"),
        "side_effect_policy": rerun_plan.get("side_effect_policy"),
        "snapshot_preview": {
            "error": _json_preview(node.get("error")),
            "input": _json_preview(node.get("input")),
            "output": _json_preview(node.get("output")),
        },
        "snapshot_status": snapshot_status,
        "stage": node.get("stage"),
        "stage_label": node.get("stage_label"),
    }


def _trace_node_rerun_error_detail(
    *,
    node: dict[str, Any],
    run: dict[str, Any],
) -> dict[str, Any]:
    rerun_plan = node.get("rerun_plan") if isinstance(node.get("rerun_plan"), dict) else {}
    preflight = _trace_node_rerun_preflight(node=node, run=run)
    return {
        "blocked_by": rerun_plan.get("blocked_by") or [],
        "debug_actions": node.get("debug_actions") or [],
        "execution_policy": preflight.get("execution_policy"),
        "full_run_request": _trace_node_full_run_request(run),
        "next_actions": preflight.get("next_actions") or [],
        "node_id": node.get("id"),
        "preflight": preflight,
        "rerun_hint": node.get("rerun_hint"),
        "rerun_plan": rerun_plan,
        "rerun_controls": rerun_plan.get("rerun_controls") or [],
        "rerun_supported": bool(node.get("rerun_supported")),
        "run_id": run.get("id"),
        "safe_next_action": rerun_plan.get("safe_next_action"),
        "snapshot_status": node.get("snapshot_status") or rerun_plan.get("snapshot_status"),
        "stage": node.get("stage"),
        "stage_label": node.get("stage_label"),
    }


def _plugin_summary_from_log(current_store: Any, plugin_log: dict[str, Any]) -> dict[str, Any]:
    return {
        "action_id": plugin_log.get("action_id"),
        "connection_environment": (
            job_store.read_memory_dict(current_store, "plugin_connections").get(
                plugin_log.get("connection_id"),
            )
            or {}
        ).get("environment"),
        "connection_id": plugin_log.get("connection_id"),
        "error_code": plugin_log.get("error_code"),
        "error_message": plugin_log.get("error_message"),
        "invocation_log_id": plugin_log["id"],
        "latency_ms": plugin_log.get("latency_ms"),
        "request_summary": plugin_log.get("request_summary") or {},
        "response_summary": plugin_log.get("response_summary") or {},
        "status": plugin_log["status"],
    }


def _response_records_imported(plugin_summary: dict[str, Any]) -> int:
    response_summary = plugin_summary.get("response_summary") or {}
    raw_json = response_summary.get("json")
    if isinstance(raw_json, dict):
        row_count = raw_json.get("row_count")
        if isinstance(row_count, int) and row_count >= 0:
            return row_count
        for key in ("rows", "items", "records"):
            value = raw_json.get(key)
            if isinstance(value, list):
                return len(value)
    if isinstance(raw_json, list):
        return len(raw_json)
    return 0


def _collector_type(job: dict[str, Any]) -> str:
    return {
        "code_repository_inspection": "code_inspection",
        "iteration_plan_suggestion_generate": "iteration_plan_suggestion",
        "online_log_ai_analysis": "online_log_metric",
        "user_feedback_insight_extract": "user_feedback",
    }.get(str(job["job_type"]), str(job["job_type"]).removesuffix("_collect"))


def _create_trace_node_collector_run(
    current_store: Any,
    *,
    job: dict[str, Any],
    node_id: str,
    run_id: str,
    source_run_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    collector_run_id = current_store.new_id("collector_run")
    collector_type = _collector_type(job)
    collector_run = {
        "collector_type": collector_type,
        "created_at": now,
        "created_by": user["id"],
        "error_message": None,
        "finished_at": None,
        "id": collector_run_id,
        "payload_summary": {
            "scheduled_job_id": job["id"],
            "scheduled_job_run_id": run_id,
            "trace_node_rerun": {
                "node_id": node_id,
                "source_run_id": source_run_id,
            },
        },
        "product_id": job.get("product_id"),
        "records_imported": 0,
        "source_system": job["source_system"],
        "started_at": now,
        "status": "running",
        "updated_at": now,
    }
    job_store.put_memory_record(current_store, "collector_runs", collector_run)
    audit_event = record_audit_event(
        current_store,
        event_type="collector_run.created",
        actor_id=user["id"],
        subject_type="collector_run",
        subject_id=collector_run_id,
        payload={
            "collector_type": collector_type,
            "scheduled_job_id": job["id"],
            "trace_node_rerun": True,
        },
    )
    job_store.persist_record(
        current_store,
        "save_collector_run_record",
        collector_run,
        audit_event=audit_event,
    )
    return collector_run


def _complete_trace_node_collector_run(
    current_store: Any,
    *,
    collector_run: dict[str, Any],
    error_message: str | None,
    records_imported: int,
    status: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    collector_status = "succeeded" if status == "succeeded" else "failed"
    updated = {
        **collector_run,
        "error_message": error_message,
        "finished_at": now,
        "records_imported": records_imported,
        "status": collector_status,
        "updated_at": now,
    }
    job_store.put_memory_record(current_store, "collector_runs", updated)
    audit_event = record_audit_event(
        current_store,
        event_type="collector_run.updated",
        actor_id=user["id"],
        subject_type="collector_run",
        subject_id=collector_run["id"],
        payload={"records_imported": records_imported, "status": collector_status},
    )
    job_store.persist_record(
        current_store,
        "save_collector_run_record",
        updated,
        audit_event=audit_event,
    )
    return updated


def _trace_node_input_mapping(node_input: dict[str, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in node_input.items()
        if key not in {"action_id", "connection_id", "connection_index"}
    }


def _result_write_target(job: dict[str, Any]) -> str:
    mapping = job.get("plugin_output_mapping")
    if isinstance(mapping, dict) and mapping.get("write_target"):
        return str(mapping["write_target"])
    for action in job.get("result_actions") or []:
        if isinstance(action, dict) and action.get("write_target"):
            return str(action["write_target"])
    return "scheduled_job_result"


def _is_data_connection_node(node: dict[str, Any]) -> bool:
    node_id = str(node.get("id") or "")
    return node_id == "data_connection" or node_id.startswith("data_connection_")


def _is_generic_result_action_node(node: dict[str, Any]) -> bool:
    node_id = str(node.get("id") or "")
    if not (node_id == "result_action" or node_id.startswith("result_action_")):
        return False
    rerun_plan = node.get("rerun_plan") if isinstance(node.get("rerun_plan"), dict) else {}
    return rerun_plan.get("generic_result_action") is True


def _is_skill_processing_node(node: dict[str, Any]) -> bool:
    return str(node.get("id") or "") == "skill_processing"


def _source_execution_nodes(source_run: dict[str, Any]) -> dict[str, Any]:
    result_summary = (
        source_run.get("result_summary")
        if isinstance(source_run.get("result_summary"), dict)
        else {}
    )
    execution_nodes = (
        result_summary.get("execution_nodes")
        if isinstance(result_summary.get("execution_nodes"), dict)
        else {}
    )
    return execution_nodes if isinstance(execution_nodes, dict) else {}


def _source_skill_output_json(source_run: dict[str, Any]) -> dict[str, Any] | None:
    skill_processing = _source_execution_nodes(source_run).get("skill_processing")
    if not isinstance(skill_processing, dict):
        return None
    output = (
        skill_processing.get("output")
        if isinstance(skill_processing.get("output"), dict)
        else {}
    )
    processed_json = output.get("processed_json")
    return processed_json if isinstance(processed_json, dict) else None


def _source_plugin_summary(source_run: dict[str, Any]) -> dict[str, Any]:
    result_summary = (
        source_run.get("result_summary")
        if isinstance(source_run.get("result_summary"), dict)
        else {}
    )
    plugin_summary = result_summary.get("plugin")
    return plugin_summary if isinstance(plugin_summary, dict) else {}


def _source_plugin_response_json(source_run: dict[str, Any]) -> dict[str, Any] | None:
    response_summary = _source_plugin_summary(source_run).get("response_summary")
    if not isinstance(response_summary, dict):
        return None
    source_json = response_summary.get("json")
    if isinstance(source_json, dict):
        return source_json
    if isinstance(source_json, list):
        return {"items": source_json, "row_count": len(source_json)}
    return None


def _source_data_row_count(
    *,
    output_mapping: dict[str, Any],
    source_run: dict[str, Any],
    source_response_json: dict[str, Any],
) -> int:
    source_nodes = _source_execution_nodes(source_run)
    data_connection = source_nodes.get("data_connection")
    if isinstance(data_connection, dict):
        records_imported = data_connection.get("records_imported")
        if isinstance(records_imported, int) and records_imported >= 0:
            return records_imported
    return records_imported_from_mapping(
        {"json": source_response_json},
        {"records_imported_path": output_mapping.get("records_imported_path")},
    )


def _ai_output_mapping_for_job(current_store: Any, job: dict[str, Any]) -> dict[str, Any]:
    output_mapping = resolve_job_plugin_output_mapping(current_store, job)
    job_type = str(job.get("job_type") or "")
    if job_type == "online_log_ai_analysis":
        return {
            "anomalies_path": "$.anomalies",
            "records_imported_path": "$.row_count",
            "summary_path": "$.summary",
            "write_target": "scheduled_job_result",
            **output_mapping,
        }
    if job_type == "code_repository_inspection":
        return {
            "branch_path": "$.branch",
            "commit_sha_path": "$.commit_sha",
            "findings_path": "$.findings",
            "repository_id_path": "$.repository_id",
            "risk_level_path": "$.risk_level",
            "summary_path": "$.summary",
            "write_target": "code_inspection_reports",
            **output_mapping,
        }
    return {
        "insights_path": "$.insights",
        "records_imported_path": "$.row_count",
        "write_target": "user_feedback_insights",
        **output_mapping,
    }


def _skill_processing_output_projection(
    *,
    job: dict[str, Any],
    output_json: dict[str, Any],
    output_mapping: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    job_type = str(job.get("job_type") or "")
    if job_type == "online_log_ai_analysis":
        anomalies = json_path_value(
            output_json,
            str(output_mapping.get("anomalies_path") or "$.anomalies"),
        )
        if anomalies is None:
            anomalies = []
        if not isinstance(anomalies, list):
            raise api_error(400, "PLUGIN_RESULT_INVALID", "Mapped anomalies result must be a list")
        output = {
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "processed_json": output_json,
            "summary": output_json.get("summary") if isinstance(output_json, dict) else None,
        }
        return output, max(
            len(anomalies),
            inferred_output_record_count(output_json, output_mapping),
        )
    if job_type == "code_repository_inspection":
        findings = json_path_value(
            output_json,
            str(output_mapping.get("findings_path") or "$.findings"),
        )
        if findings is None:
            findings = []
        if not isinstance(findings, list):
            raise api_error(400, "PLUGIN_RESULT_INVALID", "Mapped findings result must be a list")
        output = {
            "finding_count": len(findings),
            "processed_json": output_json,
            "risk_level": output_json.get("risk_level") if isinstance(output_json, dict) else None,
            "summary": output_json.get("summary") if isinstance(output_json, dict) else None,
        }
        return output, max(
            len(findings),
            inferred_output_record_count(output_json, output_mapping),
        )
    insights = json_path_value(
        output_json,
        str(output_mapping.get("insights_path") or "$.insights"),
    )
    if insights is None:
        insights = []
    if not isinstance(insights, list):
        raise api_error(400, "PLUGIN_RESULT_INVALID", "Mapped insights result must be a list")
    output = {
        "candidate_count": len(insights),
        "insights": insights,
        "processed_json": output_json,
    }
    return output, max(
        len(insights),
        inferred_output_record_count(output_json, output_mapping),
    )


def _skill_processing_input_projection(
    *,
    ai_processing: dict[str, Any],
    job: dict[str, Any],
    output_mapping: dict[str, Any],
    source_row_count: int,
) -> dict[str, Any]:
    job_type = str(job.get("job_type") or "")
    if job_type == "online_log_ai_analysis":
        return {
            "anomalies_path": str(output_mapping.get("anomalies_path") or "$.anomalies"),
            "knowledge_references": ai_processing.get("knowledge_references") or [],
            "source_row_count": source_row_count,
        }
    if job_type == "code_repository_inspection":
        return {
            "findings_path": str(output_mapping.get("findings_path") or "$.findings"),
            "knowledge_references": ai_processing.get("knowledge_references") or [],
            "source_finding_count": source_row_count,
        }
    return {
        "insights_path": str(output_mapping.get("insights_path") or "$.insights"),
        "knowledge_references": ai_processing.get("knowledge_references") or [],
        "source_row_count": source_row_count,
    }


def _generic_result_action_config(
    job: dict[str, Any],
    node: dict[str, Any],
) -> list[dict[str, Any]]:
    configured_actions = [
        item for item in job.get("result_actions") or [] if isinstance(item, dict)
    ]
    if not configured_actions:
        return []
    node_input = node.get("input") if isinstance(node.get("input"), dict) else {}
    action_index = node_input.get("action_index")
    if isinstance(action_index, int) and action_index > 0:
        selected = configured_actions[action_index - 1 : action_index]
        return selected
    return configured_actions[:1]


def _scheduled_job_trace_node_context(
    *,
    current_store: Any,
    node_id: str,
    run_id: str,
    user: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    require_scheduled_job_runner(user)
    job_store.sync_scheduled_job_store(current_store)
    job_store.sync_scheduled_job_run_store(current_store)
    run = job_store.read_memory_dict(current_store, "scheduled_job_runs").get(run_id)
    if run is None:
        raise api_error(404, "NOT_FOUND", "Scheduled job run not found")
    job = job_store.read_memory_dict(current_store, "scheduled_jobs").get(
        run.get("scheduled_job_id"),
    )
    if job is None:
        raise api_error(404, "NOT_FOUND", "Scheduled job not found")
    if not scheduled_job_matches_product_scope(job, user):
        raise api_error(404, "NOT_FOUND", "Scheduled job run not found")
    projected_run = public_scheduled_job_run(run, current_store=current_store)
    result_summary = projected_run.get("result_summary")
    trace_graph = result_summary.get("trace_graph") if isinstance(result_summary, dict) else None
    nodes = trace_graph.get("nodes") if isinstance(trace_graph, dict) else []
    if not isinstance(nodes, list):
        nodes = []
    node = next(
        (
            item
            for item in nodes
            if isinstance(item, dict) and str(item.get("id") or "") == str(node_id)
        ),
        None,
    )
    if node is None:
        raise api_error(
            404,
            "TRACE_NODE_NOT_FOUND",
            "Trace node not found for scheduled job run",
        )
    return job, run, node


def scheduled_job_trace_node_rerun_preview_response(
    *,
    current_store: Any,
    node_id: str,
    run_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _job, run, node = _scheduled_job_trace_node_context(
        current_store=current_store,
        node_id=node_id,
        run_id=run_id,
        user=user,
    )
    return _trace_node_rerun_preflight(node=node, run=run)


def _rerun_data_connection_trace_node(
    *,
    current_store: Any,
    job: dict[str, Any],
    node: dict[str, Any],
    source_run: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    node_input = node.get("input") if isinstance(node.get("input"), dict) else {}
    action_id = str(node_input.get("action_id") or job.get("plugin_action_id") or "")
    connection_id = node_input.get("connection_id") or job.get("plugin_connection_id")
    if not action_id:
        raise api_error(
            409,
            "TRACE_NODE_RERUN_PROTECTED",
            "Trace node rerun is protected because action snapshot is missing",
            _trace_node_rerun_error_detail(node=node, run=source_run),
        )

    resolved_plugin_input_mapping = _trace_node_input_mapping(node_input)
    resolved_plugin_snapshot = resolve_plugin_snapshot(
        current_store,
        action_id=action_id,
        connection_id=str(connection_id) if connection_id else None,
    )
    now = datetime.now(UTC).isoformat()
    run_id = current_store.new_id("scheduled_job_run")
    trace_node_rerun = {
        "downstream_strategy": "not_executed",
        "mode": "single_node_data_connection",
        "source_node_id": node.get("id"),
        "source_run_id": source_run["id"],
    }
    config_snapshot = {
        **job_store.snapshot(current_store, job),
        "trace_node_rerun": trace_node_rerun,
    }
    run = {
        "collector_run_id": None,
        "config_snapshot": config_snapshot,
        "created_at": now,
        "error_code": None,
        "error_message": None,
        "finished_at": None,
        "id": run_id,
        "plugin_invocation_log_id": None,
        "records_imported": 0,
        "resolved_agent_snapshot": source_run.get("resolved_agent_snapshot") or {},
        "resolved_plugin_snapshot": resolved_plugin_snapshot,
        "resolved_prompt_snapshot": source_run.get("resolved_prompt_snapshot") or {},
        "resolved_skill_snapshots": source_run.get("resolved_skill_snapshots") or [],
        "result_summary": {
            "message": "Trace DAG 数据连接节点单节点复跑执行中",
            "trace_node_rerun": trace_node_rerun,
        },
        "scheduled_for": now,
        "scheduled_job_id": job["id"],
        "source_run_id": source_run["id"],
        "started_at": now,
        "status": "running",
        "tool_policy_snapshot": source_run.get("tool_policy_snapshot") or {},
        "trigger_type": "manual_rerun",
        "updated_at": now,
    }
    job_store.put_memory_record(current_store, "scheduled_job_runs", run)
    collector_run = _create_trace_node_collector_run(
        current_store,
        job=job,
        node_id=str(node.get("id") or ""),
        run_id=run_id,
        source_run_id=source_run["id"],
        user=user,
    )
    run["collector_run_id"] = collector_run["id"]
    job_store.persist_record(current_store, "save_scheduled_job_run_record", run)

    job_config = job.get("config_json") or {}
    plugin_summary: dict[str, Any] | None = None
    records_imported = 0
    try:
        plugin_log = invoke_plugin_action_response(
            action_id=action_id,
            connection_id=str(connection_id) if connection_id else None,
            current_store=current_store,
            input_payload={
                "branch": resolved_plugin_input_mapping.get("branch") or job_config.get("branch"),
                "config": job_config,
                "input_mapping": resolved_plugin_input_mapping,
                "job_id": job["id"],
                "product_id": job.get("product_id"),
                "repository_id": (
                    resolved_plugin_input_mapping.get("repository_id")
                    or job_config.get("repository_id")
                ),
                "timezone": job.get("timezone") or "UTC",
                "trace_node_rerun": trace_node_rerun,
            },
            raise_on_failed=False,
            scheduled_job_id=job["id"],
            scheduled_job_run_id=run_id,
            trigger_type="manual_rerun",
            user=scheduled_job_plugin_invocation_user(user),
        )
        plugin_summary = _plugin_summary_from_log(current_store, plugin_log)
        records_imported = _response_records_imported(plugin_summary)
        status = "succeeded" if plugin_summary.get("status") == "succeeded" else "failed"
        error_code = None if status == "succeeded" else plugin_summary.get("error_code")
        error_message = None if status == "succeeded" else plugin_summary.get("error_message")
    except Exception as exc:
        status = "failed"
        detail = getattr(exc, "detail", None)
        if isinstance(detail, dict):
            error_code = str(detail.get("code") or exc.__class__.__name__)
            error_message = str(detail.get("message") or str(exc))
        else:
            error_code = exc.__class__.__name__
            error_message = str(exc)

    finished_at = datetime.now(UTC).isoformat()
    data_connection_node = (
        JobExecutionEngine.data_connection_execution_node(
            job=job,
            plugin_summary=plugin_summary,
            records_imported=records_imported,
            resolved_plugin_input_mapping=resolved_plugin_input_mapping,
        )
        if plugin_summary is not None
        else {
            "action_id": action_id,
            "connection_id": connection_id,
            "error_code": error_code,
            "error_message": error_message,
            "input_mapping": resolved_plugin_input_mapping,
            "label": "数据连接获取内容",
            "records_imported": 0,
            "status": "failed",
        }
    )
    result_summary = {
        "execution_nodes": {
            "data_connection": data_connection_node,
            "result_action": {
                "label": "结果动作反馈内容",
                "note": "单节点复跑仅重新执行数据连接，下游动作未执行。",
                "records_imported": 0,
                "status": "not_run",
                "write_target": _result_write_target(job),
            },
            "skill_processing": {
                "label": "Skill 处理后内容",
                "model_gateway_called": False,
                "note": "单节点复跑仅重新执行数据连接，下游 AI 处理未执行。",
                "processing_mode": "trace_node_data_connection_rerun",
                "skill_ids": list(job.get("skill_ids") or []),
                "status": "not_run",
            },
        },
        "job_type": job.get("job_type"),
        "message": (
            "Trace DAG 数据连接节点单节点复跑完成"
            if status == "succeeded"
            else "Trace DAG 数据连接节点单节点复跑失败"
        ),
        "plugin": plugin_summary,
        "records_imported": records_imported,
        "trace_node_rerun": {
            **trace_node_rerun,
            "completed_at": finished_at,
            "status": status,
        },
        "write_target": _result_write_target(job),
    }
    run = {
        **run,
        "error_code": error_code,
        "error_message": error_message,
        "finished_at": finished_at,
        "plugin_invocation_log_id": (
            plugin_summary.get("invocation_log_id") if plugin_summary is not None else None
        ),
        "records_imported": records_imported,
        "result_summary": result_summary,
        "status": status,
        "updated_at": finished_at,
    }
    job_store.put_memory_record(current_store, "scheduled_job_runs", run)
    _complete_trace_node_collector_run(
        current_store,
        collector_run=collector_run,
        error_message=error_message,
        records_imported=records_imported,
        status=status,
        user=user,
    )
    audit_event = record_audit_event(
        current_store,
        event_type=f"scheduled_job_run.{status}",
        actor_id=user["id"],
        subject_type="scheduled_job_run",
        subject_id=run_id,
        payload={
            **scheduled_job_run_audit_payload(job=job, run=run),
            "trace_node_rerun": trace_node_rerun,
        },
    )
    job_store.persist_record(
        current_store,
        "save_scheduled_job_run_record",
        run,
        audit_event=audit_event,
    )
    return public_scheduled_job_run(run, current_store=current_store)


def _rerun_skill_processing_trace_node(
    *,
    current_store: Any,
    job: dict[str, Any],
    node: dict[str, Any],
    source_run: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    source_response_json = _source_plugin_response_json(source_run)
    if source_response_json is None:
        raise api_error(
            409,
            "TRACE_NODE_RERUN_PROTECTED",
            "Trace node rerun is protected because source data connection response snapshot is missing",  # noqa: E501
            _trace_node_rerun_error_detail(node=node, run=source_run),
        )
    output_mapping = _ai_output_mapping_for_job(current_store, job)
    source_row_count = _source_data_row_count(
        output_mapping=output_mapping,
        source_response_json=source_response_json,
        source_run=source_run,
    )
    now = datetime.now(UTC).isoformat()
    run_id = current_store.new_id("scheduled_job_run")
    trace_node_rerun = {
        "downstream_strategy": "result_actions_not_executed",
        "mode": "single_node_skill_processing",
        "source_node_id": node.get("id"),
        "source_run_id": source_run["id"],
        "upstream_strategy": "source_data_connection_snapshot_reused",
    }
    run = {
        "collector_run_id": None,
        "config_snapshot": {
            **job_store.snapshot(current_store, job),
            "trace_node_rerun": trace_node_rerun,
        },
        "created_at": now,
        "error_code": None,
        "error_message": None,
        "finished_at": None,
        "id": run_id,
        "plugin_invocation_log_id": None,
        "records_imported": 0,
        "resolved_agent_snapshot": source_run.get("resolved_agent_snapshot") or {},
        "resolved_plugin_snapshot": source_run.get("resolved_plugin_snapshot") or {},
        "resolved_prompt_snapshot": source_run.get("resolved_prompt_snapshot") or {},
        "resolved_skill_snapshots": source_run.get("resolved_skill_snapshots") or [],
        "result_summary": {
            "message": "Trace DAG AI 处理节点单节点复跑执行中",
            "trace_node_rerun": trace_node_rerun,
        },
        "scheduled_for": now,
        "scheduled_job_id": job["id"],
        "source_run_id": source_run["id"],
        "started_at": now,
        "status": "running",
        "tool_policy_snapshot": source_run.get("tool_policy_snapshot") or {},
        "trigger_type": "manual_rerun",
        "updated_at": now,
    }
    job_store.put_memory_record(current_store, "scheduled_job_runs", run)
    collector_run = _create_trace_node_collector_run(
        current_store,
        job=job,
        node_id=str(node.get("id") or ""),
        run_id=run_id,
        source_run_id=source_run["id"],
        user=user,
    )
    run["collector_run_id"] = collector_run["id"]
    job_store.persist_record(current_store, "save_scheduled_job_run_record", run)

    status = "succeeded"
    error_code = None
    error_message = None
    records_imported = 0
    skill_processing_node: dict[str, Any]
    try:
        ai_processing = run_scheduled_job_ai_processing(
            current_store,
            job=job,
            output_mapping=output_mapping,
            source_response_json=source_response_json,
            source_row_count=source_row_count,
            user=user,
        )
        projected_output, records_imported = _skill_processing_output_projection(
            job=job,
            output_json=ai_processing["output_json"],
            output_mapping=output_mapping,
        )
        skill_processing_node = {
            "input": _skill_processing_input_projection(
                ai_processing=ai_processing,
                job=job,
                output_mapping=output_mapping,
                source_row_count=source_row_count,
            ),
            "label": "Skill 处理后内容",
            "model": ai_processing.get("model"),
            "model_gateway_called": True,
            "model_gateway_config_id": ai_processing.get("model_gateway_config_id"),
            "model_log_id": ai_processing.get("model_log_id"),
            "note": "单节点复跑复用来源数据连接响应快照，并重新调用平台 AI 大模型处理。",
            "output": projected_output,
            "processing_mode": "trace_node_model_gateway_json_transform",
            "provider": ai_processing.get("provider"),
            "skill_codes": skill_codes_for_job(current_store, job),
            "skill_ids": list(job.get("skill_ids") or []),
            "status": ai_processing.get("status") or "succeeded",
            "tokens": ai_processing.get("tokens") or {},
        }
    except Exception as exc:
        status = "failed"
        detail = getattr(exc, "detail", None)
        if isinstance(detail, dict):
            error_code = str(detail.get("code") or exc.__class__.__name__)
            error_message = str(detail.get("message") or str(exc))
            model_gateway_called = bool(detail.get("model_gateway_called"))
            model_gateway_config_id = detail.get("model_gateway_config_id") or job.get(
                "model_gateway_config_id",
            )
            model_log_id = detail.get("model_log_id")
        else:
            error_code = exc.__class__.__name__
            error_message = str(exc)
            model_gateway_called = False
            model_gateway_config_id = job.get("model_gateway_config_id")
            model_log_id = None
        skill_processing_node = {
            "error_code": error_code,
            "error_message": error_message,
            "input": {
                "source_row_count": source_row_count,
            },
            "label": "Skill 处理后内容",
            "model_gateway_called": model_gateway_called,
            "model_gateway_config_id": model_gateway_config_id,
            "model_log_id": model_log_id,
            "note": "AI 处理节点单节点复跑失败，下游动作未执行。",
            "processing_mode": "trace_node_model_gateway_json_transform",
            "skill_codes": skill_codes_for_job(current_store, job),
            "skill_ids": list(job.get("skill_ids") or []),
            "status": "failed",
        }

    finished_at = datetime.now(UTC).isoformat()
    source_nodes = _source_execution_nodes(source_run)
    result_summary = {
        "execution_nodes": {
            "data_connection": {
                "label": "数据连接获取内容",
                "note": "单节点复跑复用来源运行数据连接响应快照，未重新请求数据源。",
                "records_imported": source_row_count,
                "source_run_id": source_run["id"],
                "source_snapshot_available": True,
                "status": "reused_snapshot",
            },
            "result_action": {
                "label": "结果动作反馈内容",
                "note": "单节点复跑仅重新执行 AI 处理，下游动作未执行。",
                "records_imported": 0,
                "status": "not_run",
                "write_target": _result_write_target(job),
            },
            "result_actions": [],
            "skill_processing": skill_processing_node,
        },
        "job_type": job.get("job_type"),
        "message": (
            "Trace DAG AI 处理节点单节点复跑完成"
            if status == "succeeded"
            else "Trace DAG AI 处理节点单节点复跑失败"
        ),
        "plugin": _source_plugin_summary(source_run),
        "processing": {
            "model_gateway_called": bool(skill_processing_node.get("model_gateway_called")),
            "model_log_id": skill_processing_node.get("model_log_id"),
            "source_data_connection_snapshot_reused": "data_connection" in source_nodes,
        },
        "records_imported": records_imported,
        "trace_node_rerun": {
            **trace_node_rerun,
            "completed_at": finished_at,
            "status": status,
        },
        "write_target": _result_write_target(job),
    }
    run = {
        **run,
        "error_code": error_code,
        "error_message": error_message,
        "finished_at": finished_at,
        "records_imported": records_imported,
        "result_summary": result_summary,
        "status": status,
        "updated_at": finished_at,
    }
    job_store.put_memory_record(current_store, "scheduled_job_runs", run)
    _complete_trace_node_collector_run(
        current_store,
        collector_run=collector_run,
        error_message=error_message,
        records_imported=records_imported,
        status=status,
        user=user,
    )
    audit_event = record_audit_event(
        current_store,
        event_type=f"scheduled_job_run.{status}",
        actor_id=user["id"],
        subject_type="scheduled_job_run",
        subject_id=run_id,
        payload={
            **scheduled_job_run_audit_payload(job=job, run=run),
            "trace_node_rerun": trace_node_rerun,
        },
    )
    job_store.persist_record(
        current_store,
        "save_scheduled_job_run_record",
        run,
        audit_event=audit_event,
    )
    return public_scheduled_job_run(run, current_store=current_store)


def _rerun_generic_result_action_trace_node(
    *,
    current_store: Any,
    job: dict[str, Any],
    node: dict[str, Any],
    source_run: dict[str, Any],
    user: dict[str, Any],
) -> dict[str, Any]:
    source_output_json = _source_skill_output_json(source_run)
    if source_output_json is None:
        raise api_error(
            409,
            "TRACE_NODE_RERUN_PROTECTED",
            "Trace node rerun is protected because source AI output snapshot is missing",
            _trace_node_rerun_error_detail(node=node, run=source_run),
        )
    output_mapping = resolve_job_plugin_output_mapping(current_store, job)
    result_action_config = _generic_result_action_config(job, node)
    now = datetime.now(UTC).isoformat()
    run_id = current_store.new_id("scheduled_job_run")
    trace_node_rerun = {
        "mode": "single_node_result_action",
        "source_node_id": node.get("id"),
        "source_run_id": source_run["id"],
        "upstream_strategy": "source_ai_output_snapshot_reused",
    }
    run = {
        "collector_run_id": None,
        "config_snapshot": {
            **job_store.snapshot(current_store, job),
            "trace_node_rerun": trace_node_rerun,
        },
        "created_at": now,
        "error_code": None,
        "error_message": None,
        "finished_at": None,
        "id": run_id,
        "plugin_invocation_log_id": None,
        "records_imported": 0,
        "resolved_agent_snapshot": source_run.get("resolved_agent_snapshot") or {},
        "resolved_plugin_snapshot": source_run.get("resolved_plugin_snapshot") or {},
        "resolved_prompt_snapshot": source_run.get("resolved_prompt_snapshot") or {},
        "resolved_skill_snapshots": source_run.get("resolved_skill_snapshots") or [],
        "result_summary": {
            "message": "Trace DAG 结果动作节点单节点复跑执行中",
            "trace_node_rerun": trace_node_rerun,
        },
        "scheduled_for": now,
        "scheduled_job_id": job["id"],
        "source_run_id": source_run["id"],
        "started_at": now,
        "status": "running",
        "tool_policy_snapshot": source_run.get("tool_policy_snapshot") or {},
        "trigger_type": "manual_rerun",
        "updated_at": now,
    }
    job_store.put_memory_record(current_store, "scheduled_job_runs", run)
    collector_run = _create_trace_node_collector_run(
        current_store,
        job=job,
        node_id=str(node.get("id") or ""),
        run_id=run_id,
        source_run_id=source_run["id"],
        user=user,
    )
    run["collector_run_id"] = collector_run["id"]
    job_store.persist_record(current_store, "save_scheduled_job_run_record", run)

    status = "succeeded"
    error_code = None
    error_message = None
    result_actions: list[dict[str, Any]] = []
    records_imported = 0
    try:
        result_actions, records_imported = execute_generic_result_actions(
            job=job,
            output_json=source_output_json,
            output_mapping=output_mapping,
            result_actions=result_action_config,
        )
        if any(action.get("status") == "failed" for action in result_actions):
            status = "failed"
            first_failed = next(
                action for action in result_actions if action.get("status") == "failed"
            )
            error_code = first_failed.get("error_code") or "RESULT_ACTION_FAILED"
            error_message = first_failed.get("error_message") or "Result action failed"
    except Exception as exc:
        status = "failed"
        detail = getattr(exc, "detail", None)
        if isinstance(detail, dict):
            error_code = str(detail.get("code") or exc.__class__.__name__)
            error_message = str(detail.get("message") or str(exc))
        else:
            error_code = exc.__class__.__name__
            error_message = str(exc)

    finished_at = datetime.now(UTC).isoformat()
    source_nodes = _source_execution_nodes(source_run)
    source_skill_processing = (
        source_nodes.get("skill_processing")
        if isinstance(source_nodes.get("skill_processing"), dict)
        else {}
    )
    primary_result_action = result_actions[0] if result_actions else {
        "error_code": error_code,
        "error_message": error_message,
        "feedback": {"error_code": error_code, "error_message": error_message},
        "label": "结果动作反馈内容",
        "records_imported": 0,
        "status": "failed",
        "write_target": node.get("write_target") or "scheduled_job_result",
    }
    result_summary = {
        "execution_nodes": {
            "data_connection": {
                "label": "数据连接获取内容",
                "note": "单节点复跑仅执行结果动作，数据连接未重新执行。",
                "records_imported": 0,
                "source_run_id": source_run["id"],
                "source_snapshot_available": "data_connection" in source_nodes,
                "status": "not_run",
            },
            "result_action": primary_result_action,
            "result_actions": result_actions,
            "skill_processing": {
                "label": "Skill 处理后内容",
                "model_gateway_called": False,
                "model_log_id": source_skill_processing.get("model_log_id"),
                "note": "单节点复跑复用来源运行 AI 输出快照，未重新调用大模型。",
                "output": {
                    "processed_json": source_output_json,
                    "source_run_id": source_run["id"],
                },
                "processing_mode": "source_ai_output_snapshot_reused",
                "skill_ids": list(job.get("skill_ids") or []),
                "status": "reused_snapshot",
            },
        },
        "job_type": job.get("job_type"),
        "message": (
            "Trace DAG 结果动作节点单节点复跑完成"
            if status == "succeeded"
            else "Trace DAG 结果动作节点单节点复跑失败"
        ),
        "records_imported": records_imported,
        "trace_node_rerun": {
            **trace_node_rerun,
            "completed_at": finished_at,
            "status": status,
        },
        "write_target": primary_result_action.get("write_target"),
        "write_targets": [action.get("write_target") for action in result_actions],
    }
    run = {
        **run,
        "error_code": error_code,
        "error_message": error_message,
        "finished_at": finished_at,
        "records_imported": records_imported,
        "result_summary": result_summary,
        "status": status,
        "updated_at": finished_at,
    }
    job_store.put_memory_record(current_store, "scheduled_job_runs", run)
    _complete_trace_node_collector_run(
        current_store,
        collector_run=collector_run,
        error_message=error_message,
        records_imported=records_imported,
        status=status,
        user=user,
    )
    audit_event = record_audit_event(
        current_store,
        event_type=f"scheduled_job_run.{status}",
        actor_id=user["id"],
        subject_type="scheduled_job_run",
        subject_id=run_id,
        payload={
            **scheduled_job_run_audit_payload(job=job, run=run),
            "trace_node_rerun": trace_node_rerun,
        },
    )
    job_store.persist_record(
        current_store,
        "save_scheduled_job_run_record",
        run,
        audit_event=audit_event,
    )
    return public_scheduled_job_run(run, current_store=current_store)


def rerun_scheduled_job_trace_node_response(
    *,
    current_store: Any,
    node_id: str,
    run_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    job, run, node = _scheduled_job_trace_node_context(
        current_store=current_store,
        node_id=node_id,
        run_id=run_id,
        user=user,
    )
    rerun_plan = node.get("rerun_plan") if isinstance(node.get("rerun_plan"), dict) else {}
    if _is_data_connection_node(node) and node.get("rerun_supported") is True:
        return _rerun_data_connection_trace_node(
            current_store=current_store,
            job=job,
            node=node,
            source_run=run,
            user=user,
        )
    if _is_skill_processing_node(node) and node.get("rerun_supported") is True:
        return _rerun_skill_processing_trace_node(
            current_store=current_store,
            job=job,
            node=node,
            source_run=run,
            user=user,
        )
    if _is_generic_result_action_node(node) and node.get("rerun_supported") is True:
        return _rerun_generic_result_action_trace_node(
            current_store=current_store,
            job=job,
            node=node,
            source_run=run,
            user=user,
        )
    audit_event = record_audit_event(
        current_store,
        event_type="scheduled_job_run.trace_node_rerun_blocked",
        actor_id=user["id"],
        subject_type="scheduled_job_run",
        subject_id=run_id,
        payload={
            "blocked_by": rerun_plan.get("blocked_by") or [],
            "node_id": node.get("id"),
            "rerun_supported": bool(node.get("rerun_supported")),
            "safe_next_action": rerun_plan.get("safe_next_action"),
            "scheduled_job_id": run.get("scheduled_job_id"),
            "stage": node.get("stage"),
        },
    )
    _append_audit_only_event(current_store, audit_event)
    raise api_error(
        409,
        "TRACE_NODE_RERUN_PROTECTED",
        "Trace node rerun is protected until node snapshots, idempotency, and side-effect controls are satisfied",  # noqa: E501
        _trace_node_rerun_error_detail(node=node, run=run),
    )
