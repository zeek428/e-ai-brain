from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_roles
from app.core.code_review_executor import CodeReviewExecutorError
from app.services.model_gateway import (
    ModelGatewayCallError,
    ModelGatewayConfigError,
    call_model_gateway_for_task,
)
from app.services.rd_requirement_entry_adapters import require_v2_task_work_item_entrypoint
from app.services.rd_task_executor_policies import (
    queue_rd_task_executor_task,
    resolve_rd_task_executor_policy,
)
from app.services.task_access import require_task_permission_or_roles
from app.services.task_code_review_execution import (
    call_configured_code_review_executor,
    create_code_review_report,
)
from app.services.task_contexts import public_product_context
from app.services.task_graph_runtime import start_graph_run
from app.services.task_persistence_helpers import (
    save_task_start_records,
    save_task_state_records,
    uses_repository_context,
)
from app.services.task_workflow_context import task_workflow_write_store

RETRYABLE_TASK_FAILURE_STEPS = {
    "code_review_executor_failed",
    "executor_failed",
    "model_gateway_failed",
}


def deterministic_task_output(task: dict[str, Any]) -> dict[str, Any]:
    task_type = str(task.get("task_type") or "unknown")
    requirement = task.get("requirement_snapshot") or {}
    title = str(task.get("title") or requirement.get("title") or task_type)
    requirement_title = str(requirement.get("title") or title)
    output = {
        "acceptance_points": [
            "需求、迭代版本、任务、Review 和知识沉淀链路可被回归脚本验证。",
            "该输出由显式 deterministic 执行模式生成，不代表模型网关真实生成结果。",
        ],
        "generated_by": "ai_brain_deterministic_execution",
        "kind": task_type,
        "summary": f"确定性验收输出：{requirement_title}",
        "title": title,
    }
    if task_type == "code_review":
        output.update(
            {
                "executor": {
                    "executor_name": "deterministic",
                    "executor_type": "local",
                    "stage": "execute",
                },
                "findings": [],
                "risk_level": "low",
            }
        )
    return output


def start_ai_task_response(
    *,
    code_review_executor: Any | None = None,
    current_store: Any,
    execution_mode: str | None = None,
    execution_reason: str | None = None,
    opener: Any | None = None,
    task_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    write_store = task_workflow_write_store(current_store)
    task = write_store.ai_tasks.get(task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI task not found")
    require_v2_task_work_item_entrypoint(task, entrypoint="ai_tasks.start")
    is_retry_start = (
        task["status"] == "failed"
        and task.get("current_step") in RETRYABLE_TASK_FAILURE_STEPS
    )
    require_task_permission_or_roles(
        user,
        task,
        {"task.retry"} if is_retry_start else {"task.execute"},
    )
    if task["status"] != "draft" and not is_retry_start:
        raise api_error(409, "TASK_STATE_INVALID", "Task cannot be started from current status")
    audit_start_index = len(write_store.audit_events)
    if is_retry_start:
        write_store.audit(
            event_type="ai_task.retry_started",
            actor_id=user["id"],
            ai_task_id=task_id,
            subject_type="ai_task",
            subject_id=task_id,
            payload={"previous_step": task.get("current_step")},
        )

    executor_policy = (
        None
        if execution_mode == "deterministic"
        else resolve_rd_task_executor_policy(write_store, task)
    )
    if executor_policy is not None:
        executor_task = queue_rd_task_executor_task(
            current_store=write_store,
            policy=executor_policy,
            task=task,
            user=user,
        )
        now = datetime.now(UTC).isoformat()
        executor_snapshot = {
            "executor_policy_id": executor_policy["id"],
            "executor_type": executor_task["executor_type"],
            "runner_id": executor_task["runner_id"],
            "runner_task_id": executor_task["id"],
            "status": executor_task["status"],
            "workspace_root": executor_task["workspace_root"],
        }
        task["current_step"] = "waiting_ai_executor"
        task["input_json"] = {
            **dict(task.get("input_json") or {}),
            "executor": executor_snapshot,
        }
        task["status"] = "running"
        task["updated_at"] = now
        write_store.audit(
            event_type="ai_task.started",
            actor_id=user["id"],
            ai_task_id=task_id,
            subject_type="ai_task",
            subject_id=task_id,
            payload={"execution_route": "ai_executor"},
        )
        write_store.audit(
            event_type="ai_task.executor_queued",
            actor_id="system",
            ai_task_id=task_id,
            subject_type="ai_executor_task",
            subject_id=executor_task["id"],
            payload=executor_snapshot,
        )
        save_task_state_records(
            write_store,
            task=task,
            audit_events=write_store.audit_events[audit_start_index:],
        )
        return {
            "current_step": task["current_step"],
            "executor_policy_id": executor_policy["id"],
            "executor_task_id": executor_task["id"],
            "id": task_id,
            "runner_id": executor_task["runner_id"],
            "status": task["status"],
        }

    if execution_mode == "deterministic":
        require_roles(user, {"admin"})
        task["output_json"] = deterministic_task_output(task)
        model_log = None
        executor_meta = {
            "executor_name": "deterministic",
            "executor_type": "local",
            "retryable": False,
        }
        audit_payload: dict[str, Any] = {
            "execution_mode": "deterministic",
            "task_type": task["task_type"],
        }
        if execution_reason:
            audit_payload["reason"] = execution_reason
        write_store.audit(
            event_type="ai_task.deterministic_execution_used",
            actor_id=user["id"],
            ai_task_id=task_id,
            subject_type="ai_task",
            subject_id=task_id,
            payload=audit_payload,
        )
    elif task["task_type"] == "code_review":
        try:
            executor_result = call_configured_code_review_executor(
                write_store,
                code_review_executor=code_review_executor,
                opener=opener,
                public_product_context=public_product_context,
                task=task,
            )
            task["output_json"] = executor_result.output
            model_log = executor_result.model_log
            executor_meta = executor_result.executor
        except CodeReviewExecutorError as exc:
            now = datetime.now(UTC).isoformat()
            task["status"] = "failed"
            task["current_step"] = "code_review_executor_failed"
            task["updated_at"] = now
            if exc.model_log is not None:
                write_store.audit(
                    event_type="model_gateway.called",
                    actor_id="system",
                    ai_task_id=task_id,
                    subject_type="model_gateway_log",
                    subject_id=exc.model_log["id"],
                    payload={
                        "model_log_id": exc.model_log["id"],
                        "provider": exc.model_log["provider"],
                        "model": exc.model_log["model"],
                        "purpose": exc.model_log["purpose"],
                        "status": exc.model_log["status"],
                    },
                )
            payload = {
                "current_step": task["current_step"],
                "executor_name": exc.executor_name,
                "executor_type": exc.executor_type,
                "retryable": exc.retryable,
                "stage": exc.stage,
            }
            if exc.model_log is not None:
                payload["model_log_id"] = exc.model_log["id"]
            write_store.audit(
                event_type="code_review.executor_failed",
                actor_id="system",
                ai_task_id=task_id,
                subject_type="ai_task",
                subject_id=task_id,
                payload=payload,
            )
            write_store.audit(
                event_type="ai_task.failed",
                actor_id="system",
                ai_task_id=task_id,
                subject_type="ai_task",
                subject_id=task_id,
                payload={
                    "current_step": task["current_step"],
                    "reason": "code_review_executor_failed",
                },
            )
            save_task_state_records(
                write_store,
                task=task,
                model_log=exc.model_log,
                audit_events=write_store.audit_events[audit_start_index:],
            )
            raise api_error(
                502,
                "CODE_REVIEW_EXECUTOR_FAILED",
                "Code review executor failed",
            ) from exc
    else:
        try:
            task["output_json"], model_log = call_model_gateway_for_task(
                write_store,
                opener=opener,
                task=task,
            )
        except ModelGatewayConfigError as exc:
            now = datetime.now(UTC).isoformat()
            task["status"] = "failed"
            task["current_step"] = exc.current_step
            task["updated_at"] = now
            write_store.audit(
                event_type="ai_task.failed",
                actor_id="system",
                ai_task_id=task_id,
                subject_type="ai_task",
                subject_id=task_id,
                payload={
                    "current_step": task["current_step"],
                    "reason": "model_gateway_config_invalid",
                },
            )
            save_task_state_records(
                write_store,
                task=task,
                audit_events=write_store.audit_events[audit_start_index:],
            )
            raise api_error(400, "MODEL_GATEWAY_CONFIG_INVALID", str(exc)) from exc
        except ModelGatewayCallError as exc:
            now = datetime.now(UTC).isoformat()
            task["status"] = "failed"
            task["current_step"] = "model_gateway_failed"
            task["updated_at"] = now
            write_store.audit(
                event_type="model_gateway.called",
                actor_id="system",
                ai_task_id=task_id,
                subject_type="model_gateway_log",
                subject_id=exc.log["id"],
                payload={
                    "model_log_id": exc.log["id"],
                    "provider": exc.log["provider"],
                    "model": exc.log["model"],
                    "purpose": exc.log["purpose"],
                    "status": exc.log["status"],
                },
            )
            write_store.audit(
                event_type="ai_task.failed",
                actor_id="system",
                ai_task_id=task_id,
                subject_type="ai_task",
                subject_id=task_id,
                payload={
                    "current_step": task["current_step"],
                    "reason": "model_gateway_failed",
                },
            )
            save_task_state_records(
                write_store,
                task=task,
                model_log=exc.log,
                audit_events=write_store.audit_events[audit_start_index:],
            )
            raise api_error(502, "MODEL_GATEWAY_FAILED", "Model gateway request failed") from exc

    now = datetime.now(UTC).isoformat()
    task["status"] = "waiting_review"
    task["updated_at"] = now
    if model_log is not None:
        write_store.audit(
            event_type="model_gateway.called",
            actor_id="system",
            ai_task_id=task_id,
            subject_type="model_gateway_log",
            subject_id=model_log["id"],
            payload={
                "model_log_id": model_log["id"],
                "provider": model_log["provider"],
                "model": model_log["model"],
                "purpose": model_log["purpose"],
                "status": model_log["status"],
            },
        )
    if task["task_type"] == "code_review":
        write_store.audit(
            event_type="code_review.executor_called",
            actor_id="system",
            ai_task_id=task_id,
            subject_type="ai_task",
            subject_id=task_id,
            payload={
                "executor_name": executor_meta["executor_name"],
                "executor_type": executor_meta["executor_type"],
                "retryable": executor_meta["retryable"],
                "stage": "execute",
            },
        )
    write_store.audit(
        event_type="ai_task.started",
        actor_id=user["id"],
        ai_task_id=task_id,
        subject_type="ai_task",
        subject_id=task_id,
    )
    code_review_report = None
    if task["task_type"] == "code_review":
        report = create_code_review_report(
            write_store,
            task=task,
            output=task["output_json"],
            uses_repository_context=uses_repository_context,
        )
        code_review_report = report
        write_store.audit(
            event_type="code_review.generated",
            actor_id="system",
            ai_task_id=task_id,
            subject_type="code_review_report",
            subject_id=report["id"],
            payload={"risk_level": report["risk_level"]},
        )

    review_id = write_store.new_id("review")
    review = {
        "id": review_id,
        "ai_task_id": task_id,
        "stage": task["task_type"],
        "status": "pending",
        "version": 1,
        "content": write_store.snapshot(task["output_json"]),
        "created_at": now,
        "updated_at": now,
    }
    if not uses_repository_context(write_store):
        write_store.human_reviews[review_id] = review
    task.setdefault("review_ids", []).append(review_id)
    if task["task_type"] == "code_review":
        report_id = task.get("code_review_report_id")
        if code_review_report is not None:
            code_review_report = {**code_review_report, "review_id": review_id}
        elif report_id is not None:
            write_store.code_review_reports[report_id]["review_id"] = review_id
            code_review_report = write_store.code_review_reports[report_id]
    graph_run, checkpoint = start_graph_run(write_store, task=task, review_id=review_id)
    write_store.audit(
        event_type="human_review.created",
        actor_id="system",
        ai_task_id=task_id,
        subject_type="human_review",
        subject_id=review_id,
    )
    save_task_start_records(
        write_store,
        task=task,
        review=review,
        graph_run=graph_run,
        checkpoint=checkpoint,
        model_log=model_log,
        code_review_report=code_review_report,
        audit_events=write_store.audit_events[audit_start_index:],
    )
    return {
        "id": task_id,
        "status": task["status"],
        "review_id": review_id,
        "graph_run_id": graph_run["id"],
        "checkpoint_id": graph_run["checkpoint_id"],
        "current_step": graph_run["current_step"],
    }
