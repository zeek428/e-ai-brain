from __future__ import annotations

from typing import Any

from app.services import scheduled_job_runtime as job_runtime
from app.services.native_code_scanner import run_native_code_scan
from app.services.scheduled_job_ai_executor import (
    scheduled_job_uses_local_ai_executor,
    system_default_runner_node_from_ai_processing,
)
from app.services.scheduled_job_ai_processing import run_scheduled_job_ai_processing
from app.services.scheduled_job_catalog import AI_REQUIRED_SCHEDULED_JOB_TYPES
from app.services.scheduled_job_execution_engine import (
    ScheduledJobExecutionEngine as JobExecutionEngine,
)
from app.services.scheduled_job_user_feedback import resolve_job_plugin_output_mapping


def code_inspection_multi_ai_processor(
    current_store: Any,
    *,
    job: dict[str, Any],
    run_id: str,
    user: dict[str, Any],
):
    uses_ai = JobExecutionEngine.uses_ai_processing(
        job,
        ai_required_job_types=AI_REQUIRED_SCHEDULED_JOB_TYPES,
    )
    if not uses_ai or scheduled_job_uses_local_ai_executor(job):
        return None
    output_mapping = resolve_job_plugin_output_mapping(current_store, job)

    def process_repository(
        scanned_job: dict[str, Any],
        plugin_summary: dict[str, Any],
        source_response_json: dict[str, Any],
        source_finding_count: int,
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        ai_processing = run_scheduled_job_ai_processing(
            current_store,
            job=scanned_job,
            output_mapping=output_mapping,
            source_response_json=source_response_json,
            source_row_count=source_finding_count,
            user=user,
        )
        ai_processing["runner_node"] = system_default_runner_node_from_ai_processing(
            ai_processing,
            job=scanned_job,
        )
        return (
            ai_processing,
            JobExecutionEngine.code_inspection_plugin_summary_for_ai_output(
                plugin_summary,
                ai_processing=ai_processing,
            ),
        )

    return process_repository


def run_native_code_scan_with_worker_retry(
    current_store: Any,
    *,
    job: dict[str, Any],
    retry_state: dict[str, Any],
    run_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    max_retry_count = max(0, int(job.get("max_retry_count") or 0))
    attempt = 0
    while True:
        attempt += 1
        retry_state["attempts"] = int(retry_state.get("attempts") or 0) + 1
        try:
            return run_native_code_scan(
                current_store,
                job=job,
                run_id=run_id,
                user=user,
            )
        except Exception as exc:
            error_code, error_message = job_runtime.exception_error_code_and_message(exc)
            if attempt > max_retry_count:
                raise
            retry_state.setdefault("errors", []).append(
                {
                    "attempt": retry_state["attempts"],
                    "error_code": error_code,
                    "error_message": error_message,
                },
            )


def result_summary_with_worker_retry(
    result_summary: dict[str, Any],
    *,
    retry_state: dict[str, Any],
) -> dict[str, Any]:
    processing = dict(result_summary.get("processing") or {})
    retry_errors = list(retry_state.get("errors") or [])
    processing.update(
        {
            "worker_attempts": int(retry_state.get("attempts") or 0),
            "worker_retry_count": len(retry_errors),
            "worker_retry_errors": retry_errors,
        },
    )
    return {**result_summary, "processing": processing}
