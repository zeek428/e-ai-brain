from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class StepResult:
    name: str
    detail: str


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _ids(items: list[dict[str, Any]]) -> set[str]:
    return {str(item.get("id")) for item in items if item.get("id")}


def _assert_contains(values: set[str], expected: str, message: str) -> None:
    _assert(expected in values, f"{message}: expected {expected}, got {sorted(values)}")


def expect_api_error(
    call: Callable[[], Any],
    *,
    code: str | None = None,
    message: str,
    status: int,
) -> None:
    try:
        call()
    except Exception as exc:
        if getattr(exc, "status", None) == status:
            if code:
                try:
                    body = json.loads(str(getattr(exc, "body", "") or "{}"))
                except json.JSONDecodeError as parse_exc:
                    raise AssertionError(f"{message}: failed to parse error body {exc}") from parse_exc
                actual_code = (body.get("detail") or {}).get("code") if isinstance(body, dict) else None
                if actual_code != code:
                    raise AssertionError(f"{message}: expected error code {code}, got {actual_code}") from exc
            return
        raise AssertionError(f"{message}: unexpected error {exc}") from exc
    raise AssertionError(message)


def validate_runner_token_rotation(
    client: Any,
    *,
    old_runner_token: str,
    runner: dict[str, Any],
    slug: str,
) -> tuple[dict[str, str], StepResult]:
    new_runner_token = f"{old_runner_token}-rotated"
    rotated = client.post(
        f"/api/system/ai-executor-runners/{runner['id']}/rotate-token",
        {"runner_token": new_runner_token},
    )
    _assert(
        rotated.get("runner_token") == new_runner_token,
        f"Runner token rotation did not return the one-time token: {rotated}",
    )
    _assert(
        int(rotated.get("token_version") or 0) >= 2,
        f"Runner token rotation did not increment token_version: {rotated}",
    )
    _assert(rotated.get("token_rotated_at"), f"Runner token rotation missed timestamp: {rotated}")

    old_runner_headers = {"X-Runner-Token": old_runner_token}
    expect_api_error(
        lambda: client.post(
            f"/api/system/ai-executor-runners/{runner['id']}/heartbeat",
            {"metadata": {"source": "old-token-after-rotation", "slug": slug}},
            headers=old_runner_headers,
        ),
        status=401,
        message="old runner token was still accepted after rotation",
    )

    new_runner_headers = {"X-Runner-Token": new_runner_token}
    heartbeat = client.post(
        f"/api/system/ai-executor-runners/{runner['id']}/heartbeat",
        {"metadata": {"source": "new-token-after-rotation", "slug": slug}},
        headers=new_runner_headers,
    )
    _assert(
        heartbeat.get("last_heartbeat_at"),
        f"Runner heartbeat with rotated token did not update heartbeat: {heartbeat}",
    )
    _assert(
        heartbeat.get("health_status") == "online",
        f"Runner heartbeat with rotated token did not restore online health: {heartbeat}",
    )
    _assert(
        heartbeat.get("health_alert") is None,
        f"Runner heartbeat with rotated token still returned health_alert: {heartbeat}",
    )
    return (
        new_runner_headers,
        StepResult("runner_token_rotation", f"token_version={rotated.get('token_version')}"),
    )


def validate_runner_health_alert_projection(runner: dict[str, Any]) -> StepResult:
    alert = runner.get("health_alert") or {}
    _assert(
        runner.get("health_status") == "never_connected",
        f"New Runner did not start as never_connected: {runner}",
    )
    _assert(
        alert.get("code") == "runner_never_connected",
        f"New Runner missed never_connected health_alert: {runner}",
    )
    _assert(
        alert.get("severity") == "warning",
        f"New Runner health_alert severity is unexpected: {runner}",
    )
    _assert(
        "启动本地 Runner" in str(alert.get("message") or ""),
        f"New Runner health_alert missed remediation message: {runner}",
    )
    return StepResult("runner_health_alert", str(alert.get("code")))


def validate_runner_cancel_retry(
    client: Any,
    *,
    action: dict[str, Any],
    runner: dict[str, Any],
    runner_headers: dict[str, str],
) -> StepResult:
    cancel_invoked = client.post(
        f"/api/system/plugin-actions/{action['id']}/invoke",
        {"input_payload": {"source": "full-chain-runner-cancel-retry"}},
    )
    cancel_task_id = str(cancel_invoked["response_summary"]["json"]["runner_task_id"])

    cancel_claim = client.post(
        "/api/system/ai-executor-tasks/claim",
        {"executor_type": "openclaw", "runner_id": runner["id"]},
        headers=runner_headers,
    )
    cancel_claim_task = cancel_claim.get("task") or {}
    _assert(
        cancel_claim_task.get("id") == cancel_task_id,
        f"Runner cancel/retry task was not claimed first: {cancel_claim}",
    )

    appended_logs = client.post(
        f"/api/system/ai-executor-tasks/{cancel_task_id}/logs",
        {
            "logs": [
                {"level": "info", "message": "cancel retry smoke checkout"},
                {"level": "info", "message": "cancel retry smoke running"},
            ],
            "runner_id": runner["id"],
            "status": "running",
        },
        headers=runner_headers,
    )
    _assert(
        (appended_logs.get("task") or {}).get("status") == "running",
        f"Runner cancel/retry task did not enter running state: {appended_logs}",
    )
    running_logs = client.get(f"/api/system/ai-executor-tasks/{cancel_task_id}/logs")
    _assert(
        [entry.get("sequence") for entry in running_logs.get("logs", [])][:2] == [1, 2],
        f"Runner cancel/retry task logs missed ordered runner entries: {running_logs}",
    )

    cancelled = client.post(
        f"/api/system/ai-executor-tasks/{cancel_task_id}/cancel",
        {"reason": "full-chain cancel retry gate"},
    )
    cancelled_task = cancelled.get("task") or {}
    _assert(cancelled_task.get("status") == "cancelled", f"Runner task was not cancelled: {cancelled}")
    _assert(
        cancelled_task.get("error_code") == "AI_EXECUTOR_TASK_CANCELLED",
        f"Runner cancelled task error code drifted: {cancelled}",
    )

    retried = client.post(
        f"/api/system/ai-executor-tasks/{cancel_task_id}/retry",
        {"reason": "full-chain retry after cancel"},
    )
    source_task = retried.get("source_task") or {}
    retried_task = retried.get("task") or {}
    retry_task_id = str(retried_task.get("id") or "")
    retry_config = retried_task.get("request_config") or {}
    retry_history = retry_config.get("retry_history") or []
    _assert(source_task.get("id") == cancel_task_id, f"Runner retry missed source task: {retried}")
    _assert(retry_task_id and retry_task_id != cancel_task_id, f"Runner retry reused source task id: {retried}")
    _assert(retried_task.get("status") == "queued", f"Runner retry task was not queued: {retried}")
    _assert(
        retry_config.get("retry_of_task_id") == cancel_task_id,
        f"Runner retry task missed retry_of_task_id: {retried_task}",
    )
    _assert(
        retry_history and retry_history[-1].get("source_status") == "cancelled",
        f"Runner retry task missed cancelled retry_history: {retried_task}",
    )
    _assert(
        str((retried_task.get("logs") or [{}])[0].get("message") or "").startswith(
            f"Task retried from {cancel_task_id}"
        ),
        f"Runner retry task missed seed retry log: {retried_task}",
    )

    retry_claim = client.post(
        "/api/system/ai-executor-tasks/claim",
        {"executor_type": "openclaw", "runner_id": runner["id"]},
        headers=runner_headers,
    )
    _assert(
        (retry_claim.get("task") or {}).get("id") == retry_task_id,
        f"Runner did not claim retried task: {retry_claim}",
    )

    retry_complete = client.post(
        f"/api/system/ai-executor-tasks/{retry_task_id}/complete",
        {
            "logs": [{"level": "info", "message": "retry succeeded"}],
            "result_json": {"ok": True},
            "runner_id": runner["id"],
            "status": "succeeded",
        },
        headers=runner_headers,
    )
    _assert(
        (retry_complete.get("task") or {}).get("status") == "succeeded",
        f"Runner retried task did not complete: {retry_complete}",
    )

    expect_api_error(
        lambda: client.post(
            f"/api/system/ai-executor-tasks/{retry_task_id}/retry",
            {"reason": "full-chain duplicate retry guard"},
        ),
        code="AI_EXECUTOR_TASK_NOT_RETRYABLE",
        status=409,
        message="succeeded runner task was unexpectedly retryable",
    )

    cancelled_logs = client.get(f"/api/system/ai-executor-tasks/{cancel_task_id}/logs")
    _assert(
        any(
            entry.get("level") == "warning" and "cancel" in str(entry.get("message") or "").lower()
            for entry in cancelled_logs.get("logs", [])
        ),
        f"Runner cancelled task logs missed warning entry: {cancelled_logs}",
    )
    retry_audit = client.get(
        "/api/audit/events",
        {"event_type": "ai_executor_task.retry_requested", "subject_id": retry_task_id},
    )
    audit_items = retry_audit.get("items") or []
    _assert(
        audit_items and (audit_items[0].get("payload") or {}).get("source_task_id") == cancel_task_id,
        f"Runner retry audit missed source task link: {retry_audit}",
    )
    return StepResult("runner_cancel_retry", f"{cancel_task_id} -> {retry_task_id}")


def validate_ai_executor_runner_reliability(
    client: Any,
    *,
    repo_path: Path,
    slug: str,
) -> list[StepResult]:
    client.get("/api/system/plugin-marketplace")
    runner_token = f"runner-lease-{slug}"
    runner = client.post(
        "/api/system/ai-executor-runners",
        {
            "executor_types": ["openclaw"],
            "heartbeat_timeout_seconds": 30,
            "name": f"全链路 Runner 租约 {slug}",
            "protocol": "runner_polling",
            "runner_token": runner_token,
            "workspace_roots": [str(repo_path)],
        },
    )
    runner_health_alert_result = validate_runner_health_alert_projection(runner)
    runner_headers = {"X-Runner-Token": runner_token}
    initial_heartbeat = client.post(
        f"/api/system/ai-executor-runners/{runner['id']}/heartbeat",
        {"metadata": {"source": "full_chain_regression"}},
        headers=runner_headers,
    )
    _assert(
        initial_heartbeat.get("health_status") == "online",
        f"Runner initial heartbeat did not restore online health: {initial_heartbeat}",
    )
    _assert(
        initial_heartbeat.get("health_alert") is None,
        f"Runner initial heartbeat still returned health_alert: {initial_heartbeat}",
    )
    runner_headers, token_rotation_result = validate_runner_token_rotation(
        client,
        old_runner_token=runner_token,
        runner=runner,
        slug=slug,
    )

    code_suffix = slug.replace("-", "_")
    connection = client.post(
        "/api/system/plugin-connections",
        {
            "auth_type": "none",
            "endpoint_url": "runner://ai-executor",
            "environment": "dev",
            "name": f"全链路 Runner 连接 {slug}",
            "plugin_id": "plugin_standard_ai_executor",
            "request_config": {
                "query": {
                    "executor_type": "openclaw",
                    "instruction_timeout_seconds": 3600,
                    "lease_timeout_seconds": 1,
                    "max_reclaim_count": 1,
                    "runner_id": runner["id"],
                    "workspace_root": str(repo_path),
                }
            },
            "status": "active",
        },
    )
    action = client.post(
        "/api/system/plugin-actions",
        {
            "action_type": "mcp_tool",
            "code": f"full_chain_runner_lease_{code_suffix}",
            "connection_id": connection["id"],
            "name": f"全链路 Runner 租约恢复 {slug}",
            "plugin_id": "plugin_standard_ai_executor",
            "request_config": {
                "instruction": "执行一次全链路回归 Runner 租约检测，不需要真实修改仓库。",
                "tool_name": "ai_executor.run_instruction",
            },
            "result_mapping": {"write_target": "scheduled_job_result"},
            "status": "active",
        },
    )
    cancel_retry_result = validate_runner_cancel_retry(
        client,
        action=action,
        runner=runner,
        runner_headers=runner_headers,
    )

    invoked = client.post(
        f"/api/system/plugin-actions/{action['id']}/invoke",
        {"input_payload": {"source": "full-chain-runner-reliability"}},
    )
    task_id = str(invoked["response_summary"]["json"]["runner_task_id"])

    first_claim = client.post(
        "/api/system/ai-executor-tasks/claim",
        {"executor_type": "openclaw", "runner_id": runner["id"]},
        headers=runner_headers,
    )
    first_claim_task = first_claim.get("task") or {}
    _assert(first_claim_task.get("id") == task_id, f"Runner did not claim expected task: {first_claim}")
    reliability = (first_claim_task.get("request_config") or {}).get("reliability") or {}
    _assert(
        int(reliability.get("lease_timeout_seconds") or 0) == 1,
        f"Runner task lease timeout was not persisted: {first_claim_task}",
    )

    requeue_scan = client.post(
        "/api/system/ai-executor-tasks/timeout-scan",
        {"now": "2099-01-01T00:00:00+00:00"},
    )
    _assert(task_id in set(requeue_scan.get("requeued_task_ids") or []), f"Runner task was not requeued: {requeue_scan}")
    requeued_task = next((task for task in requeue_scan.get("tasks", []) if task.get("id") == task_id), {})
    _assert(requeued_task.get("status") == "queued", f"Requeued runner task did not return to queued: {requeued_task}")
    requeued_reliability = (requeued_task.get("request_config") or {}).get("reliability") or {}
    _assert(
        int(requeued_reliability.get("reclaim_count") or 0) == 1,
        f"Runner task reclaim count was not incremented: {requeued_task}",
    )

    second_claim = client.post(
        "/api/system/ai-executor-tasks/claim",
        {"executor_type": "openclaw", "runner_id": runner["id"]},
        headers=runner_headers,
    )
    _assert(
        (second_claim.get("task") or {}).get("id") == task_id,
        f"Runner did not reclaim expected task: {second_claim}",
    )

    dead_letter_scan = client.post(
        "/api/system/ai-executor-tasks/timeout-scan",
        {"now": "2099-01-01T00:00:00+00:00"},
    )
    _assert(
        task_id in set(dead_letter_scan.get("dead_letter_task_ids") or []),
        f"Runner task was not moved to dead letter: {dead_letter_scan}",
    )
    dead_letter_task = next((task for task in dead_letter_scan.get("tasks", []) if task.get("id") == task_id), {})
    _assert(dead_letter_task.get("status") == "dead_letter", f"Runner task status is not dead_letter: {dead_letter_task}")
    _assert(
        dead_letter_task.get("error_code") == "AI_EXECUTOR_TASK_LEASE_EXPIRED",
        f"Runner dead letter error code is unexpected: {dead_letter_task}",
    )

    dead_letter_tasks = client.get(
        "/api/system/ai-executor-tasks",
        {"page": 1, "page_size": 10, "status": "dead_letter"},
    )
    _assert_contains(_ids(dead_letter_tasks.get("items", [])), task_id, "Runner dead letter task missing from task list")
    task_logs = client.get(f"/api/system/ai-executor-tasks/{task_id}/logs")
    log_levels = [entry.get("level") for entry in task_logs.get("logs", [])]
    _assert("warning" in log_levels and "error" in log_levels, f"Runner lease logs are incomplete: {task_logs}")
    return [
        runner_health_alert_result,
        token_rotation_result,
        cancel_retry_result,
        StepResult("runner_reliability", f"{task_id} / requeued=1 / dead_letter=1"),
    ]
