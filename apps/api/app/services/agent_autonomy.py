from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.api.deps import api_error
from app.services.ai_executor_task_creation import create_ai_executor_task
from app.services.execution_context_manifests import (
    build_and_save_execution_context_manifest,
    execution_context_manifest_for_task,
)
from app.services.operational_records import read_memory_dict, record_audit_event
from app.services.quality_gates import quality_gate_allows_auto_merge

SAFETY_STOP_REASON_CODES = {
    "DATABASE_MIGRATION_REQUIRES_MANUAL_REVIEW",
    "HIGH_RISK_TASK_REQUIRES_MANUAL_REVIEW",
    "PROTECTED_PATH_REQUIRES_MANUAL_REVIEW",
    "SECURITY_FINDING",
}
TOKEN_USAGE_PATTERN = re.compile(r"(?i)tokens?\s+used\s*\n?\s*([0-9,]+)")
ACTIVE_AGENT_LOOP_STATUSES = {"executing", "verifying"}


def autonomy_enabled(policy: dict[str, Any] | None) -> bool:
    return str((policy or {}).get("autonomy_mode") or "single_pass") == "autonomous_loop"


def _save_loop_bundle(
    current_store: Any,
    *,
    audit_events: list[dict[str, Any]],
    iterations: list[dict[str, Any]],
    run: dict[str, Any],
) -> None:
    repository = getattr(current_store, "repository", None)
    save_bundle = getattr(repository, "save_agent_loop_bundle_record", None)
    if callable(save_bundle):
        save_bundle(audit_events=audit_events, iterations=iterations, run=run)
        return
    read_memory_dict(current_store, "agent_loop_runs")[run["id"]] = deepcopy(run)
    iteration_store = read_memory_dict(current_store, "agent_loop_iterations")
    for iteration in iterations:
        iteration_store[iteration["id"]] = deepcopy(iteration)


def _loop_and_iterations(
    current_store: Any,
    *,
    ai_task_id: str | None = None,
    loop_run_id: str | None = None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    repository = getattr(current_store, "repository", None)
    list_runs = getattr(repository, "list_agent_loop_runs", None)
    list_iterations = getattr(repository, "list_agent_loop_iterations", None)
    if callable(list_runs) and callable(list_iterations):
        runs = list(list_runs(ai_task_id=ai_task_id))
        run = next(
            (
                item
                for item in runs
                if loop_run_id is None or item.get("id") == loop_run_id
            ),
            None,
        )
        return run, list(list_iterations(run["id"])) if run else []
    runs = list(read_memory_dict(current_store, "agent_loop_runs").values())
    run = next(
        (
            item
            for item in runs
            if (ai_task_id is None or item.get("ai_task_id") == ai_task_id)
            and (loop_run_id is None or item.get("id") == loop_run_id)
        ),
        None,
    )
    if run is None:
        return None, []
    iterations = [
        item
        for item in read_memory_dict(current_store, "agent_loop_iterations").values()
        if item.get("loop_run_id") == run["id"]
    ]
    iterations.sort(key=lambda item: int(item.get("iteration_number") or 0))
    return deepcopy(run), [deepcopy(item) for item in iterations]


def start_agent_loop(
    current_store: Any,
    *,
    context_manifest: dict[str, Any],
    policy: dict[str, Any],
    task: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    now = datetime.now(UTC).isoformat()
    run = {
        "id": current_store.new_id("agent_loop_run"),
        "ai_task_id": task["id"],
        "product_id": task.get("product_id"),
        "objective": {
            "acceptance_criteria": context_manifest.get("acceptance_criteria") or [],
            "requirement_refs": context_manifest.get("requirement_refs") or [],
            "task_id": task["id"],
            "task_title": task.get("title"),
            "task_type": task.get("task_type"),
        },
        "status": "executing",
        "current_iteration": 1,
        "max_iterations": int(policy.get("max_iterations") or 3),
        "max_duration_seconds": int(policy.get("max_duration_seconds") or 3600),
        "token_budget": policy.get("token_budget"),
        "cost_budget": policy.get("cost_budget"),
        "token_used": 0,
        "cost_used": 0,
        "context_manifest_id": context_manifest["id"],
        "context_version": int(context_manifest.get("version") or 1),
        "quality_gate_policy_id": policy.get("quality_gate_policy_id"),
        "stop_reason": None,
        "started_at": now,
        "finished_at": None,
        "version": 1,
        "created_by": task.get("created_by"),
        "created_at": now,
        "updated_at": now,
    }
    iteration = {
        "id": current_store.new_id("agent_loop_iteration"),
        "loop_run_id": run["id"],
        "iteration_number": 1,
        "coding_runner_task_id": None,
        "verifier_runner_task_id": None,
        "quality_gate_run_id": None,
        "status": "executing",
        "plan": {},
        "change_summary": None,
        "test_evidence": [],
        "failure_analysis": {},
        "verification_summary": {},
        "context_version": run["context_version"],
        "token_usage": 0,
        "cost_amount": 0,
        "started_at": now,
        "finished_at": None,
        "created_at": now,
        "updated_at": now,
    }
    audit = record_audit_event(
        current_store,
        event_type="agent_loop.started",
        actor_id=str(task.get("created_by") or "system"),
        subject_type="agent_loop_run",
        subject_id=run["id"],
        payload={
            "ai_task_id": task["id"],
            "context_manifest_id": context_manifest["id"],
            "max_duration_seconds": run["max_duration_seconds"],
            "max_iterations": run["max_iterations"],
        },
    )
    _save_loop_bundle(current_store, audit_events=[audit], iterations=[iteration], run=run)
    return deepcopy(run), deepcopy(iteration)


def attach_agent_loop_coding_task(
    current_store: Any,
    *,
    coding_runner_task_id: str,
    iteration_id: str,
    loop_run_id: str,
) -> None:
    run, iterations = _loop_and_iterations(current_store, loop_run_id=loop_run_id)
    if run is None:
        return
    iteration = next((item for item in iterations if item["id"] == iteration_id), None)
    if iteration is None:
        return
    iteration["coding_runner_task_id"] = coding_runner_task_id
    iteration["updated_at"] = datetime.now(UTC).isoformat()
    _save_loop_bundle(current_store, audit_events=[], iterations=[iteration], run=run)


def _tokens_and_cost(result: dict[str, Any]) -> tuple[int, float]:
    usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
    token_usage = int(
        result.get("token_usage")
        or result.get("tokens_used")
        or usage.get("total_tokens")
        or 0
    )
    if token_usage <= 0:
        match = TOKEN_USAGE_PATTERN.search(str(result.get("output_preview") or ""))
        if match:
            token_usage = int(match.group(1).replace(",", ""))
    cost_amount = float(result.get("cost_amount") or usage.get("cost") or 0)
    return token_usage, cost_amount


def record_agent_coding_completed(
    current_store: Any,
    *,
    coding_runner_task: dict[str, Any],
    quality_gate_run_id: str,
    verifier_runner_task_id: str,
) -> None:
    loop_run_id = str(coding_runner_task.get("agent_loop_run_id") or "")
    iteration_id = str(coding_runner_task.get("agent_loop_iteration_id") or "")
    if not loop_run_id or not iteration_id:
        return
    run, iterations = _loop_and_iterations(current_store, loop_run_id=loop_run_id)
    if run is None:
        return
    iteration = next((item for item in iterations if item["id"] == iteration_id), None)
    if iteration is None:
        return
    result = (
        coding_runner_task.get("result_json")
        if isinstance(coding_runner_task.get("result_json"), dict)
        else {}
    )
    agent_iteration = (
        result.get("agent_iteration")
        if isinstance(result.get("agent_iteration"), dict)
        else {}
    )
    token_usage, cost_amount = _tokens_and_cost(result)
    now = datetime.now(UTC).isoformat()
    iteration.update(
        {
            "coding_runner_task_id": coding_runner_task["id"],
            "verifier_runner_task_id": verifier_runner_task_id,
            "quality_gate_run_id": quality_gate_run_id,
            "status": "verifying",
            "plan": agent_iteration.get("plan") or {},
            "change_summary": agent_iteration.get("change_summary")
            or result.get("summary"),
            "test_evidence": agent_iteration.get("test_evidence") or [],
            "token_usage": token_usage,
            "cost_amount": cost_amount,
            "updated_at": now,
        }
    )
    run.update(
        {
            "status": "verifying",
            "token_used": int(run.get("token_used") or 0) + token_usage,
            "cost_used": float(run.get("cost_used") or 0) + cost_amount,
            "updated_at": now,
            "version": int(run.get("version") or 1) + 1,
        }
    )
    _save_loop_bundle(current_store, audit_events=[], iterations=[iteration], run=run)


def _load_runner_task(current_store: Any, runner_task_id: str) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    list_tasks = getattr(repository, "list_ai_executor_tasks", None)
    if callable(list_tasks):
        return next(
            (item for item in list_tasks() if item.get("id") == runner_task_id),
            None,
        )
    task = read_memory_dict(current_store, "ai_executor_tasks").get(runner_task_id)
    return deepcopy(task) if task else None


def _elapsed_seconds(started_at: Any, now: datetime) -> float:
    if not started_at:
        return 0
    try:
        parsed = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
    except ValueError:
        return 0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return max(0.0, (now - parsed.astimezone(UTC)).total_seconds())


def _retry_stop_reason(run: dict[str, Any], now: datetime) -> str | None:
    if int(run.get("current_iteration") or 0) >= int(run.get("max_iterations") or 1):
        return "max_iterations_reached"
    if _elapsed_seconds(run.get("started_at"), now) >= int(
        run.get("max_duration_seconds") or 3600
    ):
        return "max_duration_reached"
    token_budget = run.get("token_budget")
    if token_budget is not None and int(run.get("token_used") or 0) >= int(token_budget):
        return "token_budget_exhausted"
    cost_budget = run.get("cost_budget")
    if cost_budget is not None and float(run.get("cost_used") or 0) >= float(cost_budget):
        return "cost_budget_exhausted"
    return None


def handle_agent_quality_gate_outcome(
    current_store: Any,
    *,
    ai_task: dict[str, Any],
    executor_policy: dict[str, Any] | None,
    quality_gate_run: dict[str, Any],
    verifier_runner_task: dict[str, Any],
) -> dict[str, Any]:
    loop_run_id = str(verifier_runner_task.get("agent_loop_run_id") or "")
    iteration_id = str(verifier_runner_task.get("agent_loop_iteration_id") or "")
    if not loop_run_id or not iteration_id:
        return {"action": "single_pass"}
    run, iterations = _loop_and_iterations(current_store, loop_run_id=loop_run_id)
    if run is None:
        return {"action": "single_pass"}
    iteration = next((item for item in iterations if item["id"] == iteration_id), None)
    if iteration is None:
        return {"action": "single_pass"}
    now_dt = datetime.now(UTC)
    now = now_dt.isoformat()
    reason_codes = {
        str(reason.get("code"))
        for reason in quality_gate_run.get("blocked_reasons") or []
        if isinstance(reason, dict)
    }
    iteration.update(
        {
            "status": "passed" if quality_gate_run.get("status") == "passed" else "failed",
            "failure_analysis": {
                "blocked_reasons": quality_gate_run.get("blocked_reasons") or [],
                "summary": quality_gate_run.get("summary"),
            },
            "verification_summary": {
                "independent_evidence_count": quality_gate_run.get(
                    "independent_evidence_count"
                ),
                "quality_gate_run_id": quality_gate_run["id"],
                "status": quality_gate_run.get("status"),
            },
            "finished_at": now,
            "updated_at": now,
        }
    )
    if quality_gate_run.get("status") == "passed":
        auto_commit = str(
            (executor_policy or {}).get("code_change_review_mode") or "manual_review"
        ) == "auto_commit"
        complete_without_review = auto_commit and quality_gate_allows_auto_merge(
            quality_gate_run
        )
        run.update(
            {
                "status": "succeeded" if complete_without_review else "waiting_review",
                "stop_reason": None
                if complete_without_review
                else "manual_review_required",
                "finished_at": now
                if complete_without_review
                else None,
                "updated_at": now,
                "version": int(run.get("version") or 1) + 1,
            }
        )
        _save_loop_bundle(current_store, audit_events=[], iterations=[iteration], run=run)
        return {
            "action": "complete" if complete_without_review else "review",
            "loop": run,
        }

    safety_stop = bool(reason_codes.intersection(SAFETY_STOP_REASON_CODES))
    stop_reason = "safety_boundary_triggered" if safety_stop else _retry_stop_reason(run, now_dt)
    if stop_reason:
        run.update(
            {
                "status": "safety_blocked" if safety_stop else "stopped",
                "stop_reason": stop_reason,
                "finished_at": now,
                "updated_at": now,
                "version": int(run.get("version") or 1) + 1,
            }
        )
        audit = record_audit_event(
            current_store,
            event_type="agent_loop.stopped",
            actor_id="system",
            subject_type="agent_loop_run",
            subject_id=run["id"],
            payload={"reason": stop_reason, "reason_codes": sorted(reason_codes)},
        )
        _save_loop_bundle(current_store, audit_events=[audit], iterations=[iteration], run=run)
        return {"action": "review", "loop": run}

    previous_coding_task = _load_runner_task(
        current_store,
        str(iteration.get("coding_runner_task_id") or ""),
    )
    if previous_coding_task is None:
        run.update(
            {
                "status": "stopped",
                "stop_reason": "coding_task_context_missing",
                "finished_at": now,
                "updated_at": now,
            }
        )
        _save_loop_bundle(current_store, audit_events=[], iterations=[iteration], run=run)
        return {"action": "review", "loop": run}
    previous_input = (
        previous_coding_task.get("input_payload")
        if isinstance(previous_coding_task.get("input_payload"), dict)
        else {}
    )
    previous_result = (
        previous_coding_task.get("result_json")
        if isinstance(previous_coding_task.get("result_json"), dict)
        else {}
    )
    workspace_isolation = (
        previous_result.get("workspace_isolation")
        if isinstance(previous_result.get("workspace_isolation"), dict)
        else {}
    )
    previous_manifest = execution_context_manifest_for_task(
        current_store,
        task_id=ai_task["id"],
    ) or {}
    permission = previous_manifest.get("permission_snapshot") or {}
    manifest_user = {
        "id": ai_task.get("created_by") or "system",
        "permissions": permission.get("permissions") or ["system.admin"],
        "roles": permission.get("roles") or ["admin"],
        "scope_summary": permission.get("scopes")
        or [{"access_level": "admin", "scope_id": "*", "scope_type": "global"}],
    }
    next_iteration_number = int(run.get("current_iteration") or 0) + 1
    failure_context = {
        "iteration": next_iteration_number,
        "previous_iteration": iteration["iteration_number"],
        "quality_gate_run_id": quality_gate_run["id"],
        "failure_analysis": iteration["failure_analysis"],
    }
    next_manifest = build_and_save_execution_context_manifest(
        branch=previous_input.get("branch"),
        current_store=current_store,
        iteration_context=failure_context,
        knowledge_references=list(previous_input.get("knowledge_references") or []),
        repository_ref=(ai_task.get("product_context") or {}).get("repository") or {},
        task=ai_task,
        user=manifest_user,
    )
    next_iteration = {
        "id": current_store.new_id("agent_loop_iteration"),
        "loop_run_id": run["id"],
        "iteration_number": next_iteration_number,
        "coding_runner_task_id": None,
        "verifier_runner_task_id": None,
        "quality_gate_run_id": None,
        "status": "executing",
        "plan": {},
        "change_summary": None,
        "test_evidence": [],
        "failure_analysis": {},
        "verification_summary": {},
        "context_version": int(next_manifest.get("version") or 1),
        "token_usage": 0,
        "cost_amount": 0,
        "started_at": now,
        "finished_at": None,
        "created_at": now,
        "updated_at": now,
    }
    retry_instruction = (
        f"{previous_coding_task.get('instruction') or ''}\n\n"
        f"Agent 自治循环第 {next_iteration_number} 轮。先分析上一轮独立门禁失败，"
        "仅针对失败原因修正代码并重新验证；不得绕过、删除或伪造质量检查。\n"
        f"上一轮失败证据：{json.dumps(failure_context, ensure_ascii=False)}"
    )
    retry_task = create_ai_executor_task(
        current_store,
        action_id=None,
        agent_loop_iteration_id=next_iteration["id"],
        agent_loop_run_id=run["id"],
        ai_task_id=ai_task["id"],
        connection_id=None,
        context_manifest_id=next_manifest["id"],
        created_by=str(ai_task.get("created_by") or "system"),
        executor_type=str(previous_coding_task.get("executor_type") or "codex"),
        input_payload={
            **previous_input,
            "agent_loop": failure_context,
            "context_manifest_id": next_manifest["id"],
        },
        instruction=retry_instruction,
        plugin_invocation_log_id=None,
        request_config={
            **dict(previous_coding_task.get("request_config") or {}),
            "agent_loop_iteration": next_iteration_number,
            "context_manifest_id": next_manifest["id"],
            "reuse_workspace": True,
            "workspace_isolation": workspace_isolation,
        },
        runner_id=str(previous_coding_task.get("runner_id") or ""),
        scheduled_job_id=None,
        scheduled_job_run_id=None,
        task_kind="coding",
        timeout_seconds=int(previous_coding_task.get("timeout_seconds") or 1800),
        workspace_root=str(
            workspace_isolation.get("worktree_path")
            or previous_coding_task.get("workspace_root")
            or ""
        ),
    )
    next_iteration["coding_runner_task_id"] = retry_task["id"]
    run.update(
        {
            "status": "executing",
            "current_iteration": next_iteration_number,
            "context_manifest_id": next_manifest["id"],
            "context_version": int(next_manifest.get("version") or 1),
            "stop_reason": None,
            "updated_at": now,
            "version": int(run.get("version") or 1) + 1,
        }
    )
    audit = record_audit_event(
        current_store,
        event_type="agent_loop.retry_queued",
        actor_id="system",
        subject_type="agent_loop_run",
        subject_id=run["id"],
        payload={
            "context_manifest_id": next_manifest["id"],
            "iteration": next_iteration_number,
            "runner_task_id": retry_task["id"],
        },
    )
    _save_loop_bundle(
        current_store,
        audit_events=[audit],
        iterations=[iteration, next_iteration],
        run=run,
    )
    return {"action": "retry", "loop": run, "runner_task": retry_task}


def latest_agent_loop_for_task(
    current_store: Any,
    *,
    product_scope_ids: list[str] | None,
    task_id: str,
) -> dict[str, Any] | None:
    repository = getattr(current_store, "repository", None)
    list_runs = getattr(repository, "list_agent_loop_runs", None)
    list_iterations = getattr(repository, "list_agent_loop_iterations", None)
    if callable(list_runs) and callable(list_iterations):
        runs = list(
            list_runs(ai_task_id=task_id, product_scope_ids=product_scope_ids)
        )
        if not runs:
            return None
        run = runs[0]
        return {**run, "iterations": list(list_iterations(run["id"]))}
    allowed_products = set(product_scope_ids or [])
    runs = [
        run
        for run in read_memory_dict(current_store, "agent_loop_runs").values()
        if run.get("ai_task_id") == task_id
        and (product_scope_ids is None or run.get("product_id") in allowed_products)
    ]
    if not runs:
        return None
    run = max(runs, key=lambda item: str(item.get("created_at") or ""))
    iterations = [
        deepcopy(item)
        for item in read_memory_dict(current_store, "agent_loop_iterations").values()
        if item.get("loop_run_id") == run["id"]
    ]
    iterations.sort(key=lambda item: int(item.get("iteration_number") or 0))
    return {**deepcopy(run), "iterations": iterations}


def request_agent_loop_human_takeover(
    current_store: Any,
    *,
    actor_id: str,
    reason: str,
    task_id: str,
) -> dict[str, Any]:
    run, iterations = _loop_and_iterations(current_store, ai_task_id=task_id)
    if run is None:
        raise api_error(409, "AGENT_LOOP_NOT_ACTIVE", "Task has no active Agent loop")
    if str(run.get("status") or "") not in ACTIVE_AGENT_LOOP_STATUSES:
        raise api_error(
            409,
            "AGENT_LOOP_NOT_ACTIVE",
            "Agent loop cannot be taken over from its current status",
        )
    now = datetime.now(UTC).isoformat()
    run.update(
        {
            "status": "waiting_review",
            "stop_reason": "human_takeover_requested",
            "updated_at": now,
            "version": int(run.get("version") or 1) + 1,
        }
    )
    audit = record_audit_event(
        current_store,
        event_type="agent_loop.human_takeover_requested",
        actor_id=actor_id,
        subject_type="agent_loop_run",
        subject_id=run["id"],
        payload={"reason": reason},
    )
    _save_loop_bundle(
        current_store,
        audit_events=[audit],
        iterations=[],
        run=run,
    )
    return {**deepcopy(run), "iterations": [deepcopy(item) for item in iterations]}
