#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.client
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse


DEFAULT_API_BASE_URL = "http://localhost:8000"
FIXTURE_ROOT = Path(os.getenv("AI_BRAIN_FULL_CHAIN_FIXTURE_ROOT", "/tmp/e-ai-brain-full-chain-fixtures"))
VERSION_DASHBOARD_BLOCKER_SEVERITIES = {"info", "low", "medium", "high", "critical", "blocker"}


class RegressionError(RuntimeError):
    pass


class ApiError(RegressionError):
    def __init__(self, method: str, path: str, status: int, body: str):
        super().__init__(f"{method} {path} failed with HTTP {status}: {body}")
        self.body = body
        self.method = method
        self.path = path
        self.status = status


@dataclass
class StepResult:
    name: str
    detail: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_regression_report(
    *,
    api_base_url: str,
    duration_ms: int,
    error: str | None,
    finished_at: str,
    started_at: str,
    status: str,
    steps: list[StepResult],
    suite: str,
    task_execution_mode: str,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "api_base_url": api_base_url,
        "duration_ms": duration_ms,
        "finished_at": finished_at,
        "started_at": started_at,
        "status": status,
        "steps": [{"detail": step.detail, "name": step.name} for step in steps],
        "suite": suite,
        "task_execution_mode": task_execution_mode,
    }
    if error:
        report["error"] = error
    return report


def write_json_report(path: str, report: dict[str, Any]) -> None:
    report_path = Path(path).expanduser()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class ApiClient:
    def __init__(self, base_url: str, *, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        parsed_base_url = urlparse(self.base_url)
        if parsed_base_url.scheme not in {"http", "https"}:
            raise RegressionError(f"Unsupported API base URL scheme: {self.base_url}")
        if not parsed_base_url.hostname:
            raise RegressionError(f"API base URL is missing host: {self.base_url}")
        self._base_path = parsed_base_url.path.rstrip("/")
        self._host = parsed_base_url.hostname
        self._port = parsed_base_url.port
        self._scheme = parsed_base_url.scheme
        self.timeout = timeout
        self.token: str | None = None

    def login(self, username: str, password: str) -> dict[str, Any]:
        payload = self.request(
            "POST",
            "/api/auth/login",
            body={"password": password, "username": username},
            authenticated=False,
        )
        token = payload.get("access_token")
        if not token:
            raise RegressionError("Login succeeded but access_token is missing.")
        self.token = str(token)
        return payload

    def get(
        self,
        path: str,
        query: dict[str, Any] | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if query:
            path = f"{path}?{urlencode({key: value for key, value in query.items() if value is not None})}"
        return self.request("GET", path, extra_headers=headers)

    def post(
        self,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return self.request("POST", path, body=body or {}, extra_headers=headers)

    def request(
        self,
        method: str,
        path: str,
        *,
        authenticated: bool = True,
        body: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Accept": "application/json", "Connection": "close"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if authenticated:
            if not self.token:
                raise RegressionError("Authenticated request attempted before login.")
            headers["Authorization"] = f"Bearer {self.token}"
        if extra_headers:
            headers.update(extra_headers)
        connection_class = http.client.HTTPSConnection if self._scheme == "https" else http.client.HTTPConnection
        connection = connection_class(self._host, self._port, timeout=self.timeout)
        target = f"{self._base_path}{path}" if self._base_path else path
        try:
            connection.request(method, target, body=data, headers=headers)
            response = connection.getresponse()
            raw = response.read().decode("utf-8", errors="replace")
            if response.status >= 400:
                raise ApiError(method, path, response.status, raw)
        except OSError as exc:
            raise RegressionError(f"{method} {path} failed: {exc}") from exc
        finally:
            connection.close()
        parsed = json.loads(raw) if raw else {}
        if isinstance(parsed, dict) and "data" in parsed:
            return parsed["data"]
        return parsed


def _slug() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"full-chain-{timestamp}"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RegressionError(message)


def _ids(items: list[dict[str, Any]]) -> set[str]:
    return {str(item["id"]) for item in items if item.get("id")}


def _status_count(items: list[dict[str, Any]], status: str) -> int:
    for item in items:
        if item.get("status") == status:
            return int(item.get("count") or 0)
    return 0


def _assert_contains(container: set[str], expected: str, message: str) -> None:
    _assert(expected in container, f"{message}: expected {expected}, got {sorted(container)}")


def expect_api_error(callable_request: Any, *, status: int, message: str) -> ApiError:
    try:
        callable_request()
    except ApiError as exc:
        _assert(
            exc.status == status,
            f"{message}: expected HTTP {status}, got {exc.status}",
        )
        return exc
    raise RegressionError(message)


def validate_version_dashboard_blocker_actions(blockers: list[dict[str, Any]]) -> None:
    for blocker in blockers:
        _assert(blocker.get("source_type"), f"Version dashboard blocker missed source_type: {blocker}")
        _assert(blocker.get("title"), f"Version dashboard blocker missed title: {blocker}")
        _assert(blocker.get("reason"), f"Version dashboard blocker missed reason: {blocker}")
        severity = str(blocker.get("severity") or "").lower()
        _assert(
            severity in VERSION_DASHBOARD_BLOCKER_SEVERITIES,
            f"Version dashboard blocker has unsupported severity: {blocker}",
        )
        _assert(blocker.get("action_label"), f"Version dashboard blocker missed action_label: {blocker}")
        _assert(blocker.get("action_target_type"), f"Version dashboard blocker missed action_target_type: {blocker}")
        _assert(blocker.get("action_target_id"), f"Version dashboard blocker missed action_target_id: {blocker}")
        _assert(blocker.get("resolution_hint"), f"Version dashboard blocker missed resolution_hint: {blocker}")


def validate_runner_token_rotation(
    client: ApiClient,
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
    return (
        new_runner_headers,
        StepResult("runner_token_rotation", f"token_version={rotated.get('token_version')}"),
    )


def validate_ai_executor_runner_reliability(
    client: ApiClient,
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
    runner_headers = {"X-Runner-Token": runner_token}
    client.post(
        f"/api/system/ai-executor-runners/{runner['id']}/heartbeat",
        {"metadata": {"source": "full_chain_regression"}},
        headers=runner_headers,
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
        token_rotation_result,
        StepResult("runner_reliability", f"{task_id} / requeued=1 / dead_letter=1"),
    ]


def _git(args: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> None:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    subprocess.run(["git", *args], cwd=cwd, env=merged_env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def create_fixture_repository(slug: str, branch: str) -> Path:
    repo_path = FIXTURE_ROOT / slug / "source-repo"
    if repo_path.exists():
        raise RegressionError(f"Fixture repository already exists: {repo_path}")
    repo_path.mkdir(parents=True)
    _git(["init", "-b", "main"], repo_path)
    _git(["config", "user.email", "full-chain@example.com"], repo_path)
    _git(["config", "user.name", "AI Brain Full Chain"], repo_path)
    (repo_path / "README.md").write_text("# AI Brain full-chain regression fixture\n", encoding="utf-8")
    _git(["add", "README.md"], repo_path)
    _git(["commit", "-m", "Initial full-chain fixture"], repo_path)
    _git(["checkout", "-b", branch], repo_path)
    source_dir = repo_path / "src"
    source_dir.mkdir()
    (source_dir / "settings.py").write_text(
        'API_KEY = "sk-full-chain-regression-secret"\n'
        'ADMIN_URL = "http://127.0.0.1:8080/admin"\n',
        encoding="utf-8",
    )
    _git(["add", "src/settings.py"], repo_path)
    _git(
        ["commit", "-m", "Add scan findings"],
        repo_path,
        env={
            "GIT_AUTHOR_EMAIL": "full-chain@example.com",
            "GIT_AUTHOR_NAME": "Full Chain Tester",
            "GIT_COMMITTER_EMAIL": "full-chain@example.com",
            "GIT_COMMITTER_NAME": "Full Chain Tester",
        },
    )
    return repo_path


def find_deposit_for_task(client: ApiClient, task_id: str) -> dict[str, Any] | None:
    deposits = client.get(
        "/api/knowledge/deposits",
        {"page": 1, "page_size": 20, "sort_by": "created_at", "sort_order": "desc", "status": "pending"},
    )
    for deposit in deposits.get("items", []):
        if deposit.get("ai_task_id") == task_id:
            return deposit
    return None


def validate_assistant_draft_governance(
    client: ApiClient,
    *,
    username: str,
    password: str,
) -> list[StepResult]:
    slug = _slug()
    results: list[StepResult] = []
    user = client.login(username, password).get("user", {})
    results.append(StepResult("login", f"logged in as {user.get('username') or username}"))

    draft = client.post(
        "/api/assistant/action-drafts",
        {
            "action": "create_scheduled_job",
            "client_draft_id": f"full_chain_assistant_draft_{slug}",
            "metadata_json": {
                "risk_reason": "full-chain regression validates action governance",
                "wizard_steps": [{"key": "basic"}, {"key": "governance"}],
            },
            "payload": {
                "enabled": False,
                "execution_mode": "deterministic",
                "job_type": "dashboard_snapshot_refresh",
                "name": f"全链路草案治理回归 {slug}",
                "schedule_type": "manual",
                "source_system": "ai-assistant",
            },
            "risk_level": "medium",
            "title": f"全链路草案治理回归 {slug}",
        },
    )
    _assert(draft.get("status") == "pending", f"Assistant draft was not pending: {draft}")
    _assert(draft.get("risk_level") == "medium", f"Assistant draft risk was not persisted: {draft}")
    governance = draft.get("governance") or {}
    impact = governance.get("impact") or {}
    permissions = governance.get("permissions") or {}
    diff = governance.get("diff") or {}
    audit = governance.get("audit") or {}
    _assert(
        permissions.get("status") == "passed",
        f"Assistant draft permission_status was not passed: {governance}",
    )
    _assert(
        impact.get("resource_type") == "scheduled_job",
        f"Assistant draft impact resource type was unexpected: {governance}",
    )
    _assert(
        int(impact.get("changed_field_count") or 0) >= 5,
        f"Assistant draft impact_changed_field_count was too small: {governance}",
    )
    _assert(
        int(diff.get("count") or 0) == int(impact.get("changed_field_count") or 0),
        f"Assistant draft diff count and impact count diverged: {governance}",
    )
    _assert(
        audit.get("latest_event_type") == "assistant_action_draft.created",
        f"Assistant draft latest_audit_event_type did not track creation: {governance}",
    )

    viewed = client.post(
        f"/api/assistant/action-drafts/{draft['id']}/view",
        {"surface": "full_chain_regression"},
    )
    _assert(
        int((viewed.get("metadata_json") or {}).get("view_count") or 0) >= 1,
        f"Assistant draft view was not tracked: {viewed}",
    )

    modified = client.post(
        f"/api/assistant/action-drafts/{draft['id']}/modification",
        {"modified_fields": ["name"], "user_modified": True},
    )
    modified_metadata = modified.get("metadata_json") or {}
    _assert(
        modified_metadata.get("user_modified") is True,
        f"Assistant draft modification marker was not tracked: {modified}",
    )

    patched_payload = dict(draft.get("payload") or {})
    patched_payload["name"] = f"{patched_payload['name']} patched"
    patched = client.request(
        "PATCH",
        f"/api/assistant/action-drafts/{draft['id']}",
        body={
            "modified_fields": ["name"],
            "payload": patched_payload,
            "user_modified": True,
        },
    )
    metadata = patched.get("metadata_json") or {}
    _assert(metadata.get("user_modified") is True, f"Assistant draft modification was not tracked: {patched}")
    _assert("name" in set(metadata.get("modified_fields") or []), f"Assistant draft modified field missing: {patched}")

    confirmed = client.post(f"/api/assistant/action-drafts/{draft['id']}/confirm")
    confirmed_draft = confirmed.get("draft") or {}
    run = confirmed.get("run") or {}
    _assert(
        confirmed_draft.get("status") == "confirmed",
        f"Assistant draft was not confirmed: {confirmed}",
    )
    _assert(run.get("status") == "succeeded", f"Assistant draft run failed: {confirmed}")
    _assert(
        run.get("result_type") == "scheduled_job",
        f"Assistant draft did not create scheduled job: {confirmed}",
    )
    result = run.get("result") or {}
    _assert(result.get("enabled") is False, f"Assistant draft created an enabled job unexpectedly: {result}")

    detail = client.get(f"/api/assistant/action-drafts/{draft['id']}")
    detail_governance = detail.get("governance") or {}
    detail_audit = detail_governance.get("audit") or {}
    _assert(
        detail_audit.get("latest_event_type") == "assistant_action_draft.confirmed",
        f"Assistant draft latest audit did not track confirmation: {detail_governance}",
    )
    _assert(
        "assistant_action_draft.confirmed" in set(detail_audit.get("event_types") or []),
        f"Assistant draft audit event types missed confirmation: {detail_governance}",
    )

    draft_list = client.get(
        "/api/assistant/action-drafts",
        {"page": 1, "page_size": 10, "status": "confirmed", "sort_by": "updated_at", "sort_order": "desc"},
    )
    matching_items = [
        item
        for item in draft_list.get("items", [])
        if item.get("id") == draft["id"]
    ]
    _assert(matching_items, f"Assistant draft list missed confirmed draft: {draft_list}")
    list_item = matching_items[0]
    _assert(
        list_item.get("permission_status") == "passed",
        f"Assistant draft list missed permission_status: {list_item}",
    )
    _assert(
        int(list_item.get("impact_changed_field_count") or 0) >= 5,
        f"Assistant draft list missed impact_changed_field_count: {list_item}",
    )
    _assert(
        list_item.get("latest_audit_event_type") == "assistant_action_draft.confirmed",
        f"Assistant draft list missed latest_audit_event_type: {list_item}",
    )

    audit_events = client.get(
        "/api/audit/events",
        {
            "page": 1,
            "page_size": 20,
            "subject_id": draft["id"],
            "subject_type": "assistant_action_draft",
        },
    )
    audit_event_types = {item.get("event_type") for item in audit_events.get("items", [])}
    for expected_event in [
        "assistant_action_draft.created",
        "assistant_action_draft.viewed",
        "assistant_action_draft.modified",
        "assistant_action_draft.updated",
        "assistant_action_draft.confirmed",
    ]:
        _assert(
            expected_event in audit_event_types,
            f"Assistant draft audit trail missed {expected_event}: {audit_events}",
        )

    results.append(
        StepResult(
            "assistant_draft_governance",
            f"{draft['id']} / {run.get('result_type')}={run.get('result_id')}",
        )
    )
    return results


def validate_version_dashboard_quick_regression(
    client: ApiClient,
    *,
    username: str,
    password: str,
) -> list[StepResult]:
    slug = _slug()
    version_branch = f"dashboard/{slug}"
    repo_path = create_fixture_repository(slug, version_branch)
    results: list[StepResult] = []

    user = client.login(username, password).get("user", {})
    results.append(StepResult("login", f"logged in as {user.get('username') or username}"))

    product = client.post(
        "/api/products",
        {
            "code": f"dashboard-{slug}",
            "description": "自动版本总览快速回归脚本创建的产品数据。",
            "name": f"版本总览快速回归产品 {slug}",
            "status": "active",
        },
    )
    version = client.post(
        f"/api/products/{product['id']}/versions",
        {
            "code": f"dashboard-{slug}",
            "description": "自动版本总览快速回归版本。",
            "name": f"版本总览快速回归版本 {slug}",
            "status": "active",
        },
    )
    results.append(StepResult("version_dashboard_product", f"{product['id']} / {version['id']}"))

    requirement = client.post(
        "/api/requirements",
        {
            "content": "版本总览快速回归验证需求、任务、分支和发布阻塞项聚合。",
            "priority": "P0",
            "product_id": product["id"],
            "source": "product_planning",
            "title": f"版本总览快速回归需求 {slug}",
            "version_id": version["id"],
        },
    )
    approved = client.post(
        f"/api/requirements/{requirement['id']}/approve",
        {"comment": "版本总览快速回归审批通过"},
    )
    _assert(
        approved["status"] in {"approved", "planned"},
        f"Version dashboard requirement was not approved: {approved}",
    )
    task = client.post(f"/api/requirements/{requirement['id']}/generate-task")
    task_id = str(task["task_id"])
    results.append(
        StepResult("version_dashboard_requirement", f"{requirement['id']} / task={task_id}")
    )

    design_started = client.post(
        f"/api/ai-tasks/{task_id}/start",
        {
            "execution_mode": "deterministic",
            "reason": "version dashboard quick regression prepares code review context",
        },
    )
    _assert(
        design_started.get("status") == "waiting_review",
        f"Version dashboard design task did not enter review: {design_started}",
    )
    design_approved = client.post(
        f"/api/reviews/{design_started['review_id']}/approve",
        {"version": 1},
    )
    _assert(
        design_approved.get("task_status") == "completed",
        f"Version dashboard design task was not completed: {design_approved}",
    )
    technical_solution = client.post(
        "/api/ai-tasks",
        {
            "input": {"product_detail_design_task_id": task_id},
            "requirement_id": requirement["id"],
            "task_type": "technical_solution",
            "title": f"技术方案：版本总览快速回归 {slug}",
        },
    )
    results.append(
        StepResult("version_dashboard_solution", str(technical_solution["id"]))
    )
    solution_started = client.post(
        f"/api/ai-tasks/{technical_solution['id']}/start",
        {
            "execution_mode": "deterministic",
            "reason": "version dashboard quick regression prepares code review context",
        },
    )
    _assert(
        solution_started.get("status") == "waiting_review",
        f"Version dashboard solution task did not enter review: {solution_started}",
    )
    solution_approved = client.post(
        f"/api/reviews/{solution_started['review_id']}/approve",
        {"version": 1},
    )
    _assert(
        solution_approved.get("task_status") == "completed",
        f"Version dashboard solution task was not completed: {solution_approved}",
    )

    repository = client.post(
        f"/api/products/{product['id']}/git-repositories",
        {
            "credential_ref": f"fixture-token-{slug}",
            "default_branch": "main",
            "git_provider": "gitlab",
            "name": f"版本总览快速回归仓库 {slug}",
            "project_path": f"dashboard/{slug}",
            "remote_url": "fixture://gitlab",
            "repo_type": "code",
            "root_path": "/",
            "status": "active",
        },
    )
    branch_config = client.post(
        f"/api/product-versions/{version['id']}/branch-configs",
        {
            "base_branch": "main",
            "branch_status": "active",
            "creation_source": "manual",
            "description": "版本总览快速回归分支，保持 active 以验证发布前分支阻塞。",
            "repository_id": repository["id"],
            "working_branch": version_branch,
        },
    )
    snapshot = client.post(
        f"/api/devops/gitlab/merge-requests/{repository['id']}/7/snapshot",
        {
            "requirement_id": requirement["id"],
            "technical_solution_task_id": technical_solution["id"],
        },
    )
    results.append(
        StepResult("version_dashboard_branch", f"{branch_config['id']} / {version_branch}")
    )
    code_review_task = client.post(
        "/api/ai-tasks",
        {
            "input": {"gitlab_mr_snapshot_id": snapshot["id"]},
            "requirement_id": requirement["id"],
            "task_type": "code_review",
            "title": f"Code Review：版本总览快速回归 {slug}",
        },
    )
    code_review_started = client.post(
        f"/api/ai-tasks/{code_review_task['id']}/start",
        {
            "execution_mode": "deterministic",
            "reason": "version dashboard quick regression validates code review aggregation",
        },
    )
    _assert(
        code_review_started.get("status") == "waiting_review",
        f"Version dashboard code review task did not enter review: {code_review_started}",
    )
    code_review_report = client.get(
        f"/api/ai-tasks/{code_review_task['id']}/code-review-report"
    )
    results.append(
        StepResult(
            "version_dashboard_code_review",
            f"{code_review_task['id']} / report={code_review_report['id']}",
        )
    )

    version_testing = client.post(
        f"/api/product-versions/{version['id']}/advance-status",
        {
            "force": True,
            "reason": "version dashboard quick regression checks release blockers",
            "target_status": "testing",
        },
    )
    _assert(
        version_testing.get("version", {}).get("status") == "testing",
        f"Version dashboard fixture did not advance to testing: {version_testing}",
    )

    dashboard = client.get(f"/api/product-versions/{version['id']}/dashboard")
    _assert(
        dashboard["summary"]["requirements"] >= 1,
        "Version dashboard quick check missed requirement summary.",
    )
    _assert(
        dashboard["summary"]["tasks"] >= 1,
        "Version dashboard quick check missed task summary.",
    )
    _assert(
        dashboard["summary"]["branch_configs"] >= 1,
        "Version dashboard quick check missed branch summary.",
    )
    _assert(
        dashboard["summary"].get("code_review_reports", 0) >= 1,
        "Version dashboard quick check missed code review report summary.",
    )
    _assert(
        dashboard["summary"].get("pending_code_review_reports", 0) >= 1,
        "Version dashboard quick check missed pending code review report summary.",
    )
    _assert_contains(
        _ids(dashboard.get("requirements", [])),
        requirement["id"],
        "Version dashboard quick check missed requirement row",
    )
    _assert_contains(
        _ids(dashboard.get("tasks", [])),
        task_id,
        "Version dashboard quick check missed task row",
    )
    _assert_contains(
        _ids(dashboard.get("branch_configs", [])),
        branch_config["id"],
        "Version dashboard quick check missed branch row",
    )
    _assert_contains(
        _ids(dashboard.get("code_review_reports", [])),
        code_review_report["id"],
        "Version dashboard quick check missed code review report row",
    )
    status_impact = dashboard.get("status_impact") or {}
    _assert(
        status_impact.get("target_status") == "released",
        f"Version dashboard quick check did not preview release impact: {status_impact}",
    )
    dashboard_blockers = dashboard.get("blockers", [])
    _assert(
        dashboard["summary"]["blockers"] >= 1,
        "Version dashboard quick check did not expose blockers.",
    )
    validate_version_dashboard_blocker_actions(dashboard_blockers)
    release_evidence_blockers = [
        blocker
        for blocker in dashboard_blockers
        if blocker.get("source_type") == "jenkins_release"
        and blocker.get("action_target_type") == "product_version"
        and str(blocker.get("action_target_id")) == version["id"]
    ]
    _assert(
        release_evidence_blockers,
        f"Version dashboard quick check missed release evidence blocker: {dashboard_blockers}",
    )
    branch_blockers = [
        blocker
        for blocker in dashboard_blockers
        if blocker.get("source_type") == "product_version_branch_config"
        and str(blocker.get("action_target_id")) == branch_config["id"]
    ]
    _assert(
        branch_blockers,
        f"Version dashboard quick check missed branch blocker: {dashboard_blockers}",
    )
    results.append(
        StepResult(
            "version_dashboard_quick",
            f"blockers={dashboard['summary']['blockers']}, tasks={dashboard['summary']['tasks']}",
        )
    )
    results.append(StepResult("fixture_repository", str(repo_path)))
    return results


def run_regression(
    client: ApiClient,
    *,
    task_execution_mode: str,
    username: str,
    password: str,
) -> list[StepResult]:
    results: list[StepResult] = []
    slug = _slug()
    version_branch = f"release/{slug}"
    repo_path = create_fixture_repository(slug, version_branch)

    user = client.login(username, password).get("user", {})
    results.append(StepResult("login", f"logged in as {user.get('username') or username}"))

    product = client.post(
        "/api/products",
        {
            "code": slug,
            "description": "自动全链路回归脚本创建的产品数据。",
            "name": f"全链路回归产品 {slug}",
            "status": "active",
        },
    )
    results.append(StepResult("product", f"{product['id']} / {product['code']}"))

    module = client.post(
        f"/api/products/{product['id']}/modules",
        {"code": "core", "name": "核心链路", "status": "active"},
    )
    version = client.post(
        f"/api/products/{product['id']}/versions",
        {
            "code": f"v-{slug}",
            "description": "自动全链路回归版本。",
            "name": f"全链路回归版本 {slug}",
            "status": "active",
        },
    )
    results.append(StepResult("version", f"{version['id']} / {version['code']}"))

    feedback = client.post(
        "/api/insights/user-feedback",
        {
            "content": "用户反馈希望将关键建议快速转成需求，并能一路追踪到版本、任务、代码巡检和知识沉淀。",
            "feedback_type": "improvement",
            "feature_code": "full-chain",
            "module_code": module["code"],
            "product_id": product["id"],
            "satisfaction_score": 3,
            "sentiment": "neutral",
            "source_channel": "regression_script",
            "tags": ["full-chain", "regression"],
        },
    )
    converted = client.post(
        f"/api/insights/user-feedback/{feedback['id']}/convert-requirement",
        {
            "priority": "P0",
            "title": f"全链路回归需求 {slug}",
            "triage_note": "回归脚本确认该反馈可进入产品需求池。",
        },
    )
    requirement = converted["requirement"]
    _assert(converted["feedback"]["status"] == "linked", "Feedback was not linked after conversion.")
    results.append(StepResult("feedback_to_requirement", f"{feedback['id']} -> {requirement['id']}"))

    approved = client.post(f"/api/requirements/{requirement['id']}/approve", {"comment": "全链路回归审批通过"})
    _assert(approved["status"] == "approved", "Requirement was not approved.")
    schedule = client.post(
        "/api/requirements/batch-schedule",
        {
            "product_id": product["id"],
            "reason": "归入自动回归版本。",
            "requirement_ids": [requirement["id"]],
            "version_id": version["id"],
        },
    )
    _assert(schedule.get("updated_count") == 1, f"Requirement schedule did not update exactly one item: {schedule}")
    results.append(StepResult("requirement_schedule", f"{requirement['id']} -> {version['id']}"))

    task = client.post(f"/api/requirements/{requirement['id']}/generate-task")
    task_id = task["task_id"]
    started = client.post(
        f"/api/ai-tasks/{task_id}/start",
        {
            "execution_mode": task_execution_mode,
            "reason": "full-chain regression",
        },
    )
    _assert(started.get("status") == "waiting_review", f"AI task did not enter waiting_review: {started}")
    approved_review = client.post(f"/api/reviews/{started['review_id']}/approve", {"version": 1})
    _assert(approved_review.get("task_status") == "completed", f"Review did not complete task: {approved_review}")
    results.append(
        StepResult(
            "ai_task_review",
            f"{task_id} / review {started['review_id']} / mode={task_execution_mode}",
        )
    )

    deposit = find_deposit_for_task(client, task_id)
    _assert(deposit is not None, f"No pending knowledge deposit found for task {task_id}.")
    approved_deposit = client.post(
        f"/api/knowledge/deposits/{deposit['id']}/approve",
        {"permission_roles": ["admin", "product_owner", "rd_owner"], "title": f"全链路回归知识沉淀 {slug}"},
    )
    _assert(approved_deposit.get("status") == "approved", f"Knowledge deposit was not approved: {approved_deposit}")
    knowledge_document_id = str(approved_deposit.get("knowledge_document_id") or "")
    _assert(knowledge_document_id, f"Knowledge deposit did not return a knowledge_document_id: {approved_deposit}")
    results.append(
        StepResult(
            "knowledge_deposit",
            f"{deposit['id']} -> {knowledge_document_id}",
        )
    )

    knowledge_health = client.get(
        "/api/knowledge/index-health",
        {"issue_limit": 20, "keyword": slug, "permission_role": "admin"},
    )
    knowledge_health_summary = knowledge_health.get("summary") or {}
    _assert(
        int(knowledge_health_summary.get("total_documents") or 0) >= 1,
        f"Knowledge index health missed the approved deposit document: {knowledge_health}",
    )
    _assert(
        int(knowledge_health_summary.get("searchable_documents") or 0) >= 1,
        f"Knowledge index health did not mark the deposit document searchable: {knowledge_health_summary}",
    )
    _assert(
        int(knowledge_health_summary.get("total_chunks") or 0) >= 1,
        f"Knowledge index health did not report chunks for the deposit document: {knowledge_health_summary}",
    )
    retrieval_modes = knowledge_health.get("retrieval_modes") or {}
    _assert(
        int(retrieval_modes.get("hybrid_ready") or 0) + int(retrieval_modes.get("keyword_fallback") or 0) >= 1,
        f"Knowledge index health did not expose a usable retrieval mode: {retrieval_modes}",
    )
    knowledge_search = client.post("/api/knowledge/search", {"query": slug, "top_k": 5})
    search_items = knowledge_search.get("items", [])
    search_document_ids = {str(item.get("document_id")) for item in search_items}
    _assert_contains(
        search_document_ids,
        knowledge_document_id,
        "Knowledge search did not retrieve the approved deposit document",
    )
    _assert(
        any(item.get("retrieval_mode") in {"keyword", "vector"} for item in search_items),
        f"Knowledge search did not return a retrieval mode: {search_items}",
    )
    results.append(
        StepResult(
            "knowledge_index_health",
            f"{knowledge_document_id} / chunks={knowledge_health_summary.get('total_chunks')}",
        )
    )

    repository = client.post(
        f"/api/products/{product['id']}/git-repositories",
        {
            "default_branch": "main",
            "git_provider": "github",
            "name": f"全链路本地扫描仓库 {slug}",
            "project_path": f"local/{slug}",
            "remote_url": str(repo_path),
            "repo_type": "code",
            "root_path": "/",
            "status": "active",
        },
    )
    branch_config = client.post(
        f"/api/product-versions/{version['id']}/branch-configs",
        {
            "base_branch": "main",
            "branch_status": "active",
            "creation_source": "manual",
            "description": "全链路回归版本分支。",
            "repository_id": repository["id"],
            "working_branch": version_branch,
        },
    )
    results.append(StepResult("version_branch", f"{branch_config['id']} / {version_branch}"))

    scan_job = client.post(
        "/api/system/scheduled-jobs",
        {
            "config_json": {
                "async_execution": False,
                "branch": version_branch,
                "quality_gate": {
                    "critical_max": 0,
                    "enabled": True,
                    "high_max": 0,
                    "medium_max": 0,
                },
                "repository_id": repository["id"],
                "scan_mode": "native_full_scan",
                "scan_rules": ["secrets", "internal_addresses"],
            },
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": f"全链路代码巡检 {slug}",
            "product_id": product["id"],
            "result_actions": [
                {"type": "write_code_inspection_report"},
                {"severity_threshold": "critical", "type": "create_bug_for_severe_findings"},
                {"severity_threshold": "high", "type": "create_task_for_severe_findings"},
            ],
            "schedule_type": "manual",
            "source_system": "native-code-scanner",
        },
    )
    scan_run = client.post(f"/api/system/scheduled-jobs/{scan_job['id']}/run")
    _assert(scan_run.get("status") == "succeeded", f"Code inspection run failed: {scan_run}")
    scan_run_summary = scan_run.get("result_summary", {})
    native_scan_node = (scan_run_summary.get("execution_nodes") or {}).get("native_scan") or {}
    native_quality_gate = native_scan_node.get("quality_gate") or {}
    _assert(
        native_quality_gate.get("status") == "failed",
        f"Native scan did not fail the configured quality gate: {native_quality_gate}",
    )
    _assert(
        native_quality_gate.get("violations"),
        f"Native scan quality gate did not include violation details: {native_quality_gate}",
    )
    report_id = scan_run_summary.get("report_id")
    _assert(bool(report_id), f"Code inspection run did not return report_id: {scan_run}")
    report_detail = client.get(f"/api/governance/code-inspections/{report_id}")
    report = report_detail["report"]
    findings = report_detail.get("findings", [])
    scan_summary = report_detail.get("scan_summary", {})
    governance_summary = report_detail.get("governance_summary", {})
    report_quality_gate = report.get("quality_gate") or {}
    scan_summary_quality_gate = scan_summary.get("quality_gate") or {}
    _assert(report["scan_mode"] == "native_full_scan", "Report is not native_full_scan.")
    _assert(report["branch"] == version_branch, "Report branch does not match version branch.")
    _assert(report["repository_id"] == repository["id"], "Report repository does not match version repository.")
    _assert(
        report_quality_gate.get("status") == "failed",
        f"Report did not persist failed quality gate status: {report_quality_gate}",
    )
    _assert(
        scan_summary_quality_gate.get("status") == "failed",
        f"Detail scan summary did not expose failed quality gate status: {scan_summary_quality_gate}",
    )
    _assert(len(findings) >= 2, f"Native scan did not return expected findings: {findings}")
    _assert(
        any(finding.get("rule_id") == "secrets.hardcoded_credential" for finding in findings),
        "Native scan did not detect the hardcoded credential finding.",
    )
    _assert(
        any(finding.get("rule_id") == "metadata.internal_address_exposure" for finding in findings),
        "Native scan did not detect the internal address finding.",
    )
    coverage = scan_summary.get("coverage") or {}
    _assert(int(coverage.get("files_scanned") or 0) >= 2, f"Scan coverage is incomplete: {coverage}")
    _assert(
        any(item.get("email") == "full-chain@example.com" for item in scan_summary.get("committer_distribution", [])),
        f"Scan did not preserve committer attribution: {scan_summary.get('committer_distribution')}",
    )
    _assert(
        int(governance_summary.get("covered_by_bug_count") or 0) >= 1,
        f"Governance summary did not count Bug coverage: {governance_summary}",
    )
    _assert(
        int(governance_summary.get("covered_by_task_count") or 0) >= 1,
        f"Governance summary did not count remediation task coverage: {governance_summary}",
    )
    inspection_dashboard = client.get(
        "/api/governance/code-inspections/dashboard",
        {"product_id": product["id"], "repository_id": repository["id"]},
    )
    _assert(
        any(int(item.get("quality_gate_failed_count") or 0) >= 1 for item in inspection_dashboard.get("trend", [])),
        f"Code inspection dashboard trend missed quality gate failure: {inspection_dashboard.get('trend')}",
    )
    _assert(
        inspection_dashboard.get("quality_gate_violations"),
        f"Code inspection dashboard missed quality gate violation aggregation: {inspection_dashboard}",
    )
    governance_pressure = inspection_dashboard.get("governance_pressure") or {}
    _assert(
        governance_pressure,
        f"Code inspection dashboard missed governance pressure summary: {inspection_dashboard}",
    )
    _assert(
        governance_pressure.get("status") == "action_required",
        f"Code inspection governance pressure did not expose quality gate pressure: {governance_pressure}",
    )
    _assert(
        int(governance_pressure.get("quality_gate_failed_report_count") or 0) >= 1,
        f"Code inspection governance pressure missed failed report count: {governance_pressure}",
    )
    _assert(
        int(governance_pressure.get("quality_gate_violation_count") or 0) >= 1,
        f"Code inspection governance pressure missed violation count: {governance_pressure}",
    )
    _assert(
        int(governance_pressure.get("active_severe_finding_count") or 0) >= 1,
        f"Code inspection governance pressure missed active severe findings: {governance_pressure}",
    )
    _assert(
        int(governance_pressure.get("uncovered_bug_finding_count") or 0) == 0,
        f"Code inspection governance pressure did not close Bug coverage: {governance_pressure}",
    )
    _assert(
        int(governance_pressure.get("uncovered_task_finding_count") or 0) == 0,
        f"Code inspection governance pressure did not close remediation coverage: {governance_pressure}",
    )
    committer_governance = [
        item
        for item in inspection_dashboard.get("committer_governance", [])
        if item.get("email") == "full-chain@example.com"
    ]
    _assert(
        committer_governance,
        f"Code inspection dashboard missed committer governance queue: {inspection_dashboard}",
    )
    committer_governance_item = committer_governance[0]
    _assert(
        committer_governance_item.get("status") == "healthy",
        f"Code inspection committer governance did not close the loop: {committer_governance_item}",
    )
    _assert(
        int(committer_governance_item.get("active_severe_finding_count") or 0) >= 1,
        f"Code inspection committer governance missed active severe findings: {committer_governance_item}",
    )
    _assert(
        int(committer_governance_item.get("covered_by_bug_count") or 0) >= 1,
        f"Code inspection committer governance missed Bug coverage: {committer_governance_item}",
    )
    _assert(
        int(committer_governance_item.get("covered_by_task_count") or 0) >= 1,
        f"Code inspection committer governance missed remediation task coverage: {committer_governance_item}",
    )
    report_bug_ids = {str(item) for item in report.get("created_bug_ids") or []}
    report_task_ids = {str(item) for item in report.get("created_task_ids") or []}
    _assert(report_bug_ids, f"Code inspection report did not record created Bug ids: {report}")
    _assert(report_task_ids, f"Code inspection report did not record created remediation task ids: {report}")
    results.append(StepResult("code_inspection", f"{report_id} / findings={len(findings)} / {scan_run['id']}"))
    results.append(
        StepResult(
            "code_inspection_governance_pressure",
            (
                f"status={governance_pressure.get('status')}, "
                f"gate_failures={governance_pressure.get('quality_gate_failed_report_count')}, "
                f"uncovered_bug={governance_pressure.get('uncovered_bug_finding_count')}, "
                f"uncovered_task={governance_pressure.get('uncovered_task_finding_count')}"
            ),
        )
    )

    bugs = client.get("/api/bugs", {"product_id": product["id"], "source": "code_inspection"})
    bug_items = bugs.get("items", [])
    _assert(len(bug_items) >= 1, "Code inspection did not create a Bug.")
    bug_ids = _ids(bug_items)
    for bug_id in report_bug_ids:
        _assert_contains(bug_ids, bug_id, "Code inspection Bug writeback missing from Bug list")
    _assert(
        all(item.get("evidence", {}).get("code_inspection_report_id") == report_id for item in bug_items if item["id"] in report_bug_ids),
        "Code inspection Bug evidence did not point back to the report.",
    )
    remediation_tasks = client.get(
        "/api/ai-tasks",
        {"product_id": product["id"], "task_type": "code_inspection_remediation"},
    )
    remediation_items = remediation_tasks.get("items", [])
    _assert(len(remediation_items) >= 1, "Code inspection did not create a remediation task.")
    remediation_task_ids = _ids(remediation_items)
    for remediation_task_id in report_task_ids:
        _assert_contains(
            remediation_task_ids,
            remediation_task_id,
            "Code inspection remediation task writeback missing from AI task list",
        )
    results.append(
        StepResult(
            "inspection_writeback",
            f"bugs={len(report_bug_ids)}, tasks={len(report_task_ids)}",
        )
    )
    results.extend(
        validate_ai_executor_runner_reliability(
            client,
            repo_path=repo_path,
            slug=slug,
        )
    )

    version_testing = client.post(
        f"/api/product-versions/{version['id']}/advance-status",
        {
            "force": True,
            "reason": "full-chain regression checks release evidence blockers",
            "target_status": "testing",
        },
    )
    _assert(
        version_testing.get("version", {}).get("status") == "testing",
        f"Version did not advance to testing before release evidence check: {version_testing}",
    )
    results.append(StepResult("version_testing", f"{version['id']} -> testing"))

    dashboard = client.get(f"/api/product-versions/{version['id']}/dashboard")
    _assert(dashboard["summary"]["requirements"] >= 1, "Version dashboard missed requirement summary.")
    _assert(dashboard["summary"]["code_inspection_reports"] >= 1, "Version dashboard missed code inspection report.")
    _assert(dashboard["summary"]["branch_configs"] >= 1, "Version dashboard missed branch config.")
    _assert(dashboard["summary"].get("knowledge_deposits", 0) >= 1, "Version dashboard missed knowledge deposit summary.")
    _assert(
        dashboard["summary"].get("searchable_knowledge_deposits", 0) >= 1,
        "Version dashboard missed searchable knowledge deposit summary.",
    )
    _assert_contains(_ids(dashboard.get("branch_configs", [])), branch_config["id"], "Version dashboard missed branch config row")
    _assert_contains(
        _ids(dashboard.get("code_inspection_reports", [])),
        report_id,
        "Version dashboard missed code inspection report row",
    )
    _assert_contains(
        _ids(dashboard.get("knowledge_deposits", [])),
        deposit["id"],
        "Version dashboard missed knowledge deposit row",
    )
    dashboard_deposit = next(
        item
        for item in dashboard.get("knowledge_deposits", [])
        if item.get("id") == deposit["id"]
    )
    _assert(
        dashboard_deposit.get("knowledge_retrieval_mode") in {"hybrid", "keyword"},
        f"Version dashboard knowledge deposit was not searchable: {dashboard_deposit}",
    )
    _assert(
        int(dashboard_deposit.get("knowledge_chunk_count") or 0) >= 1,
        f"Version dashboard knowledge deposit missed chunk health: {dashboard_deposit}",
    )
    _assert(
        dashboard_deposit.get("knowledge_index_status")
        in {"indexed", "text_indexed", "vector_indexed"},
        f"Version dashboard knowledge deposit missed searchable index status: {dashboard_deposit}",
    )
    _assert(report_bug_ids.intersection(_ids(dashboard.get("bugs", []))), "Version dashboard missed code-inspection Bug row.")
    _assert(_status_count(dashboard.get("bug_status_counts", []), "open") >= 1, "Version dashboard missed open Bug count.")
    dashboard_blockers = dashboard.get("blockers", [])
    _assert(dashboard["summary"]["blockers"] >= 1, "Version dashboard did not expose blockers.")
    _assert(dashboard_blockers, "Version dashboard blocker list is empty.")
    validate_version_dashboard_blocker_actions(dashboard_blockers)
    inspection_blockers = [
        blocker
        for blocker in dashboard_blockers
        if blocker.get("source_type") == "code_inspection_report" and str(blocker.get("action_target_id")) == report_id
    ]
    _assert(inspection_blockers, "Version dashboard missed actionable code inspection blocker.")
    _assert(
        any("质量门禁" in str(blocker.get("reason") or "") for blocker in inspection_blockers),
        f"Version dashboard code inspection blocker did not mention quality gate: {inspection_blockers}",
    )
    bug_blockers = [
        blocker
        for blocker in dashboard_blockers
        if blocker.get("source_type") == "bug" and str(blocker.get("action_target_id")) in report_bug_ids
    ]
    _assert(bug_blockers, "Version dashboard missed actionable Bug blocker.")
    release_evidence_blockers = [
        blocker
        for blocker in dashboard_blockers
        if blocker.get("source_type") == "jenkins_release"
        and str(blocker.get("action_target_id")) == version["id"]
        and blocker.get("action_target_type") == "product_version"
    ]
    _assert(
        release_evidence_blockers,
        f"Version dashboard missed release evidence blocker for product version: {dashboard_blockers}",
    )
    _assert(
        any("缺少成功发布记录" in str(blocker.get("reason") or "") for blocker in release_evidence_blockers),
        f"Version dashboard release blocker did not explain missing successful release: {release_evidence_blockers}",
    )
    results.append(
        StepResult(
            "version_dashboard",
            f"blockers={dashboard['summary']['blockers']}, blocker_actions={len(dashboard_blockers)}",
        )
    )

    full_chain = client.get(
        "/api/lifecycle/full-chain",
        {"subject_id": version["id"], "subject_type": "product_version"},
    )
    _assert(full_chain["requirement"]["id"] == requirement["id"], "Full-chain did not resolve to requirement.")
    report_ids = {item["id"] for item in full_chain.get("code_inspection_reports", [])}
    _assert(report_id in report_ids, "Full-chain did not include code inspection report.")
    _assert_contains(_ids(full_chain.get("branch_configs", [])), branch_config["id"], "Full-chain missed version branch config")
    _assert_contains(
        _ids(full_chain.get("knowledge_deposits", [])),
        deposit["id"],
        "Full-chain missed approved knowledge deposit",
    )
    _assert(full_chain.get("anchor", {}).get("subject_id") == version["id"], "Full-chain anchor did not preserve version entry.")
    timeline_types = {item.get("type") for item in full_chain.get("timeline", [])}
    for expected_type in {"requirement", "ai_task", "review", "knowledge_deposit", "branch_config", "code_inspection_report"}:
        _assert(expected_type in timeline_types, f"Full-chain timeline missed {expected_type}: {timeline_types}")
    report_full_chain = client.get(
        "/api/lifecycle/full-chain",
        {"subject_id": report_id, "subject_type": "code_inspection_report"},
    )
    _assert(
        report_full_chain["requirement"]["id"] == requirement["id"],
        "Code inspection report subject did not resolve back to the requirement full-chain.",
    )
    results.append(StepResult("full_chain", f"timeline={len(full_chain.get('timeline', []))}"))

    team_dashboard = client.get("/api/dashboard/it-team", {"product_id": product["id"], "refresh": "true", "time_range": "all"})
    dashboard_summary = team_dashboard.get("summary") or {}
    _assert(int(dashboard_summary.get("requirements") or 0) >= 1, f"IT team dashboard missed requirements: {dashboard_summary}")
    _assert(int(dashboard_summary.get("ai_tasks") or 0) >= 2, f"IT team dashboard missed AI tasks: {dashboard_summary}")
    _assert(int(dashboard_summary.get("bugs") or 0) >= 1, f"IT team dashboard missed Bugs: {dashboard_summary}")
    _assert(
        int(dashboard_summary.get("knowledge_documents") or 0) >= 1,
        f"IT team dashboard missed knowledge documents: {dashboard_summary}",
    )
    _assert(_status_count(team_dashboard.get("user_feedback_status_counts", []), "linked") >= 1, "Dashboard missed linked feedback count.")
    _assert(_status_count(team_dashboard.get("bug_status_counts", []), "open") >= 1, "Dashboard missed open Bug count.")
    _assert_contains(_ids(team_dashboard.get("latest_tasks", [])), task_id, "Dashboard missed completed AI task")
    for remediation_task_id in report_task_ids:
        _assert_contains(_ids(team_dashboard.get("latest_tasks", [])), remediation_task_id, "Dashboard missed remediation task")
    for bug_id in report_bug_ids:
        _assert_contains(_ids(team_dashboard.get("latest_high_severity_bugs", [])), bug_id, "Dashboard missed severe Bug")
    _assert_contains(
        _ids(team_dashboard.get("recent_knowledge_documents", [])),
        knowledge_document_id,
        "Dashboard missed approved knowledge document",
    )
    results.append(StepResult("team_dashboard", f"keys={','.join(sorted(team_dashboard.keys())[:6])}"))

    assistant = client.post(
        "/api/assistant/chat",
        {
            "client_request_id": f"full-chain-regression-{slug}",
            "message": f"请基于产品 {product['name']} 的这次全链路回归引用，帮我新建一个后续跟进任务向导。",
            "product_id": product["id"],
            "references": [
                {"id": requirement["id"], "type": "requirement"},
                {"id": version["id"], "type": "product_version"},
                {"id": report_id, "type": "code_inspection_report"},
            ],
        },
    )
    assistant_message = assistant.get("message", {})
    assistant_message_id = assistant_message.get("id")
    _assert(assistant_message_id, f"Assistant chat response missing message: {assistant}")
    assistant_reference_keys = {
        (reference.get("type"), reference.get("id")) for reference in assistant_message.get("references", [])
    }
    for expected_reference in [
        ("requirement", requirement["id"]),
        ("product_version", version["id"]),
        ("code_inspection_report", report_id),
    ]:
        _assert(
            expected_reference in assistant_reference_keys,
            f"Assistant response missed reference {expected_reference}: {assistant_message.get('references')}",
        )
    conversation_id = assistant.get("conversation_id") or assistant.get("run", {}).get("conversation_id")
    _assert(conversation_id, f"Assistant response missing conversation_id: {assistant}")
    conversation_messages = client.get(f"/api/assistant/conversations/{conversation_id}/messages")
    message_items = conversation_messages.get("items", [])
    _assert(len(message_items) >= 2, f"Assistant conversation history was not persisted: {conversation_messages}")
    persisted_assistant_messages = [item for item in message_items if item.get("id") == assistant_message_id]
    _assert(persisted_assistant_messages, f"Assistant message {assistant_message_id} was not found in conversation history.")
    persisted_reference_keys = {
        (reference.get("type"), reference.get("id"))
        for reference in persisted_assistant_messages[0].get("references", [])
    }
    _assert(
        ("code_inspection_report", report_id) in persisted_reference_keys,
        f"Persisted assistant message missed code inspection reference: {persisted_assistant_messages[0]}",
    )
    _assert(
        persisted_assistant_messages[0].get("tool_results"),
        f"Persisted assistant message missed tool results: {persisted_assistant_messages[0]}",
    )
    results.append(StepResult("assistant_qa", f"{assistant_message_id} / conversation={conversation_id}"))

    results.append(StepResult("fixture_repository", str(repo_path)))
    return results


def run_regression_suite(
    client: ApiClient,
    *,
    suite: str,
    task_execution_mode: str,
    username: str,
    password: str,
) -> list[StepResult]:
    results = [StepResult("suite", suite)]
    if suite == "full":
        results.extend(
            run_regression(
                client,
                task_execution_mode=task_execution_mode,
                username=username,
                password=password,
            )
        )
        return results
    if suite == "runner-reliability":
        slug = _slug()
        repo_path = create_fixture_repository(slug, f"runner/{slug}")
        user = client.login(username, password).get("user", {})
        results.append(StepResult("login", f"logged in as {user.get('username') or username}"))
        results.extend(
            validate_ai_executor_runner_reliability(
                client,
                repo_path=repo_path,
                slug=slug,
            )
        )
        results.append(StepResult("fixture_repository", str(repo_path)))
        return results
    if suite == "version-dashboard":
        results.extend(
            validate_version_dashboard_quick_regression(
                client,
                username=username,
                password=password,
            )
        )
        return results
    if suite == "assistant-draft-governance":
        results.extend(
            validate_assistant_draft_governance(
                client,
                username=username,
                password=password,
            )
        )
        return results
    raise RegressionError(f"Unsupported regression suite: {suite}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a real AI Brain full-chain regression through public APIs.",
    )
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("FULL_CHAIN_API_BASE_URL", os.getenv("READINESS_API_BASE_URL", DEFAULT_API_BASE_URL)),
        help="API base URL. Defaults to FULL_CHAIN_API_BASE_URL, READINESS_API_BASE_URL, or http://localhost:8000.",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("FULL_CHAIN_PASSWORD", os.getenv("READINESS_PASSWORD", "admin123")),
        help="Login password. Defaults to FULL_CHAIN_PASSWORD, READINESS_PASSWORD, or admin123.",
    )
    parser.add_argument(
        "--timeout",
        default=90.0,
        type=float,
        help="HTTP timeout in seconds per request.",
    )
    parser.add_argument(
        "--task-execution-mode",
        choices=["deterministic", "model_gateway"],
        default=os.getenv("FULL_CHAIN_TASK_EXECUTION_MODE", "deterministic"),
        help=(
            "AI task execution mode. deterministic keeps the full-chain check stable without "
            "calling an external model gateway; model_gateway validates the live Chat gateway."
        ),
    )
    parser.add_argument(
        "--suite",
        choices=["full", "runner-reliability", "version-dashboard", "assistant-draft-governance"],
        default=os.getenv("FULL_CHAIN_SUITE", "full"),
        help=(
            "Regression suite to run. full executes the end-to-end product workflow; "
            "runner-reliability executes only the AI executor Runner lease/dead-letter gate; "
            "version-dashboard executes a quick product version dashboard aggregation "
            "and blocker gate; assistant-draft-governance executes the AI action draft "
            "governance/audit gate."
        ),
    )
    parser.add_argument(
        "--json-output",
        default=os.getenv("FULL_CHAIN_JSON_OUTPUT"),
        help=(
            "Optional path for a machine-readable regression report. The script writes "
            "the report on both pass and fail so CI can preserve run evidence."
        ),
    )
    parser.add_argument(
        "--username",
        default=os.getenv("FULL_CHAIN_USERNAME", os.getenv("READINESS_USERNAME", "admin@example.com")),
        help="Login username. Defaults to FULL_CHAIN_USERNAME, READINESS_USERNAME, or admin@example.com.",
    )
    args = parser.parse_args()

    client = ApiClient(args.api_base_url, timeout=args.timeout)
    results: list[StepResult] = []
    started_at_iso = _utc_now_iso()
    started_at = time.perf_counter()
    try:
        results = run_regression_suite(
            client,
            suite=args.suite,
            task_execution_mode=args.task_execution_mode,
            username=args.username,
            password=args.password,
        )
    except RegressionError as exc:
        finished_at_iso = _utc_now_iso()
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        if args.json_output:
            report = build_regression_report(
                api_base_url=args.api_base_url,
                duration_ms=duration_ms,
                error=str(exc),
                finished_at=finished_at_iso,
                started_at=started_at_iso,
                status="failed",
                steps=results,
                suite=args.suite,
                task_execution_mode=args.task_execution_mode,
            )
            try:
                write_json_report(args.json_output, report)
                print(f"Full-chain regression report written to {args.json_output}.", file=sys.stderr)
            except OSError as report_exc:
                print(f"[FAIL] Could not write full-chain regression report: {report_exc}", file=sys.stderr)
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    finished_at_iso = _utc_now_iso()
    duration_ms = int((time.perf_counter() - started_at) * 1000)
    if args.json_output:
        report = build_regression_report(
            api_base_url=args.api_base_url,
            duration_ms=duration_ms,
            error=None,
            finished_at=finished_at_iso,
            started_at=started_at_iso,
            status="passed",
            steps=results,
            suite=args.suite,
            task_execution_mode=args.task_execution_mode,
        )
        try:
            write_json_report(args.json_output, report)
        except OSError as exc:
            print(f"[FAIL] Could not write full-chain regression report: {exc}", file=sys.stderr)
            return 1
    for result in results:
        print(f"[OK] {result.name}: {result.detail}")
    if args.json_output:
        print(f"Full-chain regression report written to {args.json_output}.")
    print(f"Full-chain regression passed in {duration_ms} ms.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
