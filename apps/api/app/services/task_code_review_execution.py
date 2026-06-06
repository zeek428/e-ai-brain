from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.code_review_executor import (
    CodeReviewExecutorError,
    CodeReviewExecutorResult,
    ExternalCommandCodeReviewExecutor,
    normalize_code_review_output,
)
from app.core.config import get_settings
from app.services.model_gateway import (
    ModelGatewayCallError,
    ModelGatewayConfigError,
    call_model_gateway_for_task,
)

settings = get_settings()


def code_review_executor_payload(
    current_store: Any,
    task: dict[str, Any],
    *,
    public_product_context: Callable[[Any], Any],
) -> dict[str, Any]:
    snapshot_id = str(task.get("input_json", {}).get("gitlab_mr_snapshot_id") or "")
    snapshot = current_store.gitlab_mr_snapshots.get(snapshot_id)
    technical_solution = (
        current_store.ai_tasks.get(snapshot["technical_solution_task_id"])
        if snapshot is not None
        else None
    )
    return {
        "task": {
            "id": task["id"],
            "title": task["title"],
            "task_type": task["task_type"],
            "input_json": current_store.snapshot(task.get("input_json", {})),
            "product_context": public_product_context(task.get("product_context")),
            "requirement_snapshot": current_store.snapshot(task.get("requirement_snapshot", {})),
        },
        "gitlab_mr_snapshot": current_store.snapshot(snapshot),
        "technical_solution_task": current_store.snapshot(technical_solution),
    }


def code_review_executor_metadata(executor: Any | None = None) -> tuple[str, str]:
    executor_type = (
        str(getattr(executor, "executor_type", "")).strip()
        if executor is not None
        else ""
    ) or settings.code_review_executor_type
    executor_name = (
        str(getattr(executor, "executor_name", "")).strip()
        if executor is not None
        else ""
    ) or settings.code_review_executor_name
    return executor_type, executor_name


def should_use_model_gateway_code_review_executor(
    current_store: Any,
    *,
    executor_type: str,
) -> bool:
    if executor_type != "claude_code_skill" or settings.code_review_executor_command.strip():
        return False
    if any(
        item.get("is_default") and item.get("status") == "active"
        for item in current_store.model_gateway_configs.values()
    ):
        return True
    return settings.model_gateway_status == "configured"


def coerce_code_review_executor_result(
    raw_result: Any,
    *,
    executor_type: str,
    executor_name: str,
) -> CodeReviewExecutorResult:
    if isinstance(raw_result, CodeReviewExecutorResult):
        output = raw_result.output
        model_log = raw_result.model_log
    elif isinstance(raw_result, tuple):
        output = raw_result[0]
        model_log = raw_result[1] if len(raw_result) > 1 else None
    else:
        output = raw_result
        model_log = None
    try:
        normalized = normalize_code_review_output(
            output,
            executor_type=executor_type,
            executor_name=executor_name,
        )
    except (TypeError, ValueError) as exc:
        raise CodeReviewExecutorError(
            "Code review executor returned invalid output",
            executor_type=executor_type,
            executor_name=executor_name,
            stage="parse_output",
            retryable=True,
        ) from exc
    return CodeReviewExecutorResult(
        output=normalized,
        executor=normalized["executor"],
        model_log=model_log,
    )


def call_configured_code_review_executor(
    current_store: Any,
    *,
    code_review_executor: Any | None = None,
    opener: Any | None = None,
    public_product_context: Callable[[Any], Any],
    task: dict[str, Any],
) -> CodeReviewExecutorResult:
    payload = code_review_executor_payload(
        current_store,
        task,
        public_product_context=public_product_context,
    )
    if code_review_executor is not None:
        executor_type, executor_name = code_review_executor_metadata(code_review_executor)
        try:
            raw_result = code_review_executor.execute(
                current_store=current_store,
                task=task,
                payload=payload,
            )
        except CodeReviewExecutorError:
            raise
        except Exception as exc:
            raise CodeReviewExecutorError(
                "Code review executor failed",
                executor_type=executor_type,
                executor_name=executor_name,
                stage="execute",
                retryable=True,
            ) from exc
        return coerce_code_review_executor_result(
            raw_result,
            executor_type=executor_type,
            executor_name=executor_name,
        )

    executor_type, executor_name = code_review_executor_metadata()
    if executor_type == "model_gateway" or should_use_model_gateway_code_review_executor(
        current_store,
        executor_type=executor_type,
    ):
        executor_type = "model_gateway"
        try:
            output, model_log = call_model_gateway_for_task(
                current_store,
                code_review_payload=payload,
                opener=opener,
                task=task,
            )
        except ModelGatewayConfigError as exc:
            raise CodeReviewExecutorError(
                str(exc),
                executor_type=executor_type,
                executor_name=executor_name,
                stage=exc.current_step,
                retryable=False,
            ) from exc
        except ModelGatewayCallError as exc:
            raise CodeReviewExecutorError(
                "Code review executor failed",
                executor_type=executor_type,
                executor_name=executor_name,
                stage="execute",
                retryable=True,
                model_log=exc.log,
            ) from exc
        return coerce_code_review_executor_result(
            (output, model_log),
            executor_type=executor_type,
            executor_name=executor_name,
        )

    if executor_type == "claude_code_skill":
        executor = ExternalCommandCodeReviewExecutor(
            command=settings.code_review_executor_command,
            executor_type=executor_type,
            executor_name=executor_name,
            timeout_seconds=settings.code_review_executor_timeout_seconds,
        )
        return executor.execute(current_store=current_store, task=task, payload=payload)

    raise CodeReviewExecutorError(
        "Unsupported code review executor type",
        executor_type=executor_type,
        executor_name=executor_name,
        stage="configure",
        retryable=False,
    )


def create_code_review_report(
    current_store: Any,
    *,
    task: dict[str, Any],
    output: dict[str, Any],
    uses_repository_context: Callable[[Any], bool],
) -> dict[str, Any]:
    snapshot_id = task["input_json"]["gitlab_mr_snapshot_id"]
    report_id = current_store.new_id("report")
    report = {
        "id": report_id,
        "task_id": task["id"],
        "gitlab_mr_snapshot_id": snapshot_id,
        "summary": output["summary"],
        "risk_level": output["risk_level"],
        "findings": output["findings"],
        "executor": output["executor"],
        "status": "pending_review",
        "review_id": None,
        "archived_at": None,
        "gitlab_writeback_performed": False,
    }
    if not uses_repository_context(current_store):
        current_store.code_review_reports[report_id] = report
    task["code_review_report_id"] = report_id
    return report
