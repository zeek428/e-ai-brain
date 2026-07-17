from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import Request

from app.api.deps import api_error, require_permissions
from app.core.listing import add_list_observability, sort_list_items
from app.services.agent_autonomy import (
    autonomy_enabled,
    handle_agent_quality_gate_outcome,
    record_agent_coding_completed,
)
from app.services.ai_executor_runner_constants import (
    AI_EXECUTOR_LOCAL_RUNNER_TYPES,
    AI_EXECUTOR_RUNNER_CAPABILITIES,
    AI_EXECUTOR_RUNNER_PROTOCOLS,
    AI_EXECUTOR_RUNNER_SORT_FIELDS,
    AI_EXECUTOR_RUNNER_STATUSES,
    AI_EXECUTOR_TASK_RETRYABLE_STATUSES,
    AI_EXECUTOR_TASK_SORT_FIELDS,
    AI_EXECUTOR_TASK_STATUSES,
    AI_EXECUTOR_TASK_TERMINAL_STATUSES,
    AI_EXECUTOR_TYPES,
    DEPLOYMENT_EXECUTOR_TYPE,
    SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID,
    SYSTEM_DEFAULT_AI_EXECUTOR_TYPE,
)
from app.services.ai_executor_runner_deployment_probes import (
    normalized_deployment_target_metadata,
    preserve_deployment_target_probe_metadata,
    runner_with_deployment_probe_result,
)
from app.services.ai_executor_runner_health import (
    is_system_default_runner_id as _is_system_default_runner_id,
)
from app.services.ai_executor_runner_health import (
    runner_public as _runner_public,
)
from app.services.ai_executor_runner_health import (
    system_default_ai_executor_runner,
)
from app.services.ai_executor_runner_packages import build_ai_executor_runner_install_package
from app.services.ai_executor_runner_persistence import (
    _delete_runner_record,
    _existing_pending_review,
    _memory_collection,
    _persist_record,
    _persist_task_state_records,
    _read_collection,
    _read_record,
    sync_ai_executor_runner_store,
    sync_ai_executor_task_store,
)
from app.services.ai_executor_runner_queue import (
    latest_task_for_runner as _latest_task_for_runner,
)
from app.services.ai_executor_runner_queue import (
    runner_queue_summary as _runner_queue_summary,
)
from app.services.ai_executor_runner_readiness import (
    runner_readiness_summary as _runner_readiness_summary,
)
from app.services.ai_executor_runner_task_context import (
    _ai_executor_task_visible_to_user,
    _load_ai_task,
    _load_collector_run,
    _load_plugin_invocation_log,
    _load_scheduled_job,
    _load_scheduled_job_run,
    _records_imported_from_runner_result,
    _runner_node_from_task,
    _status_for_runner_task,
    _task_public,
)
from app.services.ai_executor_runner_trust import patch_runner_trust_fields, runner_trust_fields
from app.services.ai_executor_runner_workspace import (
    reject_ai_executor_task_workspace,
    workspace_match_detail,
)
from app.services.ai_executor_task_creation import (
    create_ai_executor_task as create_ai_executor_task,
)
from app.services.ai_executor_task_reliability import (
    apply_task_claim_lease,
    refresh_task_lease,
)
from app.services.operational_records import record_audit_event
from app.services.product_scope import product_scope_filter
from app.services.quality_gates import (
    complete_pre_merge_quality_gate,
    quality_gate_allows_auto_merge,
    start_pre_merge_quality_gate,
)
from app.services.task_graph_runtime import latest_graph_run, transition_latest_graph_run
from app.services.task_output_summary import readable_task_output_summary
from app.services.task_persistence_helpers import (
    record_audit_event as record_task_audit_event,
)
from app.services.task_persistence_helpers import save_review_decision_records
from app.services.task_review_artifacts import (
    advance_requirement_after_task_completed,
    confirm_code_review_report,
    create_automated_testing_bugs,
    create_knowledge_deposit,
    create_post_release_bugs,
)
from app.services.task_workflow_context import task_workflow_write_store


def _ensure_admin(user: dict[str, Any]) -> None:
    require_permissions(user, {"system.plugins.manage"})


def _ensure_non_blank(value: str | None, field: str) -> str:
    if value is None or not value.strip():
        raise api_error(400, "VALIDATION_ERROR", f"{field} is required")
    return value.strip()


def _ensure_enum(value: str | None, allowed_values: set[str], field: str) -> str:
    normalized = _ensure_non_blank(value, field).lower()
    if normalized not in allowed_values:
        raise api_error(400, "VALIDATION_ERROR", f"Unsupported {field}")
    return normalized


def _normalized_string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise api_error(400, "VALIDATION_ERROR", f"{field} must be an array")
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _normalized_executor_types(value: Any) -> list[str]:
    executor_types = _normalized_string_list(value, "executor_types")
    if not executor_types:
        executor_types = ["codex"]
    for executor_type in executor_types:
        _ensure_enum(executor_type, AI_EXECUTOR_LOCAL_RUNNER_TYPES, "executor_type")
    return executor_types


def _normalized_runner_capabilities(value: Any) -> list[str]:
    capabilities = _normalized_string_list(value, "capabilities")
    for capability in capabilities:
        _ensure_enum(capability, AI_EXECUTOR_RUNNER_CAPABILITIES, "capability")
    return capabilities


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_ai_executor_runner_install_package_response(
    *,
    arch: str | None = None,
    current_store: Any,
    install_mode: str | None = None,
    runner_id: str,
    target_os: str | None = None,
    user: dict[str, Any],
) -> tuple[bytes, str]:
    _ensure_admin(user)
    if _is_system_default_runner_id(runner_id):
        raise api_error(
            409,
            "AI_EXECUTOR_SYSTEM_RUNNER_LOCKED",
            "系统默认执行器由平台托管，不需要 Runner 安装包",
        )
    sync_ai_executor_runner_store(current_store)
    runner = _read_record(current_store, "ai_executor_runners", runner_id)
    if runner is None:
        raise api_error(404, "NOT_FOUND", "AI executor runner not found")

    return build_ai_executor_runner_install_package(
        runner,
        arch=arch,
        install_mode=install_mode,
        target_os=target_os,
    )


def _runner_matches_filters(
    runner: dict[str, Any],
    *,
    executor_type: str | None = None,
    keyword: str | None = None,
    protocol: str | None = None,
    status: str | None = None,
) -> bool:
    if status is not None and runner.get("status") != status:
        return False
    if protocol is not None and runner.get("protocol") != protocol:
        return False
    if executor_type is not None and executor_type not in (runner.get("executor_types") or []):
        return False
    normalized_keyword = str(keyword or "").strip().lower()
    if normalized_keyword:
        searchable = " ".join(
            str(runner.get(field) or "").lower()
            for field in ("id", "name", "endpoint_url", "protocol")
        )
        if normalized_keyword not in searchable:
            return False
    return True


def _runner_public_with_latest_task(
    current_store: Any,
    runner: dict[str, Any],
) -> dict[str, Any]:
    item = _runner_public(runner)
    queue_summary = _runner_queue_summary(current_store, runner)
    item["queue_summary"] = queue_summary
    item["readiness_summary"] = _runner_readiness_summary(
        public_runner=item,
        queue_summary=queue_summary,
        runner=runner,
    )
    latest_task = _latest_task_for_runner(current_store, runner.get("id"))
    if latest_task is not None:
        item["latest_task_id"] = latest_task.get("id")
        item["latest_task_status"] = latest_task.get("status")
    return item


def _executor_policy_id_from_task(ai_task: dict[str, Any]) -> str | None:
    input_json = ai_task.get("input_json") if isinstance(ai_task.get("input_json"), dict) else {}
    executor = input_json.get("executor") if isinstance(input_json.get("executor"), dict) else {}
    policy_id = str(executor.get("executor_policy_id") or "").strip()
    return policy_id or None


def _load_executor_policy_for_ai_task(
    current_store: Any,
    ai_task: dict[str, Any],
) -> dict[str, Any] | None:
    policy_id = _executor_policy_id_from_task(ai_task)
    if not policy_id:
        return None
    policy = _read_record(current_store, "rd_task_executor_policies", policy_id)
    input_json = ai_task.get("input_json") if isinstance(ai_task.get("input_json"), dict) else {}
    executor_snapshot = (
        input_json.get("executor") if isinstance(input_json.get("executor"), dict) else {}
    )
    runner_task = _read_record(
        current_store,
        "ai_executor_tasks",
        str(executor_snapshot.get("runner_task_id") or ""),
    )
    request_config = (
        runner_task.get("request_config")
        if isinstance(runner_task, dict) and isinstance(runner_task.get("request_config"), dict)
        else {}
    )
    runtime_policy = request_config.get("runtime_policy")
    if not isinstance(runtime_policy, dict):
        runtime_policy = (
            executor_snapshot.get("runtime_policy")
            if isinstance(executor_snapshot.get("runtime_policy"), dict)
            else {}
        )
    if policy is not None:
        return {**policy, **runtime_policy}
    repository = getattr(current_store, "repository", None)
    list_policies = getattr(repository, "list_rd_task_executor_policies", None)
    if not callable(list_policies):
        return None
    for candidate in list_policies(
        product_id=None,
        status=None,
        task_type=str(ai_task.get("task_type") or ""),
    ):
        if candidate.get("id") == policy_id:
            return {**dict(candidate), **runtime_policy}
    return None


def _code_change_review_mode(policy: dict[str, Any] | None) -> str:
    mode = str((policy or {}).get("code_change_review_mode") or "manual_review").strip()
    return "auto_commit" if mode == "auto_commit" else "manual_review"


def _complete_ai_task_with_auto_commit_if_configured(
    current_store: Any,
    *,
    ai_task: dict[str, Any],
    executor_snapshot: dict[str, Any],
    output_json: dict[str, Any],
    quality_gate_run: dict[str, Any] | None,
    runner_id: str,
) -> bool:
    policy = _load_executor_policy_for_ai_task(current_store, ai_task)
    if (
        _code_change_review_mode(policy) != "auto_commit"
        or quality_gate_run is None
        or not quality_gate_allows_auto_merge(quality_gate_run)
    ):
        return False

    write_store = task_workflow_write_store(current_store)
    task = write_store.ai_tasks.get(ai_task["id"], dict(ai_task))
    now = datetime.now(UTC).isoformat()
    review_id = current_store.new_id("review")
    review = {
        "ai_task_id": task["id"],
        "content": output_json,
        "created_at": now,
        "decided_at": now,
        "decided_by": "system",
        "decision_reason": "auto_commit_by_executor_policy",
        "id": review_id,
        "questions": [],
        "stage": task.get("task_type") or "executor_result",
        "status": "approved",
        "updated_at": now,
        "version": 1,
    }
    if getattr(write_store, "repository", None) is None:
        _memory_collection(write_store, "human_reviews")[review_id] = review
    review_ids = list(task.get("review_ids") or [])
    if review_id not in review_ids:
        review_ids.append(review_id)
    task.update(
        {
            "current_step": "executor_completed",
            "output_json": output_json,
            "review_ids": review_ids,
            "status": "completed",
            "updated_at": now,
        }
    )

    audit_start_index = len(write_store.audit_events)
    record_task_audit_event(
        write_store,
        event_type="ai_task.executor_completed",
        actor_id=runner_id,
        ai_task_id=task["id"],
        subject_type="ai_task",
        subject_id=task["id"],
        payload={
            "ai_task_id": task["id"],
            **executor_snapshot,
            "code_change_review_mode": "auto_commit",
            "executor_policy_id": (policy or {}).get("id"),
            "quality_gate_run_id": quality_gate_run["id"],
        },
    )
    from app.services.ai_executor_workspace_isolation import (
        mark_ai_executor_workspace_isolation_decision,
    )

    mark_ai_executor_workspace_isolation_decision(
        current_store,
        action="merge",
        decided_by="system",
        reason="auto_commit_by_executor_policy",
        task=task,
    )
    confirm_code_review_report(write_store, task)
    created_bug_ids = [
        *create_automated_testing_bugs(write_store, actor_id="system", task=task),
        *create_post_release_bugs(write_store, actor_id="system", task=task),
    ]
    advance_requirement_after_task_completed(write_store, task)
    knowledge_deposit = create_knowledge_deposit(write_store, task)
    checkpoint = transition_latest_graph_run(
        write_store,
        task=task,
        status="completed",
        current_step="complete_archive",
        state_snapshot={
            "code_change_review_mode": "auto_commit",
            "quality_gate_run_id": quality_gate_run["id"],
            "review_id": review_id,
            "task_status": task["status"],
        },
    )
    record_task_audit_event(
        write_store,
        event_type="review.submitted",
        actor_id="system",
        ai_task_id=task["id"],
        subject_type="human_review",
        subject_id=review_id,
        payload={
            "code_change_review_mode": "auto_commit",
            "decision": "approved",
            "executor_policy_id": (policy or {}).get("id"),
            "quality_gate_run_id": quality_gate_run["id"],
        },
    )
    record_task_audit_event(
        write_store,
        event_type="ai_task.executor_auto_committed",
        actor_id="system",
        ai_task_id=task["id"],
        subject_type="ai_task",
        subject_id=task["id"],
        payload={
            "executor_policy_id": (policy or {}).get("id"),
            "quality_gate_run_id": quality_gate_run["id"],
            "runner_id": runner_id,
            "runner_task_id": executor_snapshot.get("runner_task_id"),
        },
    )
    graph_run = latest_graph_run(write_store, task)
    requirement = write_store.requirements.get(task.get("requirement_id"))
    code_review_report = (
        write_store.code_review_reports.get(task.get("code_review_report_id"))
        if task.get("code_review_report_id")
        else None
    )
    save_review_decision_records(
        write_store,
        task=task,
        review=review,
        graph_run=graph_run,
        checkpoint=checkpoint,
        requirement=requirement,
        knowledge_deposits=[knowledge_deposit],
        bugs=[write_store.bugs[bug_id] for bug_id in created_bug_ids],
        code_review_report=code_review_report,
        audit_events=write_store.audit_events[audit_start_index:],
    )
    return True


def _move_ai_task_to_executor_review(
    current_store: Any,
    *,
    ai_task: dict[str, Any],
    actor_id: str,
    executor_snapshot: dict[str, Any],
    output_json: dict[str, Any],
    quality_gate_run: dict[str, Any] | None = None,
) -> None:
    now = datetime.now(UTC).isoformat()
    review_output = (
        {**output_json, "quality_gate": quality_gate_run}
        if quality_gate_run is not None
        else output_json
    )
    updated_task = {
        **ai_task,
        "current_step": "executor_completed",
        "output_json": review_output,
        "status": "waiting_review",
        "updated_at": now,
    }
    reviews: list[dict[str, Any]] = []
    existing_review = _existing_pending_review(
        current_store,
        updated_task["id"],
        str(updated_task.get("task_type") or "executor_result"),
    )
    if existing_review is None:
        review_id = current_store.new_id("review")
        reviews.append(
            {
                "ai_task_id": updated_task["id"],
                "content": review_output,
                "created_at": now,
                "decided_at": None,
                "decided_by": None,
                "decision_reason": None,
                "id": review_id,
                "questions": [],
                "stage": updated_task.get("task_type") or "executor_result",
                "status": "pending",
                "updated_at": now,
                "version": 1,
            }
        )
    review_ids = list(updated_task.get("review_ids") or [])
    for review in reviews or ([existing_review] if existing_review else []):
        if review and review["id"] not in review_ids:
            review_ids.append(review["id"])
    updated_task["review_ids"] = review_ids
    audit_event = record_audit_event(
        current_store,
        event_type="ai_task.executor_completed",
        actor_id=actor_id,
        subject_type="ai_task",
        subject_id=updated_task["id"],
        payload={
            "ai_task_id": updated_task["id"],
            **executor_snapshot,
            "quality_gate_run_id": (quality_gate_run or {}).get("id"),
            "quality_gate_status": (quality_gate_run or {}).get("status"),
        },
    )
    _persist_task_state_records(
        current_store,
        audit_events=[audit_event],
        reviews=reviews or None,
        task=updated_task,
    )


def _sync_runner_completion_to_ai_task(
    current_store: Any,
    *,
    task: dict[str, Any],
    runner_id: str,
) -> None:
    ai_task = _load_ai_task(current_store, task.get("ai_task_id"))
    if ai_task is None:
        return
    if task.get("task_kind") == "quality_gate":
        if task.get("status") in {"queued", "claimed", "running"}:
            return
        quality_gate_run = complete_pre_merge_quality_gate(
            current_store,
            verifier_runner_task=task,
        )
        if quality_gate_run is None:
            return
        output_json = (
            ai_task.get("output_json") if isinstance(ai_task.get("output_json"), dict) else {}
        )
        output_json = {**output_json, "quality_gate": quality_gate_run}
        executor_snapshot = (
            output_json.get("executor") if isinstance(output_json.get("executor"), dict) else {}
        )
        policy = _load_executor_policy_for_ai_task(current_store, ai_task)
        loop_outcome = handle_agent_quality_gate_outcome(
            current_store,
            ai_task=ai_task,
            executor_policy=policy,
            quality_gate_run=quality_gate_run,
            verifier_runner_task=task,
        )
        if loop_outcome.get("action") == "retry":
            retry_task = loop_outcome["runner_task"]
            now = datetime.now(UTC).isoformat()
            input_json = (
                ai_task.get("input_json") if isinstance(ai_task.get("input_json"), dict) else {}
            )
            retry_executor = {
                "executor_policy_id": _executor_policy_id_from_task(ai_task),
                "executor_type": retry_task.get("executor_type"),
                "runner_id": retry_task.get("runner_id"),
                "runner_task_id": retry_task.get("id"),
                "status": retry_task.get("status"),
                "workspace_root": retry_task.get("workspace_root"),
            }
            updated_task = {
                **ai_task,
                "current_step": "agent_loop_retrying",
                "input_json": {
                    **input_json,
                    "agent_loop": {
                        "id": loop_outcome["loop"]["id"],
                        "iteration": loop_outcome["loop"]["current_iteration"],
                        "status": loop_outcome["loop"]["status"],
                    },
                    "executor": retry_executor,
                },
                "output_json": output_json,
                "status": "running",
                "updated_at": now,
            }
            audit_event = record_audit_event(
                current_store,
                event_type="ai_task.agent_loop_retrying",
                actor_id="system",
                subject_type="ai_task",
                subject_id=updated_task["id"],
                payload={
                    "agent_loop_run_id": loop_outcome["loop"]["id"],
                    "iteration": loop_outcome["loop"]["current_iteration"],
                    "runner_task_id": retry_task["id"],
                },
            )
            _persist_task_state_records(
                current_store,
                audit_events=[audit_event],
                reviews=None,
                task=updated_task,
            )
            return
        if loop_outcome.get("action") == "review":
            _move_ai_task_to_executor_review(
                current_store,
                ai_task=ai_task,
                actor_id=runner_id,
                executor_snapshot=executor_snapshot,
                output_json=output_json,
                quality_gate_run=quality_gate_run,
            )
            return
        if _complete_ai_task_with_auto_commit_if_configured(
            current_store,
            ai_task=ai_task,
            executor_snapshot=executor_snapshot,
            output_json=output_json,
            quality_gate_run=quality_gate_run,
            runner_id=runner_id,
        ):
            return
        _move_ai_task_to_executor_review(
            current_store,
            ai_task=ai_task,
            actor_id=runner_id,
            executor_snapshot=executor_snapshot,
            output_json=output_json,
            quality_gate_run=quality_gate_run,
        )
        return
    runner_status = str(task.get("status") or "running")
    now = datetime.now(UTC).isoformat()
    input_json = ai_task.get("input_json") if isinstance(ai_task.get("input_json"), dict) else {}
    existing_executor = (
        input_json.get("executor") if isinstance(input_json.get("executor"), dict) else {}
    )
    request_config = (
        task.get("request_config") if isinstance(task.get("request_config"), dict) else {}
    )
    executor_snapshot = {
        "executor_type": task.get("executor_type"),
        "runner_id": task.get("runner_id"),
        "runner_task_id": task.get("id"),
        "status": runner_status,
        "workspace_root": task.get("workspace_root"),
    }
    executor_policy_id = existing_executor.get("executor_policy_id") or request_config.get(
        "executor_policy_id"
    )
    if executor_policy_id:
        executor_snapshot["executor_policy_id"] = executor_policy_id
    if runner_status in {"queued", "claimed", "running"}:
        updated_task = {
            **ai_task,
            "current_step": "waiting_ai_executor",
            "input_json": {
                **input_json,
                "executor": executor_snapshot,
            },
            "status": "running",
            "updated_at": now,
        }
        audit_event = record_audit_event(
            current_store,
            event_type="ai_task.executor_waiting",
            actor_id=runner_id,
            subject_type="ai_task",
            subject_id=updated_task["id"],
            payload={"ai_task_id": updated_task["id"], **executor_snapshot},
        )
        _persist_task_state_records(
            current_store,
            audit_events=[audit_event],
            reviews=None,
            task=updated_task,
        )
        return

    if runner_status == "succeeded":
        output_json = {
            "executor": {
                **executor_snapshot,
                "finished_at": task.get("finished_at"),
            },
            "result": task.get("result_json") or {},
        }
        output_summary = readable_task_output_summary(output_json)
        if output_summary:
            output_json["summary"] = output_summary
        policy = _load_executor_policy_for_ai_task(current_store, ai_task)
        if _code_change_review_mode(policy) == "auto_commit" or autonomy_enabled(policy):
            quality_gate_run, verifier_task = start_pre_merge_quality_gate(
                current_store,
                ai_task=ai_task,
                coding_runner_task=task,
                executor_policy=policy,
            )
            record_agent_coding_completed(
                current_store,
                coding_runner_task=task,
                quality_gate_run_id=quality_gate_run["id"],
                verifier_runner_task_id=verifier_task["id"],
            )
            if verifier_task.get("status") == "blocked":
                output_json["quality_gate"] = quality_gate_run
                _move_ai_task_to_executor_review(
                    current_store,
                    actor_id=runner_id,
                    ai_task=ai_task,
                    executor_snapshot=executor_snapshot,
                    output_json=output_json,
                    quality_gate_run=quality_gate_run,
                )
                return
            updated_task = {
                **ai_task,
                "current_step": "quality_gate_running",
                "input_json": {
                    **input_json,
                    "executor": executor_snapshot,
                    "quality_gate": {
                        "id": quality_gate_run["id"],
                        "status": quality_gate_run["status"],
                        "verifier_runner_task_id": verifier_task["id"],
                    },
                },
                "output_json": output_json,
                "status": "running",
                "updated_at": now,
            }
            audit_event = record_audit_event(
                current_store,
                event_type="ai_task.quality_gate_started",
                actor_id=runner_id,
                subject_type="ai_task",
                subject_id=updated_task["id"],
                payload={
                    "ai_task_id": updated_task["id"],
                    "coding_runner_task_id": task["id"],
                    "quality_gate_run_id": quality_gate_run["id"],
                    "verifier_runner_task_id": verifier_task["id"],
                },
            )
            _persist_task_state_records(
                current_store,
                audit_events=[audit_event],
                reviews=None,
                task=updated_task,
            )
            return
        _move_ai_task_to_executor_review(
            current_store,
            actor_id=runner_id,
            ai_task=ai_task,
            executor_snapshot=executor_snapshot,
            output_json=output_json,
        )
        return

    next_status = "cancelled" if runner_status == "cancelled" else "failed"
    updated_task = {
        **ai_task,
        "current_step": "executor_failed",
        "error_code": task.get("error_code") or "AI_EXECUTOR_TASK_FAILED",
        "error_message": task.get("error_message") or "AI executor task failed",
        "output_json": {
            "executor": executor_snapshot,
            "result": task.get("result_json") or {},
        },
        "status": next_status,
        "updated_at": now,
    }
    audit_event = record_audit_event(
        current_store,
        event_type="ai_task.executor_failed",
        actor_id=runner_id,
        subject_type="ai_task",
        subject_id=updated_task["id"],
        payload={
            "ai_task_id": updated_task["id"],
            **executor_snapshot,
            "error_code": updated_task.get("error_code"),
            "error_message": updated_task.get("error_message"),
        },
    )
    _persist_task_state_records(
        current_store,
        audit_events=[audit_event],
        reviews=None,
        task=updated_task,
    )


def _sync_runner_completion_to_scheduled_run(
    current_store: Any,
    *,
    task: dict[str, Any],
    runner_id: str,
) -> None:
    from app.services.scheduled_job_ai_executor import (
        sync_ai_executor_completion_to_scheduled_run,
    )

    if sync_ai_executor_completion_to_scheduled_run(
        current_store,
        runner_id=runner_id,
        task=task,
    ):
        return
    run = _load_scheduled_job_run(current_store, task)
    if run is None:
        return
    now = datetime.now(UTC).isoformat()
    runner_node = _runner_node_from_task(task)
    result_summary = dict(run.get("result_summary") or {})
    execution_nodes = dict(result_summary.get("execution_nodes") or {})
    execution_nodes["runner_execution"] = runner_node
    result_action = dict(execution_nodes.get("result_action") or {})
    if result_action:
        feedback = dict(result_action.get("feedback") or {})
        feedback["runner_result"] = task.get("result_json") or {}
        result_action["feedback"] = feedback
        result_action["status"] = _status_for_runner_task(str(task.get("status") or "running"))
        execution_nodes["result_action"] = result_action
    result_summary["execution_nodes"] = execution_nodes

    log = _load_plugin_invocation_log(current_store, task)
    if log is not None:
        response_summary = dict(log.get("response_summary") or {})
        response_summary["runner"] = runner_node
        json_payload = dict(response_summary.get("json") or {})
        json_payload.update(
            {
                "executor_type": task.get("executor_type"),
                "result_json": task.get("result_json") or {},
                "runner_id": task.get("runner_id"),
                "runner_task_id": task.get("id"),
                "status": task.get("status"),
                "workspace_root": task.get("workspace_root"),
            },
        )
        response_summary["json"] = json_payload
        log_status = log.get("status") or "succeeded"
        if task.get("status") in {"dead_letter", "failed", "cancelled", "timed_out"}:
            log_status = "failed"
        updated_log = {
            **log,
            "error_code": task.get("error_code"),
            "error_message": task.get("error_message"),
            "response_summary": response_summary,
            "status": log_status,
            "updated_at": now,
        }
        _persist_record(current_store, "save_plugin_invocation_log_record", updated_log)
        plugin_summary = dict(result_summary.get("plugin") or {})
        if plugin_summary:
            plugin_summary.update(
                {
                    "error_code": updated_log.get("error_code"),
                    "error_message": updated_log.get("error_message"),
                    "response_summary": response_summary,
                    "status": log_status,
                },
            )
            result_summary["plugin"] = plugin_summary

    run_status = _status_for_runner_task(str(task.get("status") or "running"))
    records_imported = _records_imported_from_runner_result(
        task,
        fallback=int(run.get("records_imported") or 0),
    )
    updated_run = {
        **run,
        "error_code": task.get("error_code") if run_status == "failed" else None,
        "error_message": task.get("error_message") if run_status == "failed" else None,
        "finished_at": now if run_status in {"cancelled", "failed", "succeeded"} else None,
        "records_imported": records_imported,
        "result_summary": result_summary,
        "status": run_status,
        "updated_at": now,
    }
    audit_event = record_audit_event(
        current_store,
        event_type=f"scheduled_job_run.{run_status}",
        actor_id=runner_id,
        subject_type="scheduled_job_run",
        subject_id=updated_run["id"],
        payload={
            "ai_executor_task_id": task["id"],
            "records_imported": records_imported,
            "runner_id": runner_id,
            "scheduled_job_id": task.get("scheduled_job_id"),
            "status": run_status,
        },
    )
    _persist_record(
        current_store,
        "save_scheduled_job_run_record",
        updated_run,
        audit_event=audit_event,
    )

    if run_status not in {"cancelled", "failed", "succeeded"}:
        return
    collector_run = _load_collector_run(current_store, updated_run.get("collector_run_id"))
    if collector_run is not None:
        collector_status = "succeeded" if run_status == "succeeded" else "failed"
        updated_collector = {
            **collector_run,
            "error_message": updated_run.get("error_message"),
            "finished_at": now,
            "records_imported": records_imported,
            "status": collector_status,
            "updated_at": now,
        }
        _persist_record(current_store, "save_collector_run_record", updated_collector)
    job = _load_scheduled_job(current_store, task.get("scheduled_job_id"))
    if job is not None:
        updated_job = {
            **job,
            "last_error_message": updated_run.get("error_message"),
            "last_failure_at": now if run_status == "failed" else job.get("last_failure_at"),
            "last_run_at": now,
            "last_success_at": now if run_status == "succeeded" else job.get("last_success_at"),
            "updated_at": now,
        }
        _persist_record(current_store, "save_scheduled_job_record", updated_job)


def create_ai_executor_runner_response(
    *,
    current_store: Any,
    payload: Any,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    runner_token = str(getattr(payload, "runner_token", None) or secrets.token_urlsafe(32))
    now = datetime.now(UTC).isoformat()
    runner_id = current_store.new_id("ai_executor_runner")
    runner = {
        "capabilities": _normalized_runner_capabilities(
            getattr(payload, "capabilities", None),
        ),
        "created_at": now,
        "created_by": user["id"],
        "endpoint_url": _ensure_non_blank(
            getattr(payload, "endpoint_url", None) or "runner://local",
            "endpoint_url",
        ),
        "executor_types": _normalized_executor_types(getattr(payload, "executor_types", None)),
        "heartbeat_timeout_seconds": int(
            getattr(payload, "heartbeat_timeout_seconds", None) or 120,
        ),
        "id": runner_id,
        "last_heartbeat_at": None,
        "max_concurrent_tasks": int(getattr(payload, "max_concurrent_tasks", None) or 1),
        "metadata": dict(getattr(payload, "metadata", None) or {}),
        "name": _ensure_non_blank(getattr(payload, "name", None), "name"),
        "protocol": _ensure_enum(
            getattr(payload, "protocol", None) or "runner_polling",
            AI_EXECUTOR_RUNNER_PROTOCOLS,
            "protocol",
        ),
        "status": _ensure_enum(
            getattr(payload, "status", None) or "active",
            AI_EXECUTOR_RUNNER_STATUSES,
            "status",
        ),
        **runner_trust_fields(payload, ensure_enum=_ensure_enum),
        "token_hash": _token_hash(runner_token),
        "token_rotated_at": None,
        "token_version": 1,
        "updated_at": now,
        "workspace_roots": _normalized_string_list(
            getattr(payload, "workspace_roots", None),
            "workspace_roots",
        ),
    }
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_runner.created",
        actor_id=user["id"],
        subject_type="ai_executor_runner",
        subject_id=runner_id,
        payload={
            "capabilities": runner["capabilities"],
            "executor_types": runner["executor_types"],
            "protocol": runner["protocol"],
            "status": runner["status"],
        },
    )
    _persist_record(
        current_store,
        "save_ai_executor_runner_record",
        runner,
        audit_event=audit_event,
    )
    return {**_runner_public(runner), "runner_token": runner_token}


def list_ai_executor_runners_response(
    *,
    current_store: Any,
    executor_type: str | None = None,
    keyword: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    protocol: str | None = None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    started_at: float | None = None,
    status: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    if status is not None:
        _ensure_enum(status, AI_EXECUTOR_RUNNER_STATUSES, "status")
    if protocol is not None:
        _ensure_enum(
            protocol,
            AI_EXECUTOR_RUNNER_PROTOCOLS | {SYSTEM_DEFAULT_AI_EXECUTOR_TYPE},
            "protocol",
        )
    if executor_type is not None:
        _ensure_enum(executor_type, AI_EXECUTOR_TYPES, "executor_type")
    sort_order = _ensure_enum(sort_order, {"asc", "desc"}, "sort_order")
    if sort_by is not None:
        _ensure_enum(sort_by, AI_EXECUTOR_RUNNER_SORT_FIELDS, "sort_by")
    resolved_sort_by = sort_by or "updated_at"
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    with_pagination = page is not None or page_size is not None
    repository = getattr(current_store, "repository", None)
    count_page = getattr(repository, "count_ai_executor_runners", None)
    list_page = getattr(repository, "list_ai_executor_runners_page", None)
    filters = {
        "executor_type": executor_type,
        "keyword": keyword,
        "protocol": protocol,
        "status": status,
    }
    sync_ai_executor_task_store(current_store)
    system_runner = system_default_ai_executor_runner()
    system_matches = _runner_matches_filters(system_runner, **filters)
    if with_pagination and callable(count_page) and callable(list_page):
        repository_total = count_page(**filters)
        system_count = 1 if system_matches else 0
        total = repository_total + system_count
        offset = (resolved_page - 1) * resolved_page_size
        items: list[dict[str, Any]] = []
        repository_limit = resolved_page_size
        repository_offset = offset
        if system_count:
            if offset == 0:
                items.append(_runner_public_with_latest_task(current_store, system_runner))
                repository_limit = max(0, resolved_page_size - 1)
                repository_offset = 0
            else:
                repository_offset = max(0, offset - 1)
        if repository_limit > 0 and repository_offset < repository_total:
            items.extend(
                _runner_public_with_latest_task(current_store, runner)
                for runner in list_page(
                    **filters,
                    limit=repository_limit,
                    offset=repository_offset,
                    sort_by=resolved_sort_by,
                    sort_order=sort_order,
                )
            )
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="ai_executor_runners",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    sync_ai_executor_runner_store(
        current_store,
        status=status,
    )
    runners = [
        system_runner,
        *[
            runner
            for runner in _read_collection(current_store, "ai_executor_runners").values()
            if runner.get("id") != SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID
        ],
    ]
    items = [
        _runner_public_with_latest_task(current_store, runner)
        for runner in runners
        if _runner_matches_filters(runner, **filters)
    ]
    items = sort_list_items(
        items,
        allowed_fields=AI_EXECUTOR_RUNNER_SORT_FIELDS,
        default_sort_by=resolved_sort_by,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    if system_matches:
        items = sorted(
            items,
            key=lambda item: 0 if item.get("id") == SYSTEM_DEFAULT_AI_EXECUTOR_RUNNER_ID else 1,
        )
    total = len(items)
    if with_pagination:
        start_index = (resolved_page - 1) * resolved_page_size
        items = items[start_index : start_index + resolved_page_size]
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="ai_executor_runners",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    return {"items": items, "total": total}


def list_ai_executor_tasks_response(
    *,
    ai_task_id: str | None,
    current_store: Any,
    page: int | None = None,
    page_size: int | None = None,
    runner_id: str | None,
    scheduled_job_run_id: str | None,
    sort_by: str | None = None,
    sort_order: str = "desc",
    started_at: float | None = None,
    status: str | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    if status is not None:
        _ensure_enum(status, AI_EXECUTOR_TASK_STATUSES, "status")
    sort_order = _ensure_enum(sort_order, {"asc", "desc"}, "sort_order")
    if sort_by is not None:
        _ensure_enum(sort_by, AI_EXECUTOR_TASK_SORT_FIELDS, "sort_by")
    resolved_sort_by = sort_by or "updated_at"
    resolved_page = page or 1
    resolved_page_size = page_size or 10
    with_pagination = page is not None or page_size is not None
    repository = getattr(current_store, "repository", None)
    count_page = getattr(repository, "count_ai_executor_tasks", None)
    list_page = getattr(repository, "list_ai_executor_tasks_page", None)
    filters = {
        "ai_task_id": ai_task_id,
        "product_scope_ids": product_scope_filter(user),
        "runner_id": runner_id,
        "scheduled_job_run_id": scheduled_job_run_id,
        "status": status,
    }
    if with_pagination and callable(count_page) and callable(list_page):
        total = count_page(**filters)
        items = [
            _task_public(task)
            for task in list_page(
                **filters,
                limit=resolved_page_size,
                offset=(resolved_page - 1) * resolved_page_size,
                sort_by=resolved_sort_by,
                sort_order=sort_order,
            )
        ]
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="ai_executor_tasks",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    sync_ai_executor_task_store(
        current_store,
        ai_task_id=ai_task_id,
        product_scope_ids=filters["product_scope_ids"],
        runner_id=runner_id,
        scheduled_job_run_id=scheduled_job_run_id,
        status=status,
    )
    items = [
        _task_public(task)
        for task in _read_collection(current_store, "ai_executor_tasks").values()
        if (ai_task_id is None or task.get("ai_task_id") == ai_task_id)
        and (
            filters["product_scope_ids"] is None
            or _ai_executor_task_visible_to_user(current_store, task=task, user=user)
        )
        and (runner_id is None or task.get("runner_id") == runner_id)
        and (
            scheduled_job_run_id is None or task.get("scheduled_job_run_id") == scheduled_job_run_id
        )
        and (status is None or task.get("status") == status)
    ]
    items = sort_list_items(
        items,
        allowed_fields=AI_EXECUTOR_TASK_SORT_FIELDS,
        default_sort_by=resolved_sort_by,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    total = len(items)
    if with_pagination:
        start_index = (resolved_page - 1) * resolved_page_size
        items = items[start_index : start_index + resolved_page_size]
        return add_list_observability(
            {
                "items": items,
                "page": resolved_page,
                "page_size": resolved_page_size,
                "total": total,
            },
            filters=filters,
            list_name="ai_executor_tasks",
            page=resolved_page,
            page_size=resolved_page_size,
            sort_by=resolved_sort_by,
            sort_order=sort_order,
            started_at=started_at,
        )
    return {"items": items, "total": total}


def patch_ai_executor_runner_response(
    *,
    current_store: Any,
    payload: Any,
    runner_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    if _is_system_default_runner_id(runner_id):
        raise api_error(
            409,
            "AI_EXECUTOR_SYSTEM_RUNNER_LOCKED",
            "系统默认执行器由平台托管，不能修改",
        )
    sync_ai_executor_runner_store(current_store)
    runner = _read_record(current_store, "ai_executor_runners", runner_id)
    if runner is None:
        raise api_error(404, "NOT_FOUND", "AI executor runner not found")
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        updates["name"] = _ensure_non_blank(updates["name"], "name")
    if "endpoint_url" in updates:
        updates["endpoint_url"] = _ensure_non_blank(updates["endpoint_url"], "endpoint_url")
    if "protocol" in updates:
        updates["protocol"] = _ensure_enum(
            updates["protocol"],
            AI_EXECUTOR_RUNNER_PROTOCOLS,
            "protocol",
        )
    if "status" in updates:
        updates["status"] = _ensure_enum(
            updates["status"],
            AI_EXECUTOR_RUNNER_STATUSES,
            "status",
        )
    if "executor_types" in updates:
        updates["executor_types"] = _normalized_executor_types(updates["executor_types"])
    if "capabilities" in updates:
        updates["capabilities"] = _normalized_runner_capabilities(updates["capabilities"])
    if "workspace_roots" in updates:
        updates["workspace_roots"] = _normalized_string_list(
            updates["workspace_roots"],
            "workspace_roots",
        )
    if "runner_token" in updates:
        updates["token_hash"] = _token_hash(
            _ensure_non_blank(updates.pop("runner_token"), "runner_token"),
        )
        updates["token_rotated_at"] = datetime.now(UTC).isoformat()
        updates["token_version"] = int(runner.get("token_version") or 1) + 1
    for int_key in ("heartbeat_timeout_seconds", "max_concurrent_tasks"):
        if int_key in updates:
            updates[int_key] = int(updates[int_key])
    if "metadata" in updates:
        updates["metadata"] = dict(updates["metadata"] or {})
    updates = patch_runner_trust_fields(updates, runner=runner, ensure_enum=_ensure_enum)
    runner = {**runner, **updates, "updated_at": datetime.now(UTC).isoformat()}
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_runner.updated",
        actor_id=user["id"],
        subject_type="ai_executor_runner",
        subject_id=runner_id,
        payload={
            "capabilities": runner.get("capabilities") or [],
            "executor_types": runner["executor_types"],
            "protocol": runner["protocol"],
            "status": runner["status"],
        },
    )
    _persist_record(
        current_store,
        "save_ai_executor_runner_record",
        runner,
        audit_event=audit_event,
    )
    return _runner_public(runner)


def rotate_ai_executor_runner_token_response(
    *,
    current_store: Any,
    payload: Any,
    runner_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    if _is_system_default_runner_id(runner_id):
        raise api_error(
            409,
            "AI_EXECUTOR_SYSTEM_RUNNER_LOCKED",
            "系统默认执行器由平台托管，不需要 Runner Token",
        )
    sync_ai_executor_runner_store(current_store)
    runner = _read_record(current_store, "ai_executor_runners", runner_id)
    if runner is None:
        raise api_error(404, "NOT_FOUND", "AI executor runner not found")
    runner_token = str(getattr(payload, "runner_token", None) or secrets.token_urlsafe(32))
    now = datetime.now(UTC).isoformat()
    runner = {
        **runner,
        "token_hash": _token_hash(_ensure_non_blank(runner_token, "runner_token")),
        "token_rotated_at": now,
        "token_version": int(runner.get("token_version") or 1) + 1,
        "updated_at": now,
    }
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_runner.token_rotated",
        actor_id=user["id"],
        subject_type="ai_executor_runner",
        subject_id=runner_id,
        payload={"token_version": runner["token_version"]},
    )
    _persist_record(
        current_store,
        "save_ai_executor_runner_record",
        runner,
        audit_event=audit_event,
    )
    return {**_runner_public(runner), "runner_token": runner_token}


def delete_ai_executor_runner_response(
    *,
    current_store: Any,
    runner_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    if _is_system_default_runner_id(runner_id):
        raise api_error(
            409,
            "AI_EXECUTOR_SYSTEM_RUNNER_LOCKED",
            "系统默认执行器由平台托管，不能删除",
        )
    sync_ai_executor_runner_store(current_store)
    sync_ai_executor_task_store(current_store, runner_id=runner_id)
    runner = _read_record(current_store, "ai_executor_runners", runner_id)
    if runner is None:
        raise api_error(404, "NOT_FOUND", "AI executor runner not found")
    active_tasks = [
        task["id"]
        for task in _read_collection(current_store, "ai_executor_tasks").values()
        if task.get("runner_id") == runner_id
        and task.get("status") not in AI_EXECUTOR_TASK_TERMINAL_STATUSES
    ]
    if active_tasks:
        raise api_error(
            409,
            "AI_EXECUTOR_RUNNER_IN_USE",
            "AI executor runner has active tasks: " + ", ".join(active_tasks),
        )
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_runner.deleted",
        actor_id=user["id"],
        subject_type="ai_executor_runner",
        subject_id=runner_id,
        payload={"name": runner["name"], "protocol": runner["protocol"]},
    )
    _delete_runner_record(
        current_store,
        collection_name="ai_executor_runners",
        method_name="delete_ai_executor_runner_record",
        record_id=runner_id,
        audit_event=audit_event,
    )
    return {"deleted": True, "id": runner_id}


def _runner_token_from_request(request: Request) -> str:
    explicit = request.headers.get("X-Runner-Token")
    if explicit:
        return explicit.strip()
    authorization = request.headers.get("Authorization") or ""
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    raise api_error(401, "AI_EXECUTOR_RUNNER_TOKEN_REQUIRED", "Runner token is required")


def _authenticated_runner(
    current_store: Any,
    *,
    request: Request,
    runner_id: str,
) -> dict[str, Any]:
    if _is_system_default_runner_id(runner_id):
        raise api_error(
            409,
            "AI_EXECUTOR_SYSTEM_RUNNER_LOCKED",
            "系统默认执行器由平台托管，不接收 Runner 心跳或任务领取",
        )
    sync_ai_executor_runner_store(current_store)
    runner = _read_record(current_store, "ai_executor_runners", runner_id)
    if runner is None:
        raise api_error(404, "NOT_FOUND", "AI executor runner not found")
    token = _runner_token_from_request(request)
    if not secrets.compare_digest(_token_hash(token), str(runner.get("token_hash") or "")):
        raise api_error(401, "AI_EXECUTOR_RUNNER_TOKEN_INVALID", "Runner token is invalid")
    if runner.get("status") == "disabled":
        raise api_error(409, "AI_EXECUTOR_RUNNER_DISABLED", "AI executor runner is disabled")
    return runner


def runner_heartbeat_response(
    *,
    current_store: Any,
    metadata: dict[str, Any] | None,
    request: Request,
    runner_id: str,
) -> dict[str, Any]:
    runner = _authenticated_runner(current_store, request=request, runner_id=runner_id)
    now = datetime.now(UTC).isoformat()
    incoming_metadata = dict(metadata or {})
    if "deployment_targets" in incoming_metadata:
        incoming_metadata["deployment_targets"] = normalized_deployment_target_metadata(
            incoming_metadata.get("deployment_targets"),
        )
        existing_metadata = (
            runner.get("metadata") if isinstance(runner.get("metadata"), dict) else {}
        )
        incoming_metadata["deployment_targets"] = preserve_deployment_target_probe_metadata(
            incoming_metadata["deployment_targets"],
            existing_metadata.get("deployment_targets"),
        )
    merged_metadata = {**dict(runner.get("metadata") or {}), **incoming_metadata}
    runner = {
        **runner,
        "last_heartbeat_at": now,
        "metadata": merged_metadata,
        "status": "active" if runner.get("status") != "disabled" else "disabled",
        "updated_at": now,
    }
    _persist_record(current_store, "save_ai_executor_runner_record", runner)
    return _runner_public(runner)


def find_available_runner(
    current_store: Any,
    *,
    executor_type: str,
    runner_id: str | None,
    workspace_root: str,
) -> dict[str, Any]:
    if executor_type == SYSTEM_DEFAULT_AI_EXECUTOR_TYPE:
        if runner_id and not _is_system_default_runner_id(runner_id):
            raise api_error(
                409,
                "AI_EXECUTOR_RUNNER_UNAVAILABLE",
                "System default executor must use the system default runner",
            )
        return system_default_ai_executor_runner()
    if _is_system_default_runner_id(runner_id):
        raise api_error(
            409,
            "AI_EXECUTOR_RUNNER_UNAVAILABLE",
            "System default runner only supports the model_gateway executor type",
        )
    sync_ai_executor_runner_store(current_store)
    candidates = list(_read_collection(current_store, "ai_executor_runners").values())
    if runner_id:
        candidates = [runner for runner in candidates if runner.get("id") == runner_id]
    workspace_rejections: list[dict[str, Any]] = []
    for runner in candidates:
        if runner.get("status") != "active":
            continue
        if executor_type not in (runner.get("executor_types") or []):
            continue
        workspace_match = workspace_match_detail(runner, workspace_root)
        if not workspace_match["allowed"]:
            workspace_rejections.append(
                {
                    **workspace_match,
                    "runner_id": runner.get("id"),
                    "runner_name": runner.get("name"),
                }
            )
            continue
        return runner
    if workspace_rejections:
        rejection = workspace_rejections[0]
        raise api_error(
            409,
            "AI_EXECUTOR_WORKSPACE_NOT_ALLOWED",
            "Workspace root is outside the runner workspace whitelist",
            {
                "runner_id": rejection.get("runner_id"),
                "workspace_root": rejection.get("workspace_root"),
                "workspace_roots": rejection.get("workspace_roots"),
            },
        )
    raise api_error(
        409,
        "AI_EXECUTOR_RUNNER_UNAVAILABLE",
        "No active AI executor runner supports the requested executor and workspace",
    )


def _sync_runner_task_to_deployment(
    current_store: Any,
    *,
    runner_id: str,
    task: dict[str, Any],
) -> None:
    if not task.get("deployment_run_id"):
        return
    from app.services.operational_deployments import sync_deployment_runner_task

    sync_deployment_runner_task(
        current_store=current_store,
        runner_id=runner_id,
        task=task,
    )


def claim_ai_executor_task_response(
    *,
    current_store: Any,
    executor_type: str | None,
    request: Request,
    runner_id: str,
) -> dict[str, Any]:
    runner = _authenticated_runner(current_store, request=request, runner_id=runner_id)
    requested_executor = executor_type.lower() if isinstance(executor_type, str) else None
    if requested_executor is not None:
        _ensure_enum(
            requested_executor,
            AI_EXECUTOR_TYPES | {DEPLOYMENT_EXECUTOR_TYPE},
            "executor_type",
        )
    sync_ai_executor_task_store(current_store, runner_id=runner_id, status="queued")
    queued = [
        task
        for task in _read_collection(current_store, "ai_executor_tasks").values()
        if task.get("runner_id") == runner_id
        and task.get("status") == "queued"
        and (requested_executor is None or task.get("executor_type") == requested_executor)
    ]
    queued.sort(key=lambda task: (task.get("created_at") or "", task["id"]))
    if not queued:
        return {"task": None}
    task: dict[str, Any] | None = None
    for candidate in queued:
        candidate_executor = candidate.get("executor_type")
        supports_candidate = (
            DEPLOYMENT_EXECUTOR_TYPE in (runner.get("capabilities") or [])
            if candidate_executor == DEPLOYMENT_EXECUTOR_TYPE
            else candidate_executor in (runner.get("executor_types") or [])
        )
        if not supports_candidate:
            raise api_error(
                409,
                "AI_EXECUTOR_TASK_UNSUPPORTED",
                "Runner does not support task executor",
            )
        if candidate_executor == DEPLOYMENT_EXECUTOR_TYPE:
            task = candidate
            break
        workspace_match = workspace_match_detail(runner, candidate.get("workspace_root"))
        if not workspace_match["allowed"]:
            reject_ai_executor_task_workspace(
                current_store,
                append_task_logs=_append_task_logs,
                persist_record=_persist_record,
                runner=runner,
                sync_ai_task=_sync_runner_completion_to_ai_task,
                sync_scheduled_run=_sync_runner_completion_to_scheduled_run,
                task=candidate,
                workspace_match=workspace_match,
            )
            continue
        task = candidate
        break
    if task is None:
        return {"task": None}
    now_dt = datetime.now(UTC)
    now = now_dt.isoformat()
    task = apply_task_claim_lease(
        {
            **task,
            "claimed_at": now,
            "error_code": None,
            "error_message": None,
            "status": "claimed",
            "updated_at": now,
        },
        now=now_dt,
    )
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_task.claimed",
        actor_id=runner_id,
        subject_type="ai_executor_task",
        subject_id=task["id"],
        payload={"executor_type": task["executor_type"], "runner_id": runner_id},
    )
    _persist_record(
        current_store,
        "save_ai_executor_task_record",
        task,
        audit_event=audit_event,
    )
    _sync_runner_completion_to_scheduled_run(
        current_store,
        task=task,
        runner_id=runner_id,
    )
    _sync_runner_completion_to_ai_task(
        current_store,
        task=task,
        runner_id=runner_id,
    )
    _sync_runner_task_to_deployment(current_store, runner_id=runner_id, task=task)
    return {"task": _task_public(task)}


def _sync_ai_executor_task_by_id(current_store: Any, task_id: str) -> dict[str, Any]:
    sync_ai_executor_task_store(current_store)
    task = _read_record(current_store, "ai_executor_tasks", task_id)
    if task is None:
        raise api_error(404, "NOT_FOUND", "AI executor task not found")
    return task


def _sync_visible_ai_executor_task_by_id(
    current_store: Any,
    *,
    task_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    task = _sync_ai_executor_task_by_id(current_store, task_id)
    if not _ai_executor_task_visible_to_user(current_store, task=task, user=user):
        raise api_error(404, "NOT_FOUND", "AI executor task not found")
    return task


def _log_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _append_task_logs(task: dict[str, Any], logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing = [dict(item) for item in task.get("logs") or [] if isinstance(item, dict)]
    next_sequence = int(existing[-1].get("sequence") or len(existing)) + 1 if existing else 1
    normalized: list[dict[str, Any]] = []
    for item in logs:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "level": str(item.get("level") or "info"),
                "message": str(item.get("message") or ""),
                "sequence": int(item.get("sequence") or next_sequence),
                "timestamp": item.get("timestamp") or _log_timestamp(),
            }
        )
        next_sequence += 1
    return [*existing, *normalized]


def list_ai_executor_task_logs_response(
    *,
    current_store: Any,
    task_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    task = _sync_visible_ai_executor_task_by_id(current_store, task_id=task_id, user=user)
    return {"logs": list(task.get("logs") or []), "task": _task_public(task)}


def append_ai_executor_task_logs_response(
    *,
    current_store: Any,
    payload: Any,
    request: Request,
    task_id: str,
) -> dict[str, Any]:
    runner_id = _ensure_non_blank(getattr(payload, "runner_id", None), "runner_id")
    runner = _authenticated_runner(current_store, request=request, runner_id=runner_id)
    sync_ai_executor_task_store(current_store, runner_id=runner_id)
    task = _read_record(current_store, "ai_executor_tasks", task_id)
    if task is None or task.get("runner_id") != runner_id:
        raise api_error(404, "NOT_FOUND", "AI executor task not found")
    if task.get("status") in AI_EXECUTOR_TASK_TERMINAL_STATUSES:
        raise api_error(409, "AI_EXECUTOR_TASK_TERMINAL", "Terminal task cannot append logs")
    status = str(getattr(payload, "status", None) or task.get("status") or "running")
    if status not in {"claimed", "running"}:
        raise api_error(400, "VALIDATION_ERROR", "Log append status is invalid")
    if task.get("status") == "cancel_requested":
        status = "cancel_requested"
    now_dt = datetime.now(UTC)
    now = now_dt.isoformat()
    task = {
        **task,
        "logs": _append_task_logs(task, list(getattr(payload, "logs", None) or [])),
        "status": status,
        "updated_at": now,
    }
    task = refresh_task_lease(task, now=now_dt)
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_task.logs_appended",
        actor_id=runner_id,
        subject_type="ai_executor_task",
        subject_id=task_id,
        payload={"log_count": len(getattr(payload, "logs", None) or []), "runner_id": runner_id},
    )
    _persist_record(
        current_store,
        "save_ai_executor_task_record",
        task,
        audit_event=audit_event,
    )
    probe_runner = runner_with_deployment_probe_result(runner, task=task)
    if probe_runner is not None:
        probe_audit_event = record_audit_event(
            current_store,
            event_type="ai_executor_runner.deployment_connectivity_recorded",
            actor_id=runner_id,
            subject_type="ai_executor_runner",
            subject_id=runner_id,
            payload={
                "status": task["status"],
                "target_code": task["input_payload"].get("target_code"),
                "task_id": task["id"],
            },
        )
        _persist_record(
            current_store,
            "save_ai_executor_runner_record",
            probe_runner,
            audit_event=probe_audit_event,
        )
    _sync_runner_completion_to_scheduled_run(current_store, task=task, runner_id=runner_id)
    _sync_runner_completion_to_ai_task(current_store, task=task, runner_id=runner_id)
    _sync_runner_task_to_deployment(current_store, runner_id=runner_id, task=task)
    return {"logs": list(task.get("logs") or []), "task": _task_public(task)}


def cancel_ai_executor_task_response(
    *,
    current_store: Any,
    payload: Any,
    task_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    _sync_visible_ai_executor_task_by_id(current_store, task_id=task_id, user=user)
    task = request_ai_executor_task_cancel(
        current_store,
        actor_id=user["id"],
        reason=str(getattr(payload, "reason", None) or "cancelled by user"),
        task_id=task_id,
    )
    return {"task": _task_public(task)}


def request_ai_executor_task_cancel(
    current_store: Any,
    *,
    actor_id: str,
    reason: str,
    task_id: str,
) -> dict[str, Any]:
    task = _sync_ai_executor_task_by_id(current_store, task_id)
    if task.get("status") in AI_EXECUTOR_TASK_TERMINAL_STATUSES:
        raise api_error(409, "AI_EXECUTOR_TASK_TERMINAL", "Terminal task cannot be cancelled")
    now = datetime.now(UTC).isoformat()
    terminal_without_runner = task.get("status") == "queued"
    next_status = "cancelled" if terminal_without_runner else "cancel_requested"
    task = {
        **task,
        "error_code": (
            "AI_EXECUTOR_TASK_CANCELLED"
            if terminal_without_runner
            else "AI_EXECUTOR_TASK_CANCEL_REQUESTED"
        ),
        "error_message": reason,
        "finished_at": now if terminal_without_runner else None,
        "logs": _append_task_logs(
            task,
            [
                {
                    "level": "warning",
                    "message": (
                        f"Task cancelled before claim: {reason}"
                        if terminal_without_runner
                        else f"Task cancellation requested: {reason}"
                    ),
                    "timestamp": now,
                }
            ],
        ),
        "status": next_status,
        "updated_at": now,
    }
    audit_event = record_audit_event(
        current_store,
        event_type=f"ai_executor_task.{next_status}",
        actor_id=actor_id,
        subject_type="ai_executor_task",
        subject_id=task_id,
        payload={"reason": reason, "runner_id": task.get("runner_id")},
    )
    _persist_record(
        current_store,
        "save_ai_executor_task_record",
        task,
        audit_event=audit_event,
    )
    runner_id = str(task.get("runner_id") or actor_id)
    if terminal_without_runner:
        _sync_runner_completion_to_scheduled_run(
            current_store,
            task=task,
            runner_id=runner_id,
        )
        _sync_runner_completion_to_ai_task(
            current_store,
            task=task,
            runner_id=runner_id,
        )
    _sync_runner_task_to_deployment(current_store, runner_id=runner_id, task=task)
    return task


def retry_ai_executor_task_response(
    *,
    current_store: Any,
    payload: Any,
    task_id: str,
    user: dict[str, Any],
) -> dict[str, Any]:
    _ensure_admin(user)
    source_task = _sync_visible_ai_executor_task_by_id(
        current_store,
        task_id=task_id,
        user=user,
    )
    source_status = str(source_task.get("status") or "")
    if source_status not in AI_EXECUTOR_TASK_RETRYABLE_STATUSES:
        raise api_error(
            409,
            "AI_EXECUTOR_TASK_NOT_RETRYABLE",
            "Only cancelled, failed, timed_out or dead_letter tasks can be retried",
        )

    now = datetime.now(UTC).isoformat()
    reason = str(getattr(payload, "reason", None) or "manual retry")
    request_config = dict(source_task.get("request_config") or {})
    retry_history = [
        item for item in request_config.get("retry_history") or [] if isinstance(item, dict)
    ]
    retry_metadata = {
        "reason": reason,
        "retried_at": now,
        "retried_by": user["id"],
        "source_status": source_status,
        "source_task_id": source_task["id"],
    }
    request_config = {
        **request_config,
        "reliability": {},
        "retry_history": [*retry_history, retry_metadata],
        "retry_of_task_id": source_task["id"],
    }
    retry_task = {
        **source_task,
        "claimed_at": None,
        "created_at": now,
        "created_by": user["id"],
        "error_code": None,
        "error_message": None,
        "finished_at": None,
        "id": current_store.new_id("ai_executor_task"),
        "logs": _append_task_logs(
            {},
            [
                {
                    "level": "info",
                    "message": f"Task retried from {source_task['id']}: {reason}",
                    "timestamp": now,
                }
            ],
        ),
        "request_config": request_config,
        "result_json": {},
        "status": "queued",
        "updated_at": now,
    }
    audit_event = record_audit_event(
        current_store,
        event_type="ai_executor_task.retry_requested",
        actor_id=user["id"],
        subject_type="ai_executor_task",
        subject_id=retry_task["id"],
        payload={
            "reason": reason,
            "runner_id": retry_task.get("runner_id"),
            "source_status": source_status,
            "source_task_id": source_task["id"],
        },
    )
    _persist_record(
        current_store,
        "save_ai_executor_task_record",
        retry_task,
        audit_event=audit_event,
    )
    _sync_runner_completion_to_scheduled_run(
        current_store,
        task=retry_task,
        runner_id=str(retry_task.get("runner_id") or user["id"]),
    )
    _sync_runner_completion_to_ai_task(
        current_store,
        task=retry_task,
        runner_id=str(retry_task.get("runner_id") or user["id"]),
    )
    return {"source_task": _task_public(source_task), "task": _task_public(retry_task)}


def complete_ai_executor_task_response(
    *,
    current_store: Any,
    payload: Any,
    request: Request,
    task_id: str,
) -> dict[str, Any]:
    runner_id = _ensure_non_blank(getattr(payload, "runner_id", None), "runner_id")
    runner = _authenticated_runner(current_store, request=request, runner_id=runner_id)
    sync_ai_executor_task_store(current_store, runner_id=runner_id)
    task = _read_record(current_store, "ai_executor_tasks", task_id)
    if task is None or task.get("runner_id") != runner_id:
        raise api_error(404, "NOT_FOUND", "AI executor task not found")
    if task.get("status") in AI_EXECUTOR_TASK_TERMINAL_STATUSES:
        raise api_error(409, "AI_EXECUTOR_TASK_TERMINAL", "Terminal task cannot be completed")
    status = _ensure_enum(getattr(payload, "status", None), AI_EXECUTOR_TASK_STATUSES, "status")
    if status not in AI_EXECUTOR_TASK_TERMINAL_STATUSES and status != "running":
        raise api_error(400, "VALIDATION_ERROR", "Task completion status is invalid")
    now = datetime.now(UTC).isoformat()
    task = {
        **task,
        "error_code": getattr(payload, "error_code", None),
        "error_message": getattr(payload, "error_message", None),
        "finished_at": now if status in AI_EXECUTOR_TASK_TERMINAL_STATUSES else None,
        "logs": _append_task_logs(task, list(getattr(payload, "logs", None) or [])),
        "result_json": dict(getattr(payload, "result_json", None) or {}),
        "status": status,
        "updated_at": now,
    }
    assessment_execution_id = str(
        task.get("input_payload", {}).get("assessment_execution_id") or ""
    )
    audit_event = record_audit_event(
        current_store,
        event_type=f"ai_executor_task.{status}",
        actor_id=runner_id,
        subject_type="ai_executor_task",
        subject_id=task_id,
        payload={
            "executor_type": task["executor_type"],
            "runner_id": runner_id,
            "scheduled_job_id": task.get("scheduled_job_id"),
            "scheduled_job_run_id": task.get("scheduled_job_run_id"),
            "assessment_execution_id": assessment_execution_id or None,
            "model_invocation_id": task["result_json"].get("model_invocation_id"),
            "status": status,
        },
    )
    persisted_assessment_completion = False
    if assessment_execution_id and status == "succeeded":
        from app.services.requirement_assessments import (
            complete_ai_assessment_execution_from_runner,
        )

        assessment_id = str(task["input_payload"].get("assessment_id") or "")
        executor_profile_id = str(task["input_payload"].get("executor_profile_id") or "")
        if not assessment_id or not executor_profile_id:
            raise api_error(
                409,
                "ASSESSMENT_EXECUTION_INVALID",
                "Assessment runner task is missing frozen execution provenance",
            )
        complete_atomically = getattr(
            getattr(current_store, "repository", None),
            "complete_ai_assessment_runner_task",
            None,
        )
        if callable(complete_atomically):
            opinion = task["result_json"].get("assessment_opinion")
            if not isinstance(opinion, dict):
                raise api_error(
                    400,
                    "ASSESSMENT_OPINION_INVALID",
                    "Assessment runner result must include a structured assessment opinion",
                )
            model_invocation_id = str(task["result_json"].get("model_invocation_id") or "").strip()
            if not model_invocation_id:
                raise api_error(
                    400,
                    "ASSESSMENT_MODEL_INVOCATION_INVALID",
                    "Assessment runner result must include model_invocation_id",
                )
            try:
                complete_atomically(
                    task=task,
                    assessment_id=assessment_id,
                    execution_id=assessment_execution_id,
                    executor_profile_id=executor_profile_id,
                    runner_id=runner_id,
                    model_invocation_id=model_invocation_id,
                    opinion={**opinion, "actor_id": executor_profile_id},
                    audit_event=audit_event,
                    outbox_event={
                        "id": f"assessment-runner-complete-{task_id}",
                        "aggregate_type": "requirement_assessment_execution",
                        "aggregate_id": assessment_execution_id,
                        "event_type": "requirement_assessment.runner_completed",
                        "idempotency_key": f"assessment-runner-complete:{task_id}",
                        "payload_json": {
                            "assessment_id": assessment_id,
                            "execution_id": assessment_execution_id,
                            "model_invocation_id": model_invocation_id,
                            "runner_id": runner_id,
                        },
                    },
                )
            except Exception as exc:
                code = getattr(exc, "code", "ASSESSMENT_EXECUTION_INVALID")
                raise api_error(409, code, str(exc)) from exc
            persisted_assessment_completion = True
        else:
            complete_ai_assessment_execution_from_runner(
                current_store=current_store,
                assessment_id=assessment_id,
                execution_id=assessment_execution_id,
                executor_profile_id=executor_profile_id,
                runner_id=runner_id,
                model_result={
                    "model_invocation_id": task["result_json"].get("model_invocation_id"),
                    "assessment_opinion": task["result_json"].get("assessment_opinion"),
                },
            )
    if not persisted_assessment_completion:
        _persist_record(
            current_store,
            "save_ai_executor_task_record",
            task,
            audit_event=audit_event,
        )
    probe_runner = runner_with_deployment_probe_result(runner, task=task)
    if probe_runner is not None:
        probe_audit_event = record_audit_event(
            current_store,
            event_type="ai_executor_runner.deployment_connectivity_recorded",
            actor_id=runner_id,
            subject_type="ai_executor_runner",
            subject_id=runner_id,
            payload={
                "status": task["status"],
                "target_code": task["input_payload"].get("target_code"),
                "task_id": task["id"],
            },
        )
        _persist_record(
            current_store,
            "save_ai_executor_runner_record",
            probe_runner,
            audit_event=probe_audit_event,
        )
    _sync_runner_completion_to_scheduled_run(
        current_store,
        task=task,
        runner_id=runner_id,
    )
    _sync_runner_completion_to_ai_task(
        current_store,
        task=task,
        runner_id=runner_id,
    )
    _sync_runner_task_to_deployment(current_store, runner_id=runner_id, task=task)
    return {"task": _task_public(task)}
