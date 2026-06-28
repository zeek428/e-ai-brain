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

    def get(self, path: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        if query:
            path = f"{path}?{urlencode({key: value for key, value in query.items() if value is not None})}"
        return self.request("GET", path)

    def post(self, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request("POST", path, body=body or {})

    def request(
        self,
        method: str,
        path: str,
        *,
        authenticated: bool = True,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Accept": "application/json", "Connection": "close"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if authenticated:
            if not self.token:
                raise RegressionError("Authenticated request attempted before login.")
            headers["Authorization"] = f"Bearer {self.token}"
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
    results.append(
        StepResult(
            "knowledge_deposit",
            f"{deposit['id']} -> {approved_deposit.get('knowledge_document_id')}",
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
    report_id = scan_run.get("result_summary", {}).get("report_id")
    _assert(bool(report_id), f"Code inspection run did not return report_id: {scan_run}")
    report_detail = client.get(f"/api/governance/code-inspections/{report_id}")
    _assert(report_detail["report"]["scan_mode"] == "native_full_scan", "Report is not native_full_scan.")
    _assert(report_detail["report"]["branch"] == version_branch, "Report branch does not match version branch.")
    results.append(StepResult("code_inspection", f"{report_id} / {scan_run['id']}"))

    bugs = client.get("/api/bugs", {"product_id": product["id"], "source": "code_inspection"})
    bug_items = bugs.get("items", [])
    _assert(len(bug_items) >= 1, "Code inspection did not create a Bug.")
    remediation_tasks = client.get(
        "/api/ai-tasks",
        {"product_id": product["id"], "task_type": "code_inspection_remediation"},
    )
    remediation_items = remediation_tasks.get("items", [])
    _assert(len(remediation_items) >= 1, "Code inspection did not create a remediation task.")
    results.append(StepResult("inspection_writeback", f"bugs={len(bug_items)}, tasks={len(remediation_items)}"))

    dashboard = client.get(f"/api/product-versions/{version['id']}/dashboard")
    _assert(dashboard["summary"]["requirements"] >= 1, "Version dashboard missed requirement summary.")
    _assert(dashboard["summary"]["code_inspection_reports"] >= 1, "Version dashboard missed code inspection report.")
    _assert(dashboard["summary"]["branch_configs"] >= 1, "Version dashboard missed branch config.")
    results.append(StepResult("version_dashboard", f"blockers={dashboard['summary']['blockers']}"))

    full_chain = client.get(
        "/api/lifecycle/full-chain",
        {"subject_id": version["id"], "subject_type": "product_version"},
    )
    _assert(full_chain["requirement"]["id"] == requirement["id"], "Full-chain did not resolve to requirement.")
    report_ids = {item["id"] for item in full_chain.get("code_inspection_reports", [])}
    _assert(report_id in report_ids, "Full-chain did not include code inspection report.")
    results.append(StepResult("full_chain", f"timeline={len(full_chain.get('timeline', []))}"))

    team_dashboard = client.get("/api/dashboard/it-team", {"product_id": product["id"], "refresh": "true", "time_range": "all"})
    _assert("summary" in team_dashboard or "metrics" in team_dashboard, "IT team dashboard response missing summary/metrics.")
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
    _assert(assistant.get("message", {}).get("id"), f"Assistant chat response missing message: {assistant}")
    results.append(StepResult("assistant_qa", assistant["message"]["id"]))

    results.append(StepResult("fixture_repository", str(repo_path)))
    return results


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
        "--username",
        default=os.getenv("FULL_CHAIN_USERNAME", os.getenv("READINESS_USERNAME", "admin@example.com")),
        help="Login username. Defaults to FULL_CHAIN_USERNAME, READINESS_USERNAME, or admin@example.com.",
    )
    args = parser.parse_args()

    client = ApiClient(args.api_base_url, timeout=args.timeout)
    started_at = time.perf_counter()
    try:
        results = run_regression(
            client,
            task_execution_mode=args.task_execution_mode,
            username=args.username,
            password=args.password,
        )
    except RegressionError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    duration_ms = int((time.perf_counter() - started_at) * 1000)
    for result in results:
        print(f"[OK] {result.name}: {result.detail}")
    print(f"Full-chain regression passed in {duration_ms} ms.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
