"""Deterministic public-API Runner protocol for fast v2 collaboration suites."""

from __future__ import annotations

import base64
import json
import secrets
from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from full_chain_regression_rd_fixture import (
    frozen_ai_and_human_role_bindings,
    safe_report_value,
    wait_for_value,
)

_COMPLETION_LOG = {"level": "info", "message": "deterministic v2 regression completed"}
_COMPLETION_RESULT = {"summary": "deterministic v2 regression output"}
_CODE_REVIEW_COMPLETION_RESULT = {
    **_COMPLETION_RESULT,
    "findings": [],
    "risk_level": "low",
}


@dataclass(frozen=True)
class SimulatedRunnerSession:
    runner_id: str
    runner_headers: dict[str, str]
    executor_profile_id: str
    ai_employee_id: str
    verification_runner_id: str | None = None
    verification_runner_headers: dict[str, str] | None = field(default=None, repr=False)
    verification_private_key: Ed25519PrivateKey | None = field(
        default=None,
        repr=False,
        compare=False,
    )


@dataclass(frozen=True)
class SimulatedAiResult:
    ai_task_id: str
    attempt_id: str
    review_id: str
    runner_task_ids: tuple[str, ...]
    work_item: dict[str, Any]
    runner_result: dict[str, Any]
    secret_values: tuple[str, ...] = field(default=(), repr=False, compare=False)

    @property
    def step_detail(self) -> str:
        return (
            f"ai_task={self.ai_task_id} / work_item={self.work_item.get('id')} "
            f"/ runner_tasks={','.join(self.runner_task_ids)}"
        )

    @property
    def report(self) -> dict[str, Any]:
        return safe_report_value(
            {
                "ai_task_id": self.ai_task_id,
                "attempt_id": self.attempt_id,
                "review_id": self.review_id,
                "runner_result": self.runner_result,
                "runner_task_ids": self.runner_task_ids,
                "work_item": self.work_item,
            },
            secret_values=self.secret_values,
        )


def simulated_runner_role_bindings(
    session: SimulatedRunnerSession,
    *,
    role_code: str,
    reviewer_user_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Expose the frozen policy bindings needed by a simulated v2 fixture."""
    return frozen_ai_and_human_role_bindings(
        ai_employee_id=session.ai_employee_id,
        executor_profile_id=session.executor_profile_id,
        role_code=role_code,
        reviewer_user_id=reviewer_user_id,
    )


def _require_text(value: Any, description: str) -> str:
    text = str(value or "").strip()
    assert text, f"{description} is required"
    return text


def _runner_task(
    response: dict[str, Any],
    *,
    runner_id: str,
    secret_values: tuple[str, ...],
) -> dict[str, Any]:
    task = response.get("task") or {}
    assert isinstance(task, dict) and task.get("id"), (
        f"Runner {runner_id} did not claim a task: "
        f"{safe_report_value(response, secret_values=secret_values)}"
    )
    return task


def _complete_runner_task(
    client: Any,
    *,
    runner_headers: dict[str, str],
    runner_id: str,
    result_json: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:
    task_id = _require_text(task.get("id"), "Runner task id")
    client.post(
        f"/api/system/ai-executor-tasks/{task_id}/logs",
        {
            "logs": [_COMPLETION_LOG],
            "runner_id": runner_id,
            "status": "running",
        },
        headers=runner_headers,
    )
    completed = client.post(
        f"/api/system/ai-executor-tasks/{task_id}/complete",
        {
            "logs": [_COMPLETION_LOG],
            "result_json": result_json,
            "runner_id": runner_id,
            "status": "succeeded",
        },
        headers=runner_headers,
    )
    completed_task = completed.get("task") or {}
    assert completed_task.get("status") == "succeeded", (
        "Runner task was not completed: "
        f"{safe_report_value(completed, secret_values=tuple(runner_headers.values()))}"
    )
    return completed_task


def _completion_result(task: dict[str, Any]) -> dict[str, Any]:
    input_payload = task.get("input_payload") or {}
    task_snapshot = input_payload.get("task") or {}
    task_type = str(task_snapshot.get("task_type") or task.get("task_type") or "").strip()
    if task_type == "code_review":
        return dict(_CODE_REVIEW_COMPLETION_RESULT)
    return dict(_COMPLETION_RESULT)


def _claim_runner_task(
    client: Any,
    *,
    runner_headers: dict[str, str],
    runner_id: str,
    executor_type: str,
) -> dict[str, Any]:
    return _runner_task(
        client.post(
            "/api/system/ai-executor-tasks/claim",
            {"executor_type": executor_type, "runner_id": runner_id},
            headers=runner_headers,
        ),
        runner_id=runner_id,
        secret_values=tuple(runner_headers.values()),
    )


def _quality_gate_task(
    client: Any,
    *,
    ai_task_id: str,
    secret_values: tuple[str, ...],
    timeout_seconds: float,
) -> dict[str, Any]:
    def fetch() -> dict[str, Any]:
        return client.get(
            "/api/system/ai-executor-tasks",
            {"ai_task_id": ai_task_id, "status": "queued"},
        )

    def queued_quality_gate(response: dict[str, Any]) -> bool:
        return any(
            item.get("task_kind") == "quality_gate" for item in response.get("items") or []
        )

    queued = wait_for_value(
        fetch,
        queued_quality_gate,
        timeout_seconds=timeout_seconds,
        description="verification quality-gate Runner task",
        secret_values=secret_values,
    )
    return next(
        item for item in queued.get("items") or [] if item.get("task_kind") == "quality_gate"
    )


def _quality_gate_result(
    task: dict[str, Any],
    *,
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    task_id = _require_text(task.get("id"), "Quality gate Runner task id")
    checks = []
    for check in (task.get("input_payload") or {}).get("checks") or []:
        if not isinstance(check, dict):
            continue
        check_type = _require_text(check.get("type"), "Check type")
        checks.append(
            {
                "evidence_ref": f"simulated://{task_id}/{check_type}",
                "status": "passed",
                "type": check_type,
            }
        )
    assert checks, "Quality gate Runner task did not include required checks"
    attestation_payload = {"runner_task_id": task_id}
    signature = private_key.sign(
        json.dumps(
            attestation_payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )
    return {
        "checks": checks,
        "execution_attestation": {
            "payload": attestation_payload,
            "signature": base64.b64encode(signature).decode("ascii"),
        },
        "summary": _COMPLETION_RESULT["summary"],
    }


def _work_item(
    client: Any,
    *,
    run_id: str,
    secret_values: tuple[str, ...],
    work_item_id: str,
) -> dict[str, Any]:
    response = client.get(f"/api/delivery/rd-collaboration-runs/{run_id}/work-items")
    item = next(
        (item for item in response.get("items") or [] if item.get("id") == work_item_id),
        None,
    )
    assert isinstance(item, dict), (
        "Collaboration work item was not returned: "
        f"{safe_report_value(response, secret_values=secret_values)}"
    )
    return item


def create_simulated_runner_session(
    client: Any,
    marker: str,
    workspace_root: str,
    role_codes: tuple[str, ...],
) -> SimulatedRunnerSession:
    """Provision a disposable coding Runner and its frozen AI execution identity."""
    token = secrets.token_urlsafe(32)
    runner = client.post(
        "/api/system/ai-executor-runners",
        {
            "executor_types": ["codex"],
            "name": f"Simulated v2 Runner {marker}",
            "protocol": "runner_polling",
            "runner_token": token,
            "trust_boundary_id": f"simulated-coding-{marker}",
            "trust_domain": "coding",
            "workspace_roots": [workspace_root],
        },
    )
    runner_id = _require_text(runner.get("id"), "Simulated Runner id")
    verification_token = secrets.token_urlsafe(32)
    verification_private_key = Ed25519PrivateKey.generate()
    verification_public_key = base64.b64encode(
        verification_private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
    ).decode("ascii")
    verification_runner = client.post(
        "/api/system/ai-executor-runners",
        {
            "attestation_public_key": verification_public_key,
            "attestation_status": "active",
            "executor_types": ["codex"],
            "name": f"Simulated v2 verification Runner {marker}",
            "protocol": "runner_polling",
            "runner_token": verification_token,
            "trust_boundary_id": f"simulated-verification-{marker}",
            "trust_domain": "verification",
            "workspace_roots": [workspace_root],
        },
    )
    verification_runner_id = _require_text(
        verification_runner.get("id"), "Simulated verification Runner id"
    )
    employee = client.post(
        "/api/delivery/rd-ai-employees",
        {
            "capability_tags": ["product_detail_design"],
            "code": f"simulated-ai-{marker}",
            "name": f"Simulated v2 AI employee {marker}",
            "persona_json": {"mode": "deterministic_regression"},
            "persona_version": 1,
            "work_style_json": {"mode": "single_pass"},
            "work_style_version": 1,
        },
    )
    ai_employee_id = _require_text(employee.get("id"), "Simulated AI employee id")
    profile = client.post(
        "/api/delivery/rd-executor-profiles",
        {
            "code": f"simulated-runner-profile-{marker}",
            "executor_type": "codex",
            "health_status": "healthy",
            "max_concurrency": 1,
            "name": f"Simulated v2 Runner profile {marker}",
            "runner_id": runner_id,
            "supported_role_codes": list(role_codes),
            "workspace_capabilities": {"workspace_root": workspace_root},
        },
    )
    executor_profile_id = _require_text(profile.get("id"), "Simulated executor profile id")
    return SimulatedRunnerSession(
        runner_id=runner_id,
        runner_headers={"X-Runner-Token": token},
        executor_profile_id=executor_profile_id,
        ai_employee_id=ai_employee_id,
        verification_runner_id=verification_runner_id,
        verification_runner_headers={"X-Runner-Token": verification_token},
        verification_private_key=verification_private_key,
    )


def complete_ai_work_item_via_runner_protocol(
    client: Any,
    session: SimulatedRunnerSession,
    run_id: str,
    work_item_id: str,
    reviewer_client: Any,
    timeout_seconds: float,
) -> SimulatedAiResult:
    """Drive queued Runner work to independent Review without Git delivery."""
    session_secret_values = tuple(
        value
        for headers in (session.runner_headers, session.verification_runner_headers or {})
        for value in headers.values()
    )
    first_task = _claim_runner_task(
        client,
        runner_headers=session.runner_headers,
        runner_id=session.runner_id,
        executor_type="codex",
    )
    ai_task_id = _require_text(first_task.get("ai_task_id"), "AI task id")
    attempt_id = _require_text(
        (first_task.get("input_payload") or {}).get("rd_work_item_attempt_id"),
        "R&D work-item attempt id",
    )
    runner_task_ids = [_require_text(first_task.get("id"), "Runner task id")]
    completion_result = _completion_result(first_task)
    completed_task = _complete_runner_task(
        client,
        runner_headers=session.runner_headers,
        runner_id=session.runner_id,
        result_json=completion_result,
        task=first_task,
    )

    post_coding_task: dict[str, Any] | None = None
    if first_task.get("task_kind") == "coding":
        post_coding_task = wait_for_value(
            lambda: client.get(f"/api/ai-tasks/{ai_task_id}"),
            lambda task: task.get("status") == "waiting_review"
            or task.get("current_step") == "quality_gate_running",
            timeout_seconds=timeout_seconds,
            description="coding AI task selecting review or quality-gate path",
            secret_values=session_secret_values,
        )
    if (
        post_coding_task is not None
        and post_coding_task.get("current_step") == "quality_gate_running"
    ):
        gate_task = _quality_gate_task(
            client,
            ai_task_id=ai_task_id,
            secret_values=session_secret_values,
            timeout_seconds=timeout_seconds,
        )
        gate_runner_id = _require_text(gate_task.get("runner_id"), "Verification Runner id")
        assert gate_runner_id == session.verification_runner_id, (
            "Quality gate Runner does not match the independent verification session"
        )
        verification_headers = session.verification_runner_headers or {}
        verification_private_key = session.verification_private_key
        assert verification_headers and verification_private_key is not None, (
            "Quality gate requires a verification-trust Runner session"
        )
        assert (
            (gate_task.get("request_config") or {}).get("required_trust_domain")
            == "verification"
        ), (
            f"Quality gate did not require verification trust: {safe_report_value(gate_task)}"
        )
        claimed_gate = _claim_runner_task(
            client,
            runner_headers=verification_headers,
            runner_id=gate_runner_id,
            executor_type=_require_text(
                gate_task.get("executor_type"), "Quality gate executor type"
            ),
        )
        assert claimed_gate.get("id") == gate_task.get("id"), (
            f"Verification Runner claimed an unexpected task: {safe_report_value(claimed_gate)}"
        )
        runner_task_ids.append(_require_text(claimed_gate.get("id"), "Quality gate Runner task id"))
        completed_task = _complete_runner_task(
            client,
            runner_headers=verification_headers,
            runner_id=gate_runner_id,
            result_json=_quality_gate_result(
                claimed_gate,
                private_key=verification_private_key,
            ),
            task=claimed_gate,
        )
        wait_for_value(
            lambda: _work_item(
                client,
                run_id=run_id,
                secret_values=session_secret_values,
                work_item_id=work_item_id,
            ),
            lambda item: item.get("status") == "reviewing",
            timeout_seconds=timeout_seconds,
            description="quality-gated collaboration work item awaiting review",
            secret_values=session_secret_values,
        )

    waiting_task = (
        post_coding_task
        if post_coding_task is not None
        and post_coding_task.get("status") == "waiting_review"
        else wait_for_value(
            lambda: client.get(f"/api/ai-tasks/{ai_task_id}"),
            lambda task: task.get("status") == "waiting_review",
            timeout_seconds=timeout_seconds,
            description="AI task waiting for independent review",
            secret_values=session_secret_values,
        )
    )
    pending_review = waiting_task.get("pending_review") or {}
    review_id = _require_text(pending_review.get("id"), "Pending review id")
    pending = reviewer_client.get("/api/reviews/pending", {"ai_task_id": ai_task_id})
    review = next(
        (item for item in pending.get("items") or [] if item.get("id") == review_id),
        None,
    )
    assert isinstance(review, dict), (
        "Independent reviewer cannot see pending review: "
        f"{safe_report_value(pending, secret_values=session_secret_values)}"
    )
    approved = reviewer_client.post(
        f"/api/reviews/{review_id}/approve",
        {"version": review["version"]},
    )
    assert approved.get("task_status") == "completed", (
        f"Independent review did not complete AI task: {safe_report_value(approved)}"
    )
    work_item = wait_for_value(
        lambda: _work_item(
            client,
            run_id=run_id,
            secret_values=session_secret_values,
            work_item_id=work_item_id,
        ),
        lambda item: item.get("status") == "completed",
        timeout_seconds=timeout_seconds,
        description="AI-owned collaboration work item completion",
        secret_values=session_secret_values,
    )
    return SimulatedAiResult(
        ai_task_id=ai_task_id,
        attempt_id=attempt_id,
        review_id=review_id,
        runner_task_ids=tuple(runner_task_ids),
        work_item=work_item,
        runner_result={
            "result_json": completion_result,
            "runner_task_id": completed_task.get("id"),
            "status": completed_task.get("status"),
        },
        secret_values=session_secret_values,
    )
