from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error, require_roles
from app.core.code_review_executor import CodeReviewExecutorError
from app.core.repositories.rd_collaboration import RdCollaborationRepositoryError
from app.services.model_gateway import (
    ModelGatewayCallError,
    ModelGatewayConfigError,
    call_model_gateway_for_task,
)
from app.services.operational_records import read_memory_dict
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
from app.services.task_creation import _collaboration_record, create_ai_task_for_work_item
from app.services.task_graph_runtime import start_graph_run
from app.services.task_persistence_helpers import (
    record_audit_event,
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


def _work_item_execution_records(
    current_store: Any,
    collection_name: str,
) -> dict[str, dict[str, Any]]:
    return read_memory_dict(current_store, collection_name)


def _active_work_item_dispatch_replay(
    current_store: Any,
    *,
    collaboration_run_id: str,
    work_item_id: str,
) -> dict[str, Any] | None:
    """Read the committed dispatch after another transaction won the claim race."""
    repository = getattr(current_store, "repository", None)
    if repository is None:
        return None
    load_tasks = getattr(repository, "load_ai_tasks", None)
    list_attempts = getattr(repository, "list_rd_work_item_attempts", None)
    list_runner_tasks = getattr(repository, "list_ai_executor_tasks", None)
    if not all(callable(method) for method in (load_tasks, list_attempts, list_runner_tasks)):
        return None
    loaded = load_tasks()
    tasks = loaded.get("ai_tasks", {}) if isinstance(loaded, dict) else {}
    task = next(
        (
            dict(candidate)
            for candidate in tasks.values()
            if isinstance(candidate, dict)
            and candidate.get("collaboration_run_id") == collaboration_run_id
            and candidate.get("work_item_id") == work_item_id
            and candidate.get("status") not in {"cancelled", "failed", "completed"}
        ),
        None,
    )
    if task is None:
        return None
    attempts = [
        dict(candidate)
        for candidate in list_attempts(work_item_id)
        if isinstance(candidate, dict) and candidate.get("status") in {"claimed", "running"}
    ]
    if len(attempts) != 1:
        return None
    attempt = attempts[0]
    runner_task = next(
        (
            dict(candidate)
            for candidate in list_runner_tasks(ai_task_id=task["id"])
            if isinstance(candidate, dict)
            and (candidate.get("input_payload") or {}).get("rd_work_item_attempt_id")
            == attempt["id"]
        ),
        None,
    )
    if runner_task is None:
        return None
    return {"task": task, "attempt": attempt, "runner_task": runner_task, "idempotent_replay": True}


def _frozen_work_item_execution_policy(
    *,
    current_store: Any,
    executor_profile: dict[str, Any],
    strategy_snapshot: dict[str, Any],
    task: dict[str, Any],
    work_item: dict[str, Any],
) -> dict[str, Any]:
    """Translate an immutable strategy snapshot to the existing Runner contract.

    The result deliberately has no current policy lookup.  Runner selection is
    limited to the profile frozen on the run seat, so changing an active policy
    or executor profile after dispatch cannot redirect the work item.
    """
    payload = strategy_snapshot.get("payload_json") or {}
    autonomy = (
        payload.get("autonomy_config") if isinstance(payload.get("autonomy_config"), dict) else {}
    )
    quality = (
        payload.get("quality_gate_config")
        if isinstance(payload.get("quality_gate_config"), dict)
        else {}
    )
    git = payload.get("git_config") if isinstance(payload.get("git_config"), dict) else {}
    workspace_root = str(git.get("workspace_root") or "").strip()
    if not workspace_root:
        raise api_error(
            409,
            "RD_EXECUTION_POLICY_REQUIRED",
            "Frozen strategy snapshot is missing workspace_root",
        )
    executor_type = str(executor_profile.get("executor_type") or "").strip()
    runner_id = str(executor_profile.get("runner_id") or "").strip()
    if not executor_type or not runner_id:
        raise api_error(409, "RD_EXECUTOR_UNAVAILABLE", "Frozen executor profile has no runner")
    mode = str(autonomy.get("mode") or "single_pass").strip()
    quality_gate_policy_id = str(quality.get("quality_gate_policy_id") or "").strip() or None
    quality_gate_policy_snapshot: dict[str, Any] | None = None
    if quality_gate_policy_id:
        candidates = read_memory_dict(current_store, "quality_gate_policies")
        candidate = candidates.get(quality_gate_policy_id)
        if isinstance(candidate, dict):
            quality_gate_policy_snapshot = deepcopy(candidate)
    execution_snapshot = {
        "snapshot_schema_version": 1,
        "source_snapshot_id": strategy_snapshot["id"],
        "source_policy_id": strategy_snapshot.get("policy_id"),
        "source_policy_version": strategy_snapshot.get("policy_version"),
        "source_schema_version": strategy_snapshot.get("schema_version"),
        "source_content_hash": strategy_snapshot.get("content_hash"),
        "executor_profile": {
            "id": executor_profile["id"],
            "executor_type": executor_type,
            "runner_id": runner_id,
        },
        "autonomy_config": deepcopy(autonomy),
        "git_config": deepcopy(git),
        "quality_gate_config": deepcopy(quality),
        "quality_gate_policy_snapshot": quality_gate_policy_snapshot,
        "work_item_output_contract": deepcopy(work_item.get("output_contract") or {}),
        "resolved_executor_policy": {
            "id": strategy_snapshot.get("policy_id"),
            "autonomy_mode": "autonomous_loop" if mode == "autonomous_loop" else "single_pass",
            "auto_merge_risk_threshold": str(
                quality.get("auto_merge_risk_threshold") or "low"
            ),
            "code_change_review_mode": str(
                quality.get("code_change_review_mode") or "manual_review"
            ),
            "cost_budget": autonomy.get("cost_budget"),
            "max_duration_seconds": int(autonomy.get("max_duration_seconds") or 3600),
            "max_iterations": int(autonomy.get("max_iterations") or 1),
            "quality_gate_policy_id": quality_gate_policy_id,
            "token_budget": autonomy.get("token_budget"),
        },
    }
    return {
        "id": f"snapshot:{strategy_snapshot['id']}:work-item:{work_item['id']}",
        "executor_type": executor_type,
        "runner_id": runner_id,
        "workspace_root": workspace_root,
        "branch": git.get("branch"),
        "repository_id": git.get("repository_id"),
        "instruction_template": (
            "Execute the frozen R&D collaboration work item {{task_id}}. "
            "Respect the supplied input/output contracts and provide test evidence."
        ),
        "output_contract": dict(work_item.get("output_contract") or {}),
        "timeout_seconds": int(autonomy.get("timeout_seconds") or 1800),
        "autonomy_mode": "autonomous_loop" if mode == "autonomous_loop" else "single_pass",
        "max_iterations": int(autonomy.get("max_iterations") or 1),
        "max_duration_seconds": int(autonomy.get("max_duration_seconds") or 3600),
        "token_budget": autonomy.get("token_budget"),
        "cost_budget": autonomy.get("cost_budget"),
        "quality_gate_policy_id": quality_gate_policy_id,
        "code_change_review_mode": str(quality.get("code_change_review_mode") or "manual_review"),
        "auto_merge_risk_threshold": str(quality.get("auto_merge_risk_threshold") or "low"),
        "task_type": task["task_type"],
        "rd_execution_policy_snapshot": execution_snapshot,
    }


def dispatch_ai_task_for_work_item(
    current_store: Any,
    *,
    collaboration_run_id: str,
    work_item_id: str,
) -> dict[str, Any]:
    """Dispatch a ready AI work item through its frozen employee/executor pair.

    This internal command is the only bridge from a collaboration work item to
    the legacy AI-task/Agent Loop/Runner pipeline.  It does not call the public
    task start endpoint, and cannot silently fall back to a current executor
    policy, model gateway, or deterministic execution mode.
    """
    repository = getattr(current_store, "repository", None)
    created = create_ai_task_for_work_item(
        current_store,
        collaboration_run_id=collaboration_run_id,
        work_item_id=work_item_id,
        # PostgreSQL task and Runner rows must only become visible with the
        # claimed work item, attempt, event and audit bundle below.
        persist=repository is None,
    )
    task = dict(created["task"])
    run = _collaboration_record(current_store, "rd_collaboration_runs", collaboration_run_id)
    work_item = _collaboration_record(current_store, "rd_work_items", work_item_id)
    if (
        run is None
        or work_item is None
        or work_item.get("collaboration_run_id") != collaboration_run_id
    ):
        raise api_error(404, "NOT_FOUND", "Collaboration work item was not found")
    if work_item.get("status") not in {"ready", "rework_required"}:
        replay = _active_work_item_dispatch_replay(
            current_store,
            collaboration_run_id=collaboration_run_id,
            work_item_id=work_item_id,
        )
        if replay is not None:
            return replay
        raise api_error(409, "RD_WORK_ITEM_NOT_READY", "Work item is not ready for dispatch")
    owner = _collaboration_record(
        current_store,
        "rd_run_seats",
        str(work_item.get("owner_seat_id") or ""),
    )
    snapshot = _collaboration_record(
        current_store,
        "rd_task_executor_policy_snapshots",
        str(run.get("strategy_snapshot_id") or ""),
    )
    profile = _collaboration_record(
        current_store,
        "rd_executor_profiles",
        str((owner or {}).get("executor_profile_id") or ""),
    )
    if (
        owner is None
        or owner.get("subject_type") != "ai_employee"
        or owner.get("status") != "active"
        or not owner.get("ai_employee_id")
        or profile is None
        or profile.get("status") != "active"
        or snapshot is None
    ):
        raise api_error(
            409,
            "RD_ROLE_ASSIGNMENT_REQUIRED",
            "Work item no longer has its frozen AI employee/executor assignment",
        )

    list_attempts = getattr(repository, "list_rd_work_item_attempts", None)
    persisted_attempts = list_attempts(work_item_id) if callable(list_attempts) else None
    attempt_store = _work_item_execution_records(current_store, "rd_work_item_attempts")
    attempts = (
        [dict(attempt) for attempt in persisted_attempts if isinstance(attempt, dict)]
        if isinstance(persisted_attempts, list)
        else list(attempt_store.values())
    )
    active_attempt = next(
        (
            attempt
            for attempt in attempts
            if attempt.get("work_item_id") == work_item_id
            and attempt.get("status") in {"claimed", "running"}
        ),
        None,
    )
    if active_attempt is not None:
        list_runner_tasks = getattr(repository, "list_ai_executor_tasks", None)
        persisted_runner_tasks = (
            list_runner_tasks(ai_task_id=task["id"]) if callable(list_runner_tasks) else None
        )
        runner_tasks = (
            [dict(candidate) for candidate in persisted_runner_tasks if isinstance(candidate, dict)]
            if isinstance(persisted_runner_tasks, list)
            else list(_work_item_execution_records(current_store, "ai_executor_tasks").values())
        )
        runner_task = next(
            (
                runner_task
                for runner_task in runner_tasks
                if runner_task.get("ai_task_id") == task["id"]
                and (runner_task.get("input_payload") or {}).get("rd_work_item_attempt_id")
                == active_attempt["id"]
            ),
            None,
        )
        if runner_task is not None:
            return {
                "task": task,
                "attempt": dict(active_attempt),
                "runner_task": dict(runner_task),
                "idempotent_replay": True,
            }
        raise api_error(409, "RD_WORK_ITEM_NOT_READY", "Work item already has an active dispatch")

    attempt_no = 1 + max(
        (
            int(candidate.get("attempt_no") or 0)
            for candidate in attempts
            if candidate.get("work_item_id") == work_item_id
        ),
        default=0,
    )
    now = datetime.now(UTC).isoformat()
    attempt = {
        "id": current_store.new_id("rd_work_item_attempt"),
        "work_item_id": work_item_id,
        "attempt_no": attempt_no,
        "idempotency_key": f"ai-dispatch:{task['id']}:attempt:{attempt_no}",
        "lease_id": current_store.new_id("rd_lease"),
        # Runner events are also fenced by this immutable attempt id.  The
        # opaque token is not exposed because an AI seat does not receive a
        # public claim credential.
        "lease_token_hash": None,
        "status": "running",
        "executor_profile_id": profile["id"],
        "ai_employee_id": owner["ai_employee_id"],
        "input_json": {"task_id": task["id"], "strategy_snapshot_id": snapshot["id"]},
        "result_json": None,
        "failure_json": None,
        "rework_evidence": [],
        "claimed_at": now,
        "started_at": now,
        "completed_at": None,
    }
    policy = _frozen_work_item_execution_policy(
        current_store=current_store,
        executor_profile=profile,
        strategy_snapshot=snapshot,
        task=task,
        work_item=work_item,
    )
    system_actor = {
        # Context-manifest / Runner rows are foreign-keyed to a real user.
        # The frozen run creator is the accountable system-dispatch principal;
        # audit events still identify the orchestration actor separately.
        "id": str(run.get("created_by") or "user_admin"),
        "roles": ["admin"],
        "permissions": ["system.admin"],
        "scope_summary": [{"scope_type": "global", "scope_id": "*", "access_level": "admin"}],
    }
    runner_task = queue_rd_task_executor_task(
        current_store=current_store,
        policy=policy,
        task=task,
        user=system_actor,
        persist=repository is None,
    )
    frozen_execution_snapshot = deepcopy(policy["rd_execution_policy_snapshot"])
    runner_task["input_payload"] = {
        **dict(runner_task.get("input_payload") or {}),
        "rd_collaboration_run_id": collaboration_run_id,
        "rd_work_item_attempt_id": attempt["id"],
        "rd_work_item_id": work_item_id,
        "rd_execution_policy_snapshot": frozen_execution_snapshot,
    }
    runner_task["request_config"] = {
        **dict(runner_task.get("request_config") or {}),
        "rd_collaboration_run_id": collaboration_run_id,
        "rd_work_item_attempt_id": attempt["id"],
        "rd_work_item_id": work_item_id,
        "rd_execution_policy_snapshot": frozen_execution_snapshot,
    }
    _work_item_execution_records(current_store, "ai_executor_tasks")[runner_task["id"]] = (
        runner_task
    )

    executor_snapshot = {
        "executor_policy_id": policy["id"],
        "executor_profile_id": profile["id"],
        "executor_type": profile.get("executor_type"),
        "runner_id": profile.get("runner_id"),
        "runner_task_id": runner_task["id"],
        "status": runner_task["status"],
        "workspace_root": runner_task.get("workspace_root"),
    }
    task.update(
        {
            "current_step": "waiting_ai_executor",
            "input_json": {
                **dict(task.get("input_json") or {}),
                "executor": executor_snapshot,
                "rd_collaboration": {
                    **dict((task.get("input_json") or {}).get("rd_collaboration") or {}),
                    "attempt_id": attempt["id"],
                    "execution_policy_snapshot": frozen_execution_snapshot,
                },
            },
            "status": "running",
            "updated_at": now,
        }
    )
    work_item.update(
        {
            "ai_task_id": task["id"],
            "lease_owner": owner["id"],
            "status": "running",
            "version": int(work_item.get("version") or 1) + 1,
        }
    )
    audit_event = record_audit_event(
        current_store,
        event_type="rd_work_item.ai_task_dispatched",
        actor_id="system",
        ai_task_id=task["id"],
        subject_type="rd_work_item",
        subject_id=work_item_id,
        payload={
            "attempt_id": attempt["id"],
            "executor_profile_id": profile["id"],
            "runner_id": runner_task["runner_id"],
            "runner_task_id": runner_task["id"],
        },
    )
    dispatch_bundle = getattr(repository, "dispatch_work_item_execution_bundle", None)
    if callable(dispatch_bundle):
        try:
            persisted = dispatch_bundle(
                work_item_id=work_item_id,
                expected_version=int(work_item["version"]) - 1,
                task=task,
                requirement=created.get("requirement"),
                runner_task=runner_task,
                attempt=attempt,
                event={
                    "id": current_store.new_id("rd_collaboration_event"),
                    "collaboration_run_id": collaboration_run_id,
                    "event_type": "work_item.ai_task_dispatched",
                    "event_key": f"work-item-dispatch:{work_item_id}:{attempt['id']}",
                    "subject_type": "rd_work_item",
                    "subject_id": work_item_id,
                    "payload_json": {
                        "attempt_id": attempt["id"],
                        "ai_task_id": task["id"],
                        "runner_task_id": runner_task["id"],
                    },
                    "occurred_at": now,
                },
                audit_events=[
                    event
                    for event in (created.get("creation_audit_event"), audit_event)
                    if isinstance(event, dict)
                ],
            )
        except RdCollaborationRepositoryError as exc:
            if exc.code != "RD_WORK_ITEM_STATE_INVALID":
                raise
            replay = _active_work_item_dispatch_replay(
                current_store,
                collaboration_run_id=collaboration_run_id,
                work_item_id=work_item_id,
            )
            if replay is None:
                raise
            return replay
        return {
            "task": dict(persisted["task"]),
            "attempt": dict(persisted["attempt"]),
            "runner_task": dict(persisted["runner_task"]),
            "idempotent_replay": False,
        }

    # MemoryStore is a test-only command fixture; collaboration record reads
    # return defensive copies, so explicitly write the canonical fixture row.
    _work_item_execution_records(current_store, "rd_work_items")[work_item["id"]] = work_item
    attempt_store[attempt["id"]] = attempt
    _work_item_execution_records(current_store, "ai_tasks")[task["id"]] = task
    return {
        "task": task,
        "attempt": attempt,
        "runner_task": runner_task,
        "idempotent_replay": False,
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
        task["status"] == "failed" and task.get("current_step") in RETRYABLE_TASK_FAILURE_STEPS
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
