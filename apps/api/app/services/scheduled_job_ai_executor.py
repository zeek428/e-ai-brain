from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.services.ai_executor_runner_constants import (
    AI_EXECUTOR_LOCAL_RUNNER_TYPES,
    AI_EXECUTOR_TYPES,
    SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID,
    SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
)
from app.services.ai_executor_runner_task_context import _runner_node_from_task
from app.services.ai_executor_runners import create_ai_executor_task, find_available_runner
from app.services.operational_records import record_audit_event
from app.services.scheduled_job_ai_processing import (
    scheduled_job_ai_messages,
    scheduled_job_knowledge_references,
    skill_codes_for_job,
    validate_skill_output_json_contract,
    validate_skill_output_mapping_contract,
)
from app.services.scheduled_job_execution_engine import (
    ScheduledJobExecutionEngine as JobExecutionEngine,
)
from app.services.scheduled_job_result_actions import (
    execute_generic_result_actions,
    inferred_output_record_count,
)
from app.services.scheduled_job_runtime import exception_error_code_and_message
from app.services.scheduled_job_store import persist_record, put_memory_record, read_memory_dict

AI_EXECUTOR_CONFIG_KEY = "ai_executor"
AI_EXECUTOR_STAGE_MARKER = "scheduled_job_ai_execution"
DEFAULT_AI_EXECUTOR_CONFIG = {
    "executor_type": SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
    "runner_id": SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID,
    "runner_label": "系统默认执行器",
    "workspace_root": "model-gateway://scheduled-job",
}
RUNNER_ACTIVE_STATUSES = {"claimed", "queued", "running"}
RUNNER_FAILED_STATUSES = {"cancelled", "dead_letter", "failed", "timed_out"}


def _payload_config_json(payload_or_job: Any) -> dict[str, Any]:
    raw_config = (
        payload_or_job.get("config_json")
        if isinstance(payload_or_job, dict)
        else getattr(payload_or_job, "config_json", None)
    )
    return dict(raw_config) if isinstance(raw_config, dict) else {}


def scheduled_job_ai_executor_config(payload_or_job: Any) -> dict[str, Any]:
    config_json = _payload_config_json(payload_or_job)
    raw_config = config_json.get(AI_EXECUTOR_CONFIG_KEY)
    config = dict(raw_config) if isinstance(raw_config, dict) else {}
    executor_type = str(config.get("executor_type") or SYSTEM_DEFAULT_AI_EXECUTOR_TYPE).lower()
    runner_id = str(config.get("runner_id") or "").strip()
    if executor_type == SYSTEM_DEFAULT_AI_EXECUTOR_TYPE and not runner_id:
        runner_id = SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID
    workspace_root = str(config.get("workspace_root") or "").strip()
    if executor_type == SYSTEM_DEFAULT_AI_EXECUTOR_TYPE and not workspace_root:
        workspace_root = str(DEFAULT_AI_EXECUTOR_CONFIG["workspace_root"])
    return {
        **config,
        "executor_type": executor_type,
        "runner_id": runner_id or None,
        "workspace_root": workspace_root,
    }


def scheduled_job_uses_local_ai_executor(payload_or_job: Any) -> bool:
    config = scheduled_job_ai_executor_config(payload_or_job)
    return str(config.get("executor_type") or "") in AI_EXECUTOR_LOCAL_RUNNER_TYPES


def scheduled_job_ai_executor_requires_model_gateway(payload_or_job: Any) -> bool:
    return not scheduled_job_uses_local_ai_executor(payload_or_job)


def scheduled_job_config_with_ai_executor_defaults(
    config_json: dict[str, Any],
    *,
    ai_processing_job: bool,
) -> dict[str, Any]:
    if not ai_processing_job:
        return dict(config_json)
    config = dict(config_json)
    raw_ai_executor = config.get(AI_EXECUTOR_CONFIG_KEY)
    if not isinstance(raw_ai_executor, dict):
        config[AI_EXECUTOR_CONFIG_KEY] = dict(DEFAULT_AI_EXECUTOR_CONFIG)
        return config
    normalized = scheduled_job_ai_executor_config({"config_json": config})
    if normalized["executor_type"] == SYSTEM_DEFAULT_AI_EXECUTOR_TYPE:
        normalized.setdefault("runner_label", "系统默认执行器")
    config[AI_EXECUTOR_CONFIG_KEY] = normalized
    return config


def validate_scheduled_job_ai_executor_config(
    current_store: Any,
    payload_or_job: Any,
    *,
    ai_processing_job: bool,
) -> dict[str, Any]:
    config = scheduled_job_ai_executor_config(payload_or_job)
    if not ai_processing_job:
        return config
    executor_type = str(config.get("executor_type") or "")
    if executor_type not in AI_EXECUTOR_TYPES:
        raise api_error(400, "AI_EXECUTOR_TYPE_UNSUPPORTED", "Unsupported AI executor type")
    runner_id = config.get("runner_id")
    if executor_type == SYSTEM_DEFAULT_AI_EXECUTOR_TYPE:
        if runner_id not in {None, "", SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID}:
            raise api_error(
                400,
                "AI_EXECUTOR_RUNNER_UNAVAILABLE",
                "System default AI executor must use the system default runner",
            )
        return {
            **config,
            "runner_id": SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID,
            "workspace_root": config.get("workspace_root")
            or DEFAULT_AI_EXECUTOR_CONFIG["workspace_root"],
        }
    if not runner_id:
        raise api_error(400, "AI_EXECUTOR_RUNNER_REQUIRED", "AI executor runner is required")
    workspace_root = str(config.get("workspace_root") or "").strip()
    if not workspace_root:
        raise api_error(
            400,
            "AI_EXECUTOR_WORKSPACE_REQUIRED",
            "AI executor workspace_root is required",
        )
    find_available_runner(
        current_store,
        executor_type=executor_type,
        runner_id=str(runner_id),
        workspace_root=workspace_root,
    )
    return {**config, "runner_id": str(runner_id), "workspace_root": workspace_root}


def system_default_runner_node_from_ai_processing(
    ai_processing: dict[str, Any],
    *,
    job: dict[str, Any],
) -> dict[str, Any] | None:
    config = scheduled_job_ai_executor_config(job)
    if str(config.get("executor_type")) != SYSTEM_DEFAULT_AI_EXECUTOR_TYPE:
        return None
    return {
        "executor_type": SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
        "finished_at": datetime.now(UTC).isoformat(),
        "label": "AI 执行器执行内容",
        "model_gateway_called": True,
        "model_gateway_log_id": ai_processing.get("model_log_id"),
        "result_json": ai_processing.get("output_json") or {},
        "runner_id": SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID,
        "runner_task_id": None,
        "status": ai_processing.get("status") or "succeeded",
        "workspace_root": config.get("workspace_root")
        or DEFAULT_AI_EXECUTOR_CONFIG["workspace_root"],
    }


def _scheduled_job_ai_instruction(
    *,
    messages: list[dict[str, str]],
    output_schema: dict[str, Any],
) -> str:
    payload = {
        "messages": messages,
        "output_schema": output_schema,
        "return_contract": (
            "只返回一个 JSON 对象，不要返回 Markdown。该 JSON 会作为定时作业 AI 处理结果，"
            "后端会继续执行结果动作。"
        ),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def dispatch_scheduled_job_ai_executor_processing(
    current_store: Any,
    *,
    job: dict[str, Any],
    output_mapping: dict[str, Any],
    plugin_summary: dict[str, Any],
    resolved_plugin_input_mapping: dict[str, Any],
    run_id: str,
    source_response_json: dict[str, Any],
    source_row_count: int,
    user: dict[str, Any],
) -> dict[str, Any]:
    config = validate_scheduled_job_ai_executor_config(
        current_store,
        job,
        ai_processing_job=True,
    )
    output_schema = validate_skill_output_mapping_contract(
        current_store,
        job=job,
        output_mapping=output_mapping,
    )
    knowledge_references = scheduled_job_knowledge_references(
        current_store,
        job=job,
        user=user,
    )
    messages = scheduled_job_ai_messages(
        current_store,
        job=job,
        knowledge_references=knowledge_references,
        output_mapping=output_mapping,
        source_response_json=source_response_json,
        source_row_count=source_row_count,
    )
    executor_type = str(config["executor_type"])
    runner_id = str(config["runner_id"])
    workspace_root = str(config.get("workspace_root") or "")
    runner = find_available_runner(
        current_store,
        executor_type=executor_type,
        runner_id=runner_id,
        workspace_root=workspace_root,
    )
    input_payload = {
        "data_connection_response": source_response_json,
        "job": {
            "id": job.get("id"),
            "job_type": job.get("job_type"),
            "name": job.get("name"),
            "product_id": job.get("product_id"),
            "source_system": job.get("source_system"),
            "timezone": job.get("timezone"),
        },
        "knowledge_references": knowledge_references,
        "output_mapping": output_mapping,
        "output_schema": output_schema,
        "source_row_count": source_row_count,
    }
    request_config = {
        **config,
        AI_EXECUTOR_STAGE_MARKER: {
            "knowledge_references": knowledge_references,
            "output_mapping": output_mapping,
            "output_schema": output_schema,
            "resolved_plugin_input_mapping": resolved_plugin_input_mapping,
            "source_row_count": source_row_count,
            "stage": "ai_processing",
        },
    }
    task = create_ai_executor_task(
        current_store,
        action_id=plugin_summary.get("action_id") or job.get("plugin_action_id"),
        connection_id=plugin_summary.get("connection_id") or job.get("plugin_connection_id"),
        created_by=user["id"],
        executor_type=executor_type,
        input_payload=input_payload,
        instruction=_scheduled_job_ai_instruction(messages=messages, output_schema=output_schema),
        plugin_invocation_log_id=plugin_summary.get("invocation_log_id"),
        request_config=request_config,
        runner_id=runner["id"],
        scheduled_job_id=job.get("id"),
        scheduled_job_run_id=run_id,
        timeout_seconds=int(config.get("instruction_timeout_seconds") or job.get("timeout_seconds") or 1800),
        workspace_root=workspace_root,
    )
    return {
        "executor_type": executor_type,
        "knowledge_references": knowledge_references,
        "model_gateway_called": False,
        "output_json": {},
        "output_schema": output_schema,
        "runner_id": runner["id"],
        "runner_node": _runner_node_from_task(task),
        "runner_task_id": task["id"],
        "status": "queued",
    }


def pending_runner_skill_processing_node(
    current_store: Any,
    *,
    ai_processing: dict[str, Any],
    job: dict[str, Any],
    note: str,
    source_count_key: str,
    source_count: int,
) -> dict[str, Any]:
    return {
        "input": {
            "knowledge_references": ai_processing.get("knowledge_references") or [],
            source_count_key: source_count,
        },
        "label": "Skill 处理后内容",
        "model_gateway_called": False,
        "note": note,
        "output": {
            "runner_task_id": ai_processing.get("runner_task_id"),
        },
        "processing_mode": "ai_executor_runner",
        "runner_id": ai_processing.get("runner_id"),
        "runner_task_id": ai_processing.get("runner_task_id"),
        "skill_codes": skill_codes_for_job(current_store, job),
        "skill_ids": list(job.get("skill_ids", [])),
        "status": "waiting_runner",
    }


def pending_ai_executor_result_summary(
    current_store: Any,
    *,
    ai_processing: dict[str, Any],
    job: dict[str, Any],
    output_mapping: dict[str, Any],
    plugin_summary: dict[str, Any],
    resolved_plugin_input_mapping: dict[str, Any],
    source_count_key: str,
    source_row_count: int,
    wait_note: str,
    write_target: str | None = None,
) -> dict[str, Any]:
    resolved_write_target = write_target or str(
        output_mapping.get("write_target") or "scheduled_job_result",
    )
    return {
        "execution_nodes": {
            "data_connection": JobExecutionEngine.data_connection_execution_node(
                job=job,
                plugin_summary=plugin_summary,
                records_imported=source_row_count,
                resolved_plugin_input_mapping=resolved_plugin_input_mapping,
            ),
            "result_action": {
                "label": "结果动作反馈内容",
                "records_imported": 0,
                "status": "not_run",
                "write_target": resolved_write_target,
            },
            "result_actions": [
                {
                    "label": "结果动作反馈内容",
                    "records_imported": 0,
                    "status": "not_run",
                    "write_target": resolved_write_target,
                },
            ],
            "runner_execution": ai_processing.get("runner_node") or {},
            "skill_processing": pending_runner_skill_processing_node(
                current_store,
                ai_processing=ai_processing,
                job=job,
                note=wait_note,
                source_count=source_row_count,
                source_count_key=source_count_key,
            ),
        },
        "job_type": job.get("job_type"),
        "message": "AI 执行器任务已派发，等待 Runner 完成后继续执行结果动作。",
        "plugin": plugin_summary,
        "processing": {
            "executor_type": ai_processing.get("executor_type"),
            "model_gateway_called": False,
            "runner_id": ai_processing.get("runner_id"),
            "runner_task_id": ai_processing.get("runner_task_id"),
            "skill_codes": skill_codes_for_job(current_store, job),
            "skill_ids": list(job.get("skill_ids", [])),
        },
        "source_row_count": source_row_count,
        "write_target": resolved_write_target,
        "write_targets": [resolved_write_target],
    }


def scheduled_job_result_summary_has_pending_runner(result_summary: dict[str, Any]) -> bool:
    execution_nodes = result_summary.get("execution_nodes") if isinstance(result_summary, dict) else {}
    if not isinstance(execution_nodes, dict):
        return False
    runner_node = execution_nodes.get("runner_execution")
    return isinstance(runner_node, dict) and runner_node.get("status") in RUNNER_ACTIVE_STATUSES


def _runner_output_json(task: dict[str, Any]) -> dict[str, Any]:
    result_json = task.get("result_json")
    if not isinstance(result_json, dict):
        return {}
    direct_result = result_json.get("result")
    if isinstance(direct_result, dict):
        return direct_result
    parsed_output = result_json.get("parsed_output")
    if isinstance(parsed_output, dict):
        return parsed_output
    output_preview = result_json.get("output_preview")
    if isinstance(output_preview, str) and output_preview.strip():
        text = output_preview.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"summary": text[:1000]}
        if isinstance(parsed, dict):
            return parsed
        return {"result": parsed}
    return result_json


def _existing_plugin_summary(run: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    result_summary = run.get("result_summary") or {}
    plugin_summary = result_summary.get("plugin")
    if isinstance(plugin_summary, dict):
        return dict(plugin_summary)
    return {
        "action_id": task.get("action_id"),
        "connection_id": task.get("connection_id"),
        "invocation_log_id": task.get("plugin_invocation_log_id"),
        "request_summary": {},
        "response_summary": {},
        "status": "succeeded",
    }


def _resolve_job_plugin_output_mapping(current_store: Any, job: dict[str, Any]) -> dict[str, Any]:
    job_mapping = job.get("plugin_output_mapping") or {}
    if isinstance(job_mapping, dict) and job_mapping:
        return dict(job_mapping)
    action_id = job.get("plugin_action_id")
    if not action_id:
        return {}
    action = read_memory_dict(current_store, "plugin_actions").get(action_id) or {}
    action_mapping = action.get("result_mapping") if isinstance(action, dict) else {}
    return dict(action_mapping) if isinstance(action_mapping, dict) else {}


def _generic_ai_executor_result_summary(
    current_store: Any,
    *,
    ai_processing: dict[str, Any],
    job: dict[str, Any],
    output_mapping: dict[str, Any],
    output_json: dict[str, Any],
    plugin_summary: dict[str, Any],
    resolved_plugin_input_mapping: dict[str, Any],
    runner_node: dict[str, Any],
    source_row_count: int,
) -> tuple[dict[str, Any], int]:
    result_actions, action_records_imported = execute_generic_result_actions(
        job=job,
        output_json=output_json,
        output_mapping=output_mapping,
        result_actions=job.get("result_actions") or [],
    )
    records_imported = max(
        action_records_imported,
        inferred_output_record_count(output_json, output_mapping),
    )
    primary_result_action = result_actions[0] if result_actions else {}
    return {
        "execution_nodes": {
            "data_connection": JobExecutionEngine.data_connection_execution_node(
                job=job,
                plugin_summary=plugin_summary,
                records_imported=source_row_count,
                resolved_plugin_input_mapping=resolved_plugin_input_mapping,
            ),
            "result_action": primary_result_action,
            "result_actions": result_actions,
            "runner_execution": runner_node,
            "skill_processing": {
                "input": {
                    "knowledge_references": ai_processing.get("knowledge_references") or [],
                    "source_row_count": source_row_count,
                },
                "label": "Skill 处理后内容",
                "model_gateway_called": False,
                "note": "数据连接返回内容已通过 AI 执行器处理为结果动作可消费的结构化 JSON。",
                "output": {
                    "processed_json": output_json,
                    "records_imported": records_imported,
                    "summary": output_json.get("summary"),
                },
                "processing_mode": "ai_executor_runner",
                "runner_id": runner_node.get("runner_id"),
                "runner_task_id": runner_node.get("runner_task_id"),
                "skill_codes": skill_codes_for_job(current_store, job),
                "skill_ids": list(job.get("skill_ids", [])),
                "status": "succeeded",
            },
        },
        "job_type": job.get("job_type"),
        "message": "AI 执行器处理完成，结果已进入动作。",
        "plugin": plugin_summary,
        "processing": {
            "executor_type": runner_node.get("executor_type"),
            "model_gateway_called": False,
            "runner_id": runner_node.get("runner_id"),
            "runner_task_id": runner_node.get("runner_task_id"),
            "skill_ids": list(job.get("skill_ids", [])),
        },
        "source_row_count": source_row_count,
        "write_target": primary_result_action.get("write_target"),
        "write_targets": [action["write_target"] for action in result_actions],
    }, records_imported


def _code_inspection_ai_executor_result_summary(
    current_store: Any,
    *,
    job: dict[str, Any],
    output_mapping: dict[str, Any],
    output_json: dict[str, Any],
    plugin_summary: dict[str, Any],
    resolved_plugin_input_mapping: dict[str, Any],
    runner_node: dict[str, Any],
    run: dict[str, Any],
    source_finding_count: int,
    user: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    from app.services.code_inspections import execute_code_inspection_result_actions

    ai_processing = {
        "knowledge_references": [],
        "output_json": output_json,
        "runner_id": runner_node.get("runner_id"),
        "runner_node": runner_node,
        "runner_task_id": runner_node.get("runner_task_id"),
        "status": "succeeded",
    }
    effective_plugin_summary = JobExecutionEngine.code_inspection_plugin_summary_for_ai_output(
        plugin_summary,
        ai_processing=ai_processing,
    )
    inspection_result = execute_code_inspection_result_actions(
        current_store,
        collector_run_id=run.get("collector_run_id"),
        job=job,
        plugin_summary=effective_plugin_summary,
        result_actions=job.get("result_actions") or [],
        run_id=str(run["id"]),
        user=user,
    )
    report = inspection_result["report"]
    records_imported = int(inspection_result["finding_count"])
    skill_codes = skill_codes_for_job(current_store, job)
    findings = output_json.get("findings") if isinstance(output_json, dict) else []
    skill_node = {
        "input": {
            "findings_path": str(output_mapping.get("findings_path") or "$.findings"),
            "knowledge_references": ai_processing.get("knowledge_references") or [],
            "source_finding_count": source_finding_count,
        },
        "label": "Skill 处理后内容",
        "model_gateway_called": False,
        "note": "代码扫描返回内容已通过 AI 执行器处理为代码巡检报告可消费的结构化 JSON。",
        "output": {
            "finding_count": len(findings) if isinstance(findings, list) else 0,
            "processed_json": output_json,
            "risk_level": output_json.get("risk_level") if isinstance(output_json, dict) else None,
            "summary": output_json.get("summary") if isinstance(output_json, dict) else None,
        },
        "processing_mode": "ai_executor_runner",
        "runner_id": runner_node.get("runner_id"),
        "runner_task_id": runner_node.get("runner_task_id"),
        "skill_codes": skill_codes,
        "skill_ids": list(job.get("skill_ids", [])),
        "status": "succeeded",
    }
    result_action_node = JobExecutionEngine.code_inspection_result_action_node(
        inspection_result=inspection_result,
        report=report,
    )
    native_scan_summary = (plugin_summary.get("response_summary") or {}).get("native_scan")
    execution_nodes = {
        "bug_creation": {
            "created_bug_ids": inspection_result["bug_ids"],
            "deduplicated_bug_ids": inspection_result["deduplicated_bug_ids"],
            "label": "严重问题自动创建 Bug",
            "records_imported": len(inspection_result["bug_ids"]),
            "status": "succeeded",
        },
        "task_creation": {
            "created_task_ids": inspection_result.get("task_ids") or [],
            "label": "严重问题自动创建整改任务",
            "records_imported": len(inspection_result.get("task_ids") or []),
            "status": "succeeded",
        },
        "code_inspection_report": {
            "finding_count": report["finding_count"],
            "label": "代码巡检报告写入结果",
            "report_id": report["id"],
            "risk_level": report["risk_level"],
            "severe_finding_count": report["severe_finding_count"],
            "status": "succeeded",
        },
        "data_connection": JobExecutionEngine.data_connection_execution_node(
            job=job,
            plugin_summary=plugin_summary,
            records_imported=source_finding_count,
            resolved_plugin_input_mapping=resolved_plugin_input_mapping,
        ),
        "notifications": {
            "created_notification_ids": inspection_result["notification_ids"],
            "label": "问题消息通知",
            "records_imported": len(inspection_result["notification_ids"]),
            "status": "succeeded",
        },
        "result_action": result_action_node,
        "result_actions": inspection_result["action_results"],
        "runner_execution": runner_node,
        "skill_processing": skill_node,
    }
    if isinstance(native_scan_summary, dict):
        execution_nodes["native_scan"] = {
            **native_scan_summary,
            "label": "本地完整代码静态扫描",
            "records_imported": source_finding_count,
            "status": "succeeded",
        }
    return {
        "bug_ids": inspection_result["bug_ids"],
        "deduplicated_bug_ids": inspection_result["deduplicated_bug_ids"],
        "execution_nodes": execution_nodes,
        "finding_count": report["finding_count"],
        "notification_ids": inspection_result["notification_ids"],
        "plugin": effective_plugin_summary,
        "processing": {
            "model_gateway_called": False,
            "runner_id": runner_node.get("runner_id"),
            "runner_task_id": runner_node.get("runner_task_id"),
            "skill_codes": skill_codes,
            "skill_ids": list(job.get("skill_ids", [])),
        },
        "report_id": report["id"],
        "result_actions": inspection_result["result_actions"],
        "risk_level": report["risk_level"],
        "severe_finding_count": report["severe_finding_count"],
        "task_ids": inspection_result.get("task_ids") or [],
        "write_target": "code_inspection_reports",
    }, records_imported


def _update_collector_run(
    current_store: Any,
    *,
    error_message: str | None,
    records_imported: int,
    run: dict[str, Any],
    status: str,
    user_id: str,
) -> None:
    collector_run_id = run.get("collector_run_id")
    collector_run = (
        read_memory_dict(current_store, "collector_runs").get(collector_run_id)
        if collector_run_id
        else None
    )
    if collector_run is None:
        return
    now = datetime.now(UTC).isoformat()
    collector_status = (
        "succeeded" if status == "succeeded" else "cancelled" if status == "cancelled" else "failed"
    )
    updated_collector = {
        **collector_run,
        "error_message": error_message,
        "finished_at": now if status in {"cancelled", "failed", "succeeded"} else None,
        "records_imported": records_imported,
        "status": collector_status if status in {"cancelled", "failed", "succeeded"} else "running",
        "updated_at": now,
    }
    put_memory_record(current_store, "collector_runs", updated_collector)
    audit_event = record_audit_event(
        current_store,
        event_type="collector_run.updated",
        actor_id=user_id,
        subject_type="collector_run",
        subject_id=updated_collector["id"],
        payload={"records_imported": records_imported, "status": updated_collector["status"]},
    )
    persist_record(
        current_store,
        "save_collector_run_record",
        updated_collector,
        audit_event=audit_event,
    )


def sync_ai_executor_completion_to_scheduled_run(
    current_store: Any,
    *,
    runner_id: str,
    task: dict[str, Any],
) -> bool:
    request_config = task.get("request_config") if isinstance(task.get("request_config"), dict) else {}
    stage_context = request_config.get(AI_EXECUTOR_STAGE_MARKER)
    if not isinstance(stage_context, dict) or stage_context.get("stage") != "ai_processing":
        return False
    run_id = task.get("scheduled_job_run_id")
    job_id = task.get("scheduled_job_id")
    run = read_memory_dict(current_store, "scheduled_job_runs").get(run_id)
    job = read_memory_dict(current_store, "scheduled_jobs").get(job_id)
    if run is None or job is None:
        return True
    output_mapping = (
        dict(stage_context.get("output_mapping"))
        if isinstance(stage_context.get("output_mapping"), dict)
        else _resolve_job_plugin_output_mapping(current_store, job)
    )
    output_schema = (
        dict(stage_context.get("output_schema"))
        if isinstance(stage_context.get("output_schema"), dict)
        else {}
    )
    resolved_plugin_input_mapping = (
        dict(stage_context.get("resolved_plugin_input_mapping"))
        if isinstance(stage_context.get("resolved_plugin_input_mapping"), dict)
        else {}
    )
    source_row_count = int(stage_context.get("source_row_count") or 0)
    plugin_summary = _existing_plugin_summary(run, task)
    runner_node = _runner_node_from_task(task)
    result_summary = dict(run.get("result_summary") or {})
    execution_nodes = dict(result_summary.get("execution_nodes") or {})
    execution_nodes["runner_execution"] = runner_node
    status = str(task.get("status") or "running")
    records_imported = int(run.get("records_imported") or 0)
    error_code = None
    error_message = None
    finished_at = None
    if status in RUNNER_ACTIVE_STATUSES:
        skill_node = dict(execution_nodes.get("skill_processing") or {})
        skill_node.update(
            {
                "label": "Skill 处理后内容",
                "model_gateway_called": False,
                "note": "AI 执行器任务已派发，等待 Runner 完成后继续执行动作。",
                "processing_mode": "ai_executor_runner",
                "runner_id": task.get("runner_id"),
                "runner_task_id": task.get("id"),
                "status": "waiting_runner" if status != "running" else "running",
            }
        )
        execution_nodes["skill_processing"] = skill_node
        result_summary["execution_nodes"] = execution_nodes
        run_status = "running"
    elif status in RUNNER_FAILED_STATUSES:
        error_code = task.get("error_code") or "AI_EXECUTOR_TASK_FAILED"
        error_message = task.get("error_message") or "AI executor task failed"
        skill_node = dict(execution_nodes.get("skill_processing") or {})
        skill_node.update(
            {
                "error_code": error_code,
                "error_message": error_message,
                "label": "Skill 处理后内容",
                "model_gateway_called": False,
                "note": "AI 执行器处理失败，结果动作未执行。",
                "processing_mode": "ai_executor_runner",
                "runner_id": task.get("runner_id"),
                "runner_task_id": task.get("id"),
                "status": "failed",
            }
        )
        execution_nodes["skill_processing"] = skill_node
        result_action = dict(execution_nodes.get("result_action") or {})
        result_action.update({"label": "结果动作反馈内容", "records_imported": 0, "status": "not_run"})
        execution_nodes["result_action"] = result_action
        result_summary["execution_nodes"] = execution_nodes
        run_status = "failed" if status != "cancelled" else "cancelled"
        finished_at = datetime.now(UTC).isoformat()
    else:
        output_json = _runner_output_json(task)
        try:
            validate_skill_output_json_contract(output_json, output_schema)
            if job.get("job_type") == "user_feedback_insight_extract":
                from app.services.scheduled_job_user_feedback import (
                    user_feedback_result_summary_from_ai_output,
                )

                result_summary, records_imported = user_feedback_result_summary_from_ai_output(
                    current_store,
                    ai_processing={
                        "knowledge_references": stage_context.get("knowledge_references") or [],
                        "output_json": output_json,
                        "runner_id": task.get("runner_id"),
                        "runner_node": runner_node,
                        "runner_task_id": task.get("id"),
                        "status": "succeeded",
                    },
                    job=job,
                    plugin_summary=plugin_summary,
                    processed_json=output_json,
                    resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                    source_row_count=source_row_count,
                    user={"id": task.get("created_by") or runner_id, "roles": ["admin"]},
                )
            elif job.get("job_type") == "code_repository_inspection":
                result_summary, records_imported = _code_inspection_ai_executor_result_summary(
                    current_store,
                    job=job,
                    output_mapping=output_mapping,
                    output_json=output_json,
                    plugin_summary=plugin_summary,
                    resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                    runner_node=runner_node,
                    run=run,
                    source_finding_count=source_row_count,
                    user={"id": task.get("created_by") or runner_id, "roles": ["admin"]},
                )
            else:
                result_summary, records_imported = _generic_ai_executor_result_summary(
                    current_store,
                    ai_processing={"knowledge_references": stage_context.get("knowledge_references") or []},
                    job=job,
                    output_mapping=output_mapping,
                    output_json=output_json,
                    plugin_summary=plugin_summary,
                    resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                    runner_node=runner_node,
                    source_row_count=source_row_count,
                )
            result_summary.setdefault("execution_nodes", {})["runner_execution"] = runner_node
            run_status = "succeeded"
            finished_at = datetime.now(UTC).isoformat()
        except Exception as exc:  # noqa: BLE001 - completion must convert action/schema errors to run failure.
            error_code, error_message = exception_error_code_and_message(exc)
            execution_nodes["runner_execution"] = runner_node
            execution_nodes["skill_processing"] = {
                "error_code": error_code,
                "error_message": error_message,
                "label": "Skill 处理后内容",
                "model_gateway_called": False,
                "note": "AI 执行器已返回结果，但结果不符合 Skill 输出契约或动作写入失败。",
                "output": {"processed_json": _runner_output_json(task)},
                "processing_mode": "ai_executor_runner",
                "runner_id": task.get("runner_id"),
                "runner_task_id": task.get("id"),
                "status": "failed",
            }
            execution_nodes["result_action"] = {
                "label": "结果动作反馈内容",
                "records_imported": 0,
                "status": "not_run",
            }
            result_summary["execution_nodes"] = execution_nodes
            run_status = "failed"
            records_imported = 0
            finished_at = datetime.now(UTC).isoformat()
    now = datetime.now(UTC).isoformat()
    updated_run = {
        **run,
        "error_code": error_code if run_status == "failed" else None,
        "error_message": error_message if run_status == "failed" else None,
        "finished_at": finished_at,
        "records_imported": records_imported,
        "result_summary": result_summary,
        "status": run_status,
        "updated_at": now,
    }
    put_memory_record(current_store, "scheduled_job_runs", updated_run)
    _update_collector_run(
        current_store,
        error_message=error_message,
        records_imported=records_imported,
        run=updated_run,
        status=run_status,
        user_id=runner_id,
    )
    if run_status in {"failed", "succeeded"}:
        job_update = {
            **job,
            "last_error_message": error_message,
            "last_failure_at": finished_at if run_status == "failed" else job.get("last_failure_at"),
            "last_run_at": finished_at or now,
            "last_success_at": finished_at if run_status == "succeeded" else job.get("last_success_at"),
            "updated_at": now,
        }
        put_memory_record(current_store, "scheduled_jobs", job_update)
        persist_record(current_store, "save_scheduled_job_record", job_update)
    audit_event = record_audit_event(
        current_store,
        event_type=f"scheduled_job_run.{run_status}",
        actor_id=runner_id,
        subject_type="scheduled_job_run",
        subject_id=updated_run["id"],
        payload={
            "ai_executor_task_id": task["id"],
            "executor_type": task.get("executor_type"),
            "records_imported": records_imported,
            "runner_id": runner_id,
            "scheduled_job_id": task.get("scheduled_job_id"),
            "status": run_status,
        },
    )
    persist_record(
        current_store,
        "save_scheduled_job_run_record",
        updated_run,
        audit_event=audit_event,
    )
    return True
