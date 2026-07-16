from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.services import scheduled_job_runtime as job_runtime
from app.services import scheduled_job_store as job_store
from app.services.code_inspections import execute_code_inspection_result_actions
from app.services.native_code_scanner import NATIVE_CODE_SCAN_MODE
from app.services.operational_records import record_audit_event
from app.services.scheduled_job_access import require_admin
from app.services.scheduled_job_ai_executor import (
    dispatch_scheduled_job_ai_executor_processing,
    pending_ai_executor_result_summary,
    scheduled_job_uses_local_ai_executor,
    system_default_runner_node_from_ai_processing,
)
from app.services.scheduled_job_ai_processing import (
    run_scheduled_job_ai_processing,
    skill_codes_for_job,
)
from app.services.scheduled_job_audit import scheduled_job_run_audit_payload
from app.services.scheduled_job_catalog import AI_REQUIRED_SCHEDULED_JOB_TYPES
from app.services.scheduled_job_code_inspection_runtime import (
    code_inspection_multi_ai_processor,
    result_summary_with_worker_retry,
    run_native_code_scan_with_worker_retry,
)
from app.services.scheduled_job_constants import SCHEDULED_JOB_RUN_TERMINAL_STATUSES
from app.services.scheduled_job_execution_engine import (
    ScheduledJobExecutionEngine as JobExecutionEngine,
)
from app.services.scheduled_job_native_scan import (
    code_inspection_single_result_summary,
    execute_native_multi_code_inspection_summary,
    native_code_scan_repository_ids,
)
from app.services.scheduled_job_read_models import public_scheduled_job_run
from app.services.scheduled_job_user_feedback import resolve_job_plugin_output_mapping


def execute_queued_scheduled_job_run_response(
    *,
    current_store: Any,
    run_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    # Import lifecycle helpers lazily to keep the worker module separate from API orchestration.
    from app.services.scheduled_jobs import (
        _next_run_after,
        cancelled_scheduled_job_run_if_requested,
        complete_collector_run,
        create_collector_run_for_job,
        queued_native_scan_result_summary,
        scheduled_job_uses_async_worker,
    )

    require_admin(user)
    job_store.sync_scheduled_job_store(current_store)
    job_store.sync_ai_agent_store(current_store)
    job_store.sync_ai_skill_store(current_store)
    job_store.sync_reference_store(current_store)
    job_store.sync_scheduled_job_run_store(current_store)
    run = job_store.read_memory_dict(current_store, "scheduled_job_runs").get(run_id)
    if run is None:
        raise api_error(404, "NOT_FOUND", "Scheduled job run not found")
    if run.get("status") in SCHEDULED_JOB_RUN_TERMINAL_STATUSES:
        raise api_error(409, "SCHEDULED_JOB_RUN_STATE_INVALID", "Terminal run cannot be executed")
    if run.get("status") != "queued":
        raise api_error(409, "SCHEDULED_JOB_RUN_STATE_INVALID", "Only queued runs can be executed")
    job = job_store.read_memory_dict(current_store, "scheduled_jobs").get(run.get("scheduled_job_id"))  # noqa: E501
    if job is None:
        raise api_error(404, "NOT_FOUND", "Scheduled job not found")
    if not scheduled_job_uses_async_worker(job):
        raise api_error(400, "VALIDATION_ERROR", "Scheduled job run is not async native code scan")
    if not job.get("enabled"):
        raise api_error(409, "SCHEDULED_JOB_DISABLED", "Scheduled job is disabled")

    now = datetime.now(UTC).isoformat()
    collector_run = job_store.read_memory_dict(current_store, "collector_runs").get(
        run.get("collector_run_id"),
    )
    if collector_run is None:
        collector_run = create_collector_run_for_job(
            current_store,
            job=job,
            run_id=run_id,
            status="running",
            user=user,
        )
        run["collector_run_id"] = collector_run["id"]
    run = {
        **run,
        "result_summary": queued_native_scan_result_summary(current_store, job=job),
        "started_at": now,
        "status": "running",
        "updated_at": now,
    }
    job_store.put_memory_record(current_store, "scheduled_job_runs", run)
    job_store.persist_record(current_store, "save_scheduled_job_run_record", run)

    plugin_summary = None
    plugin_output_mapping: dict[str, Any] = {}
    records_imported = 0
    resolved_plugin_input_mapping: dict[str, Any] = {}
    worker_retry_state: dict[str, Any] = {"attempts": 0, "errors": []}
    try:
        native_repository_ids = native_code_scan_repository_ids(job, current_store=current_store)
        if len(native_repository_ids) > 1:
            result_summary, records_imported = execute_native_multi_code_inspection_summary(
                current_store,
                ai_processor=code_inspection_multi_ai_processor(
                    current_store,
                    job=job,
                    run_id=run_id,
                    user=user,
                ),
                collector_run_id=collector_run["id"],
                job=job,
                repository_ids=native_repository_ids,
                run_id=run_id,
                scan_runner=lambda current_store, job, run_id, user: run_native_code_scan_with_worker_retry(  # noqa: E501
                    current_store,
                    job=job,
                    retry_state=worker_retry_state,
                    run_id=run_id,
                    user=user,
                ),
                skill_codes=skill_codes_for_job(current_store, job),
                user=user,
            )
            cancelled_run = cancelled_scheduled_job_run_if_requested(
                current_store,
                collector_run=collector_run,
                run_id=run_id,
                user=user,
            )
            if cancelled_run is not None:
                return cancelled_run
            status = "succeeded"
            error_code = None
            error_message = None
            raise StopIteration
        job_config = job.get("config_json") or {}
        resolved_plugin_input_mapping = {
            "branch": job_config.get("branch"),
            "repository_id": job_config.get("repository_id"),
            "scan_mode": NATIVE_CODE_SCAN_MODE,
        }
        plugin_summary = run_native_code_scan_with_worker_retry(
            current_store,
            job=job,
            retry_state=worker_retry_state,
            run_id=run_id,
            user=user,
        )
        cancelled_run = cancelled_scheduled_job_run_if_requested(
            current_store,
            collector_run=collector_run,
            run_id=run_id,
            user=user,
        )
        if cancelled_run is not None:
            return cancelled_run
        if plugin_summary.get("status") != "succeeded":
            raise api_error(
                502,
                "PLUGIN_ACTION_FAILED",
                "Code repository inspection plugin action failed",
            )
        plugin_output_mapping = resolve_job_plugin_output_mapping(current_store, job)
        source_response_json = (plugin_summary.get("response_summary") or {}).get("json") or {}
        if not isinstance(source_response_json, dict):
            source_response_json = {}
        source_findings = source_response_json.get("findings")
        source_finding_count = len(source_findings) if isinstance(source_findings, list) else 0
        ai_processing = None
        effective_plugin_summary = plugin_summary
        if JobExecutionEngine.uses_ai_processing(
            job,
            ai_required_job_types=AI_REQUIRED_SCHEDULED_JOB_TYPES,
        ):
            if scheduled_job_uses_local_ai_executor(job):
                ai_processing = dispatch_scheduled_job_ai_executor_processing(
                    current_store,
                    job=job,
                    output_mapping=plugin_output_mapping,
                    plugin_summary=plugin_summary,
                    resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                    run_id=run_id,
                    source_response_json=source_response_json,
                    source_row_count=source_finding_count,
                    user=user,
                )
                result_summary = pending_ai_executor_result_summary(
                    current_store,
                    ai_processing=ai_processing,
                    job=job,
                    output_mapping=plugin_output_mapping,
                    plugin_summary=plugin_summary,
                    resolved_plugin_input_mapping=resolved_plugin_input_mapping,
                    source_count_key="source_finding_count",
                    source_row_count=source_finding_count,
                    wait_note=(
                        "代码扫描结果已派发给 AI 执行器，"
                        "等待 Runner 复核后写入代码巡检报告。"
                    ),
                    write_target="code_inspection_reports",
                )
                records_imported = 0
                status = "succeeded"
                error_code = None
                error_message = None
                raise StopIteration
            ai_processing = run_scheduled_job_ai_processing(
                current_store,
                job=job,
                output_mapping=plugin_output_mapping,
                source_response_json=source_response_json,
                source_row_count=source_finding_count,
                user=user,
            )
            ai_processing["runner_node"] = system_default_runner_node_from_ai_processing(
                ai_processing,
                job=job,
            )
            effective_plugin_summary = (
                JobExecutionEngine.code_inspection_plugin_summary_for_ai_output(
                    plugin_summary,
                    ai_processing=ai_processing,
                )
            )
        inspection_result = execute_code_inspection_result_actions(
            current_store,
            collector_run_id=collector_run["id"],
            job=job,
            plugin_summary=effective_plugin_summary,
            result_actions=job.get("result_actions") or [],
            run_id=run_id,
            user=user,
        )
        records_imported = int(inspection_result["finding_count"])
        result_summary = code_inspection_single_result_summary(
            ai_processing=ai_processing,
            async_worker=True,
            effective_plugin_summary=effective_plugin_summary,
            include_native_scan=True,
            inspection_result=inspection_result,
            job=job,
            output_mapping=plugin_output_mapping,
            plugin_summary=plugin_summary,
            resolved_plugin_input_mapping=resolved_plugin_input_mapping,
            skill_codes=skill_codes_for_job(current_store, job),
            source_finding_count=source_finding_count,
        )
        status = "succeeded"
        error_code = None
        error_message = None
    except StopIteration:
        pass
    except Exception as exc:
        status = "failed"
        error_code, error_message = job_runtime.exception_error_code_and_message(exc)
        result_summary = {
            "execution_nodes": {
                "native_scan": {
                    "error_code": error_code,
                    "error_message": error_message,
                    "label": "本地完整代码静态扫描",
                    "records_imported": 0,
                    "scan_mode": NATIVE_CODE_SCAN_MODE,
                    "status": "failed",
                },
                "result_action": {
                    "label": "结果动作反馈内容",
                    "records_imported": 0,
                    "status": "not_run",
                    "write_target": "code_inspection_reports",
                },
            },
            "plugin": plugin_summary,
            "processing": {
                "async_worker": True,
                "error_code": error_code,
                "error_message": error_message,
                "model_gateway_called": False,
                "skill_codes": skill_codes_for_job(current_store, job),
                "skill_ids": list(job.get("skill_ids", [])),
            },
            "write_target": "code_inspection_reports",
        }
        records_imported = 0

    result_summary = result_summary_with_worker_retry(
        result_summary,
        retry_state=worker_retry_state,
    )
    finished_at = datetime.now(UTC).isoformat()
    updated_at = datetime.now(UTC).isoformat()
    run = {
        **run,
        "error_code": error_code,
        "error_message": error_message,
        "finished_at": finished_at,
        "records_imported": records_imported,
        "result_summary": result_summary,
        "status": status,
        "updated_at": updated_at,
    }
    job_store.put_memory_record(current_store, "scheduled_job_runs", run)
    complete_collector_run(
        current_store,
        collector_run=collector_run,
        error_message=error_message,
        records_imported=records_imported,
        status=status,
        user=user,
    )
    job_update = {
        **job,
        "last_error_message": error_message,
        "last_failure_at": finished_at if status == "failed" else job.get("last_failure_at"),
        "last_run_at": finished_at,
        "last_success_at": finished_at if status == "succeeded" else job.get("last_success_at"),
        "next_run_at": _next_run_after(job, finished_at),
        "updated_at": updated_at,
    }
    job_store.put_memory_record(current_store, "scheduled_jobs", job_update)
    job_store.persist_record(current_store, "save_scheduled_job_record", job_update)
    job_store.persist_record(current_store, "save_scheduled_job_run_record", run)
    audit_event = record_audit_event(
        current_store,
        event_type=f"scheduled_job_run.{status}",
        actor_id=user["id"],
        subject_type="scheduled_job_run",
        subject_id=run_id,
        payload=scheduled_job_run_audit_payload(job=job, run=run),
    )
    job_store.persist_record(
        current_store,
        "save_scheduled_job_run_record",
        run,
        audit_event=audit_event,
    )
    return public_scheduled_job_run(run, current_store=current_store)
