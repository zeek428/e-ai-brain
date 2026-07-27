#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from full_chain_regression_assistant_drafts import validate_assistant_draft_governance  # noqa: E402
from full_chain_regression_assistant_qa import validate_assistant_qa_quick_regression  # noqa: E402
from full_chain_regression_code_inspection import (  # noqa: E402
    validate_code_inspection_governance_quick_regression,  # noqa: E402
)
from full_chain_regression_knowledge import (  # noqa: E402
    validate_knowledge_index_health_quick_regression,  # noqa: E402
)
from full_chain_regression_permissions import (  # noqa: E402
    validate_permission_visibility_quick_regression,  # noqa: E402
)
from full_chain_regression_rd_collaboration import (  # noqa: E402
    validate_rd_collaboration_quick_regression,
)
from full_chain_regression_rd_delivery_e2e import (  # noqa: E402
    RD_E2E_SCENARIOS,
    RdDeliveryE2EConfig,
    validate_rd_delivery_e2e,
)
from full_chain_regression_rd_runner_protocol import (  # noqa: E402
    complete_ai_work_item_via_runner_protocol,
)
from full_chain_regression_runner import validate_ai_executor_runner_reliability  # noqa: E402
from full_chain_regression_slug import regression_slug  # noqa: E402
from full_chain_regression_suites import (  # noqa: E402
    REGRESSION_TARGETED_SUITE_NAMES,
    approve_high_risk_dispatch,
    create_v2_collaboration_setup,
    regression_suite_coverage,
    wait_for_ai_work_item,
)
from full_chain_regression_version_dashboard import (  # noqa: E402
    validate_version_dashboard_blocker_actions,
    validate_version_dashboard_branch_quality,
    validate_version_dashboard_delivery_stage_overview,
    validate_version_dashboard_evidence_coverage,
    validate_version_dashboard_governance_conclusion,
    validate_version_dashboard_next_actions,
    validate_version_dashboard_release_readiness,
    validate_version_dashboard_status_impact,
    validate_version_dashboard_status_impact_projection,
)

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
    evidence: dict[str, Any] | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_regression_suite_coverage(suite: str) -> StepResult:
    coverage = regression_suite_coverage(suite)
    _assert(
        coverage["covered_domain_count"] > 0,
        f"Regression suite has no declared coverage domains: {suite}",
    )
    if suite == "full":
        _assert(
            coverage["is_complete_chain"],
            f"Full regression suite coverage is incomplete: {coverage}",
        )
    return StepResult(
        "coverage",
        (
            f"{coverage['covered_domain_count']}/"
            f"{coverage['objective_domain_count']} objective domains"
        ),
    )


def regression_suite_header_results(suite: str) -> list[StepResult]:
    return [StepResult("suite", suite), validate_regression_suite_coverage(suite)]


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
        "coverage": regression_suite_coverage(suite),
        "duration_ms": duration_ms,
        "finished_at": finished_at,
        "started_at": started_at,
        "status": status,
        "steps": [
            {
                **{"detail": step.detail, "name": step.name},
                **({"evidence": step.evidence} if step.evidence is not None else {}),
            }
            for step in steps
        ],
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


def validate_login_credentials(username: str | None, password: str | None) -> tuple[str, str]:
    missing: list[str] = []
    if not username or not str(username).strip():
        missing.append("--username or FULL_CHAIN_USERNAME/READINESS_USERNAME")
    if not password or not str(password).strip():
        missing.append("--password or FULL_CHAIN_PASSWORD/READINESS_PASSWORD")
    if missing:
        raise RegressionError(
            "Missing full-chain login credentials: provide "
            + " and ".join(missing)
            + "."
        )
    return str(username).strip(), str(password)


def parse_task_execution_mode(value: str) -> str:
    if value != "simulated_runner":
        raise argparse.ArgumentTypeError(
            "only simulated_runner is supported by the full-chain regression suites"
        )
    return value


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
        challenge = self.request(
            "POST",
            "/api/auth/login-challenge",
            body={},
            authenticated=False,
        )
        challenge_id = str(challenge.get("challenge_id") or "").strip()
        question = str(challenge.get("question") or "")
        addition = re.search(r"(\d+)\s*\+\s*(\d+)", question)
        if not challenge_id or addition is None:
            raise RegressionError(
                "Login challenge response is missing a supported arithmetic prompt."
            )
        payload = self.request(
            "POST",
            "/api/auth/login",
            body={
                "challenge_answer": str(int(addition.group(1)) + int(addition.group(2))),
                "challenge_id": challenge_id,
                "password": password,
                "username": username,
            },
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

    def patch(
        self,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return self.request("PATCH", path, body=body or {}, extra_headers=headers)

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
    return regression_slug()


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RegressionError(message)


def _v2_work_item(
    *,
    input_contract: dict[str, Any] | None = None,
    item_id: str,
    owner_role_code: str,
    priority: int,
    risk_level: str,
    reviewer_role_code: str,
    work_item_type: str,
) -> dict[str, Any]:
    return {
        "acceptance_criteria": ["Regression evidence is recorded"],
        "description": f"Full-chain v2 work item: {item_id}",
        "id": item_id,
        "input_contract": input_contract or {},
        "owner_role_code": owner_role_code,
        "output_contract": {},
        "priority": priority,
        "reviewer_role_code": reviewer_role_code,
        "risk_level": risk_level,
        "title": item_id,
        "work_item_type": work_item_type,
    }


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


def select_active_knowledge_space(client: ApiClient) -> dict[str, Any]:
    response = client.get("/api/knowledge/spaces")
    space = next(
        (
            item
            for item in response.get("items", [])
            if item.get("status") == "active" and str(item.get("id") or "").strip()
        ),
        None,
    )
    _assert(space is not None, f"No accessible active knowledge space found: {response}")
    return space


def validate_code_inspection_requirement_coverage(
    client: ApiClient,
    *,
    committer_governance: dict[str, Any],
    governance_summary: dict[str, Any],
    product_id: str,
    report: dict[str, Any],
) -> set[str]:
    _assert(
        int(governance_summary.get("covered_by_requirement_count") or 0) >= 1,
        f"Governance summary did not count requirement coverage: {governance_summary}",
    )
    _assert(
        int(governance_summary.get("historical_covered_by_task_count") or 0) == 0,
        f"Governance summary unexpectedly counted direct task coverage: {governance_summary}",
    )
    _assert(
        float(governance_summary.get("requirement_coverage_rate") or 0) == 1.0,
        f"Governance summary did not close requirement coverage: {governance_summary}",
    )
    _assert(
        int(committer_governance.get("covered_by_requirement_count") or 0) >= 1,
        f"Committer governance missed requirement coverage: {committer_governance}",
    )
    _assert(
        int(committer_governance.get("historical_covered_by_task_count") or 0) == 0,
        f"Committer governance unexpectedly counted direct task coverage: {committer_governance}",
    )
    requirement_ids = {str(item) for item in report.get("created_requirement_ids") or []}
    _assert(
        requirement_ids,
        f"Code inspection report did not record created requirement ids: {report}",
    )
    _assert(
        not report.get("created_task_ids"),
        f"Code inspection report unexpectedly created direct remediation tasks: {report}",
    )
    requirements = client.get(
        "/api/requirements",
        {"page": 1, "page_size": 100, "product_id": product_id},
    )
    listed_ids = _ids(requirements.get("items", []))
    for requirement_id in requirement_ids:
        _assert_contains(
            listed_ids,
            requirement_id,
            "Code inspection remediation requirement missing from requirement ledger",
        )
    return requirement_ids


def validate_code_inspection_report_full_chain_requirement(
    report_full_chain: dict[str, Any],
    report_requirement_ids: set[str],
) -> str:
    requirement_id = str((report_full_chain.get("requirement") or {}).get("id") or "")
    _assert_contains(
        report_requirement_ids,
        requirement_id,
        "Code inspection report subject did not resolve to its remediation requirement",
    )
    return requirement_id


def validate_full_team_dashboard_collaboration_task(
    team_dashboard: dict[str, Any],
    task_id: str,
) -> None:
    summary = team_dashboard.get("summary") or {}
    _assert(
        int(summary.get("ai_tasks") or 0) >= 1,
        f"IT team dashboard missed collaboration AI task: {summary}",
    )
    _assert_contains(
        _ids(team_dashboard.get("latest_tasks", [])),
        task_id,
        "Dashboard missed completed collaboration AI task",
    )


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
            "status": "planning",
        },
    )
    results.append(StepResult("version_dashboard_product", f"{product['id']} / {version['id']}"))

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

    marker = f"version-dashboard-{slug}"
    ai_role_code = f"simulated-ai-{marker}"
    assessment_role_code = f"simulated-assessor-{marker}"
    human_role_code = f"simulated-reviewer-{marker}"
    design_id = f"design-{slug}"
    solution_id = f"solution-{slug}"
    snapshot_binding_id = f"snapshot-binding-{slug}"
    setup = create_v2_collaboration_setup(
        client,
        dependencies=(
            {
                "predecessor_work_item_id": design_id,
                "successor_work_item_id": solution_id,
            },
            {
                "predecessor_work_item_id": solution_id,
                "successor_work_item_id": snapshot_binding_id,
            },
        ),
        marker=marker,
        matching_task_types=("code_review",),
        owner_user_id=str(user["id"]),
        product_id=str(product["id"]),
        repository_id=str(repository["id"]),
        requirement=None,
        work_items=(
            _v2_work_item(
                item_id=design_id,
                owner_role_code=ai_role_code,
                priority=1,
                risk_level="low",
                reviewer_role_code=human_role_code,
                work_item_type="product_detail_design",
            ),
            _v2_work_item(
                item_id=solution_id,
                owner_role_code=ai_role_code,
                priority=2,
                risk_level="low",
                reviewer_role_code=human_role_code,
                work_item_type="technical_solution",
            ),
            _v2_work_item(
                item_id=snapshot_binding_id,
                owner_role_code=assessment_role_code,
                priority=3,
                risk_level="low",
                reviewer_role_code=human_role_code,
                work_item_type="documentation",
            ),
        ),
        workspace_root=str(repo_path),
    )
    fixture = setup.fixture
    _assert(
        fixture.version_id == version["id"],
        f"Version dashboard collaboration selected another version: {fixture}",
    )
    requirement = {"id": fixture.requirement_id}
    design_work_item = next(
        item
        for item in fixture.work_items
        if item.get("work_item_type") == "product_detail_design"
    )
    solution_work_item = next(
        item
        for item in fixture.work_items
        if item.get("work_item_type") == "technical_solution"
    )
    snapshot_binding_work_item = next(
        item
        for item in fixture.work_items
        if item.get("work_item_type") == "documentation"
    )
    results.append(
        StepResult(
            "version_dashboard_requirement",
            f"{requirement['id']} / run={fixture.run_id}",
        )
    )

    wait_for_ai_work_item(
        client,
        run_id=fixture.run_id,
        status="running",
        timeout_seconds=30.0,
        work_item_id=str(design_work_item["id"]),
    )
    design_result = complete_ai_work_item_via_runner_protocol(
        client,
        setup.session,
        fixture.run_id,
        str(design_work_item["id"]),
        client,
        30.0,
    )
    task_id = design_result.ai_task_id
    results.append(
        StepResult("version_dashboard_design", design_result.step_detail)
    )
    wait_for_ai_work_item(
        client,
        run_id=fixture.run_id,
        status="running",
        timeout_seconds=30.0,
        work_item_id=str(solution_work_item["id"]),
    )
    solution_result = complete_ai_work_item_via_runner_protocol(
        client,
        setup.session,
        fixture.run_id,
        str(solution_work_item["id"]),
        client,
        30.0,
    )
    technical_solution_task_id = solution_result.ai_task_id
    results.append(
        StepResult("version_dashboard_solution", solution_result.step_detail)
    )
    snapshot_binding_work_item = wait_for_ai_work_item(
        client,
        run_id=fixture.run_id,
        status="ready",
        timeout_seconds=30.0,
        work_item_id=str(snapshot_binding_work_item["id"]),
    )
    claimed_binding = client.post(
        f"/api/delivery/rd-work-items/{snapshot_binding_work_item['id']}/claim",
        {
            "expected_version": snapshot_binding_work_item["version"],
            "idempotency_key": (
                f"claim-snapshot-binding:{marker}:{snapshot_binding_work_item['id']}"
            ),
            "lease_seconds": 60,
        },
    )
    binding_attempt = claimed_binding.get("attempt") or {}
    claimed_binding_item = claimed_binding.get("work_item") or {}
    binding_lease_token = str(claimed_binding.get("lease_token") or "")
    _assert(
        binding_attempt.get("id")
        and binding_lease_token
        and claimed_binding_item.get("status") == "running",
        f"Snapshot-binding work item was not claimed: {claimed_binding}",
    )

    snapshot = client.post(
        f"/api/devops/gitlab/merge-requests/{repository['id']}/7/snapshot",
        {
            "requirement_id": requirement["id"],
            "technical_solution_task_id": technical_solution_task_id,
        },
    )
    review_id = f"review-{slug}"
    replan = client.post(
        f"/api/delivery/rd-collaboration-runs/{fixture.run_id}/replan",
        {
            "dependencies": [],
            "work_items": [
                {
                    **_v2_work_item(
                        input_contract={"gitlab_mr_snapshot_id": snapshot["id"]},
                        item_id=review_id,
                        owner_role_code=ai_role_code,
                        priority=1,
                        risk_level="high",
                        reviewer_role_code=human_role_code,
                        work_item_type="code_review",
                    ),
                    "requirement_id": requirement["id"],
                }
            ],
        },
    )
    _assert(
        int(replan.get("plan_version") or 0) == 2,
        f"Version dashboard code-review replan did not create plan version 2: {replan}",
    )
    code_review_work_item = next(
        item
        for item in replan.get("work_items") or []
        if item.get("work_item_type") == "code_review"
    )
    _assert(
        (code_review_work_item.get("input_contract") or {}).get(
            "gitlab_mr_snapshot_id"
        )
        == snapshot["id"],
        f"Code-review plan did not freeze the real MR snapshot: {code_review_work_item}",
    )
    submitted_binding = client.post(
        f"/api/delivery/rd-work-items/{snapshot_binding_work_item['id']}/submit",
        {
            "attempt_id": binding_attempt["id"],
            "evidence": {
                "gitlab_mr_snapshot_id": snapshot["id"],
                "status": "passed",
            },
            "idempotency_key": (
                f"submit-snapshot-binding:{marker}:{snapshot_binding_work_item['id']}"
            ),
            "lease_token": binding_lease_token,
            "output": {
                "gitlab_mr_snapshot_id": snapshot["id"],
                "summary": "Real MR snapshot bound to immutable code-review plan",
            },
            "version": claimed_binding_item["version"],
        },
    )
    submitted_binding_item = submitted_binding.get("work_item") or {}
    _assert(
        submitted_binding_item.get("status") == "reviewing",
        f"Snapshot-binding work item did not enter review: {submitted_binding}",
    )
    reviewed_binding = client.post(
        f"/api/delivery/rd-work-items/{snapshot_binding_work_item['id']}/review",
        {
            "comment": "MR snapshot binding independently reviewed",
            "decision": "approve",
            "idempotency_key": (
                f"review-snapshot-binding:{marker}:{snapshot_binding_work_item['id']}"
            ),
            "version": submitted_binding_item["version"],
        },
    )
    _assert(
        (reviewed_binding.get("work_item") or {}).get("status") == "completed",
        f"Snapshot-binding work item did not complete: {reviewed_binding}",
    )
    results.append(
        StepResult("version_dashboard_branch", f"{branch_config['id']} / {version_branch}")
    )
    approve_high_risk_dispatch(
        client,
        marker=marker,
        run_id=fixture.run_id,
        timeout_seconds=30.0,
        work_item_id=str(code_review_work_item["id"]),
    )
    wait_for_ai_work_item(
        client,
        run_id=fixture.run_id,
        status="running",
        timeout_seconds=30.0,
        work_item_id=str(code_review_work_item["id"]),
    )
    code_review_result = complete_ai_work_item_via_runner_protocol(
        client,
        setup.session,
        fixture.run_id,
        str(code_review_work_item["id"]),
        client,
        30.0,
    )
    code_review_task_id = code_review_result.ai_task_id
    code_review_report = client.get(
        f"/api/ai-tasks/{code_review_task_id}/code-review-report"
    )
    _assert(
        code_review_report.get("status") == "approved",
        (
            "Version dashboard persisted Code Review report was not approved: "
            f"{code_review_report}"
        ),
    )
    results.append(
        StepResult(
            "version_dashboard_code_review",
            (
                f"{code_review_task_id} / report={code_review_report['id']} "
                f"/ snapshot={snapshot['id']}"
            ),
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
    version_bug = client.post(
        "/api/bugs",
        {
            "description": "版本总览快速回归创建的阻塞 Bug，用于验证版本页集中展示缺陷和发布阻塞。",
            "evidence": {
                "code_review_report_id": code_review_report["id"],
                "gitlab_mr_snapshot_id": snapshot["id"],
                "regression_suite": "version-dashboard",
            },
            "product_id": product["id"],
            "related_task_id": code_review_task_id,
            "requirement_id": requirement["id"],
            "reproduce_steps": ["打开版本总览", "确认 Bug 汇总、列表和阻塞项"],
            "severity": "blocker",
            "source": "manual_test",
            "title": f"版本总览快速回归阻塞 Bug {slug}",
            "version_id": version["id"],
        },
    )
    _assert(
        version_bug.get("status") == "open",
        f"Version dashboard quick Bug was not open: {version_bug}",
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
        dashboard["summary"].get("pending_code_review_reports", 0) == 0,
        "Version dashboard quick check retained a completed code review as pending.",
    )
    _assert(
        dashboard["summary"].get("bugs", 0) >= 1,
        "Version dashboard quick check missed Bug summary.",
    )
    _assert(
        dashboard["summary"].get("open_bugs", 0) >= 1,
        "Version dashboard quick check missed open Bug summary.",
    )
    _assert(
        dashboard["summary"].get("severe_bugs", 0) >= 1,
        "Version dashboard quick check missed severe Bug summary.",
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
        _ids(dashboard.get("tasks", [])),
        technical_solution_task_id,
        "Version dashboard quick check missed technical solution task row",
    )
    _assert_contains(
        _ids(dashboard.get("tasks", [])),
        code_review_task_id,
        "Version dashboard quick check missed code review task row",
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
    _assert_contains(
        _ids(dashboard.get("bugs", [])),
        version_bug["id"],
        "Version dashboard quick check missed Bug row",
    )
    _assert(
        _status_count(dashboard.get("bug_status_counts", []), "open") >= 1,
        "Version dashboard quick check missed open Bug status count.",
    )
    validate_version_dashboard_status_impact(
        dashboard,
        expected_target_status="released",
        require_preview=True,
    )
    dashboard_blockers = dashboard.get("blockers", [])
    _assert(
        dashboard["summary"]["blockers"] >= 1,
        "Version dashboard quick check did not expose blockers.",
    )
    validate_version_dashboard_blocker_actions(dashboard_blockers)
    validate_version_dashboard_next_actions(dashboard, dashboard_blockers)
    validate_version_dashboard_governance_conclusion(dashboard, dashboard_blockers)
    validate_version_dashboard_delivery_stage_overview(dashboard)
    validate_version_dashboard_evidence_coverage(dashboard, require_blockers=True)
    validate_version_dashboard_release_readiness(dashboard, require_blockers=True)
    validate_version_dashboard_status_impact(dashboard)
    release_evidence_blockers = [
        blocker
        for blocker in dashboard_blockers
        if blocker.get("source_type") == "deployment_request"
        and blocker.get("action_target_type") == "product_version"
        and str(blocker.get("action_target_id")) == version["id"]
    ]
    _assert(
        release_evidence_blockers,
        f"Version dashboard quick check missed deployment evidence blocker: {dashboard_blockers}",
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
    bug_blockers = [
        blocker
        for blocker in dashboard_blockers
        if blocker.get("source_type") == "bug"
        and str(blocker.get("action_target_id")) == version_bug["id"]
    ]
    _assert(
        bug_blockers,
        f"Version dashboard quick check missed Bug blocker: {dashboard_blockers}",
    )
    _assert(
        dashboard.get("next_actions", [{}])[0].get("source_type") == "bug",
        f"Version dashboard next actions should prioritize blocker Bug: {dashboard.get('next_actions')}",
    )
    branch_quality = validate_version_dashboard_branch_quality(
        dashboard,
        branch_config_id=branch_config["id"],
        branch_name=version_branch,
        expected_status="pending_scan",
    )
    results.append(
        StepResult(
            "version_dashboard_branch_quality",
            f"{branch_quality['status']} / pending_scan={dashboard['summary'].get('branch_quality_pending_scan')}",
        )
    )
    results.append(
        StepResult(
            "version_dashboard_quick",
            (
                f"blockers={dashboard['summary']['blockers']}, "
                f"tasks={dashboard['summary']['tasks']}, bugs={dashboard['summary'].get('bugs')}"
            ),
        )
    )
    results.append(StepResult("fixture_repository", str(repo_path)))
    return results


def run_regression(
    client: ApiClient,
    *,
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
            "status": "planning",
        },
    )
    results.append(StepResult("version", f"{version['id']} / {version['code']}"))

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
            "version_id": version["id"],
        },
    )
    requirement = converted["requirement"]
    _assert(converted["feedback"]["status"] == "linked", "Feedback was not linked after conversion.")
    results.append(StepResult("feedback_to_requirement", f"{feedback['id']} -> {requirement['id']}"))

    marker = f"full-chain-{slug}"
    ai_role_code = f"simulated-ai-{marker}"
    human_role_code = f"simulated-reviewer-{marker}"
    design_id = f"product-detail-design-{slug}"
    setup = create_v2_collaboration_setup(
        client,
        dependencies=(),
        marker=marker,
        owner_user_id=str(user["id"]),
        product_id=str(product["id"]),
        repository_id=str(repository["id"]),
        requirement=requirement,
        work_items=(
            _v2_work_item(
                item_id=design_id,
                owner_role_code=ai_role_code,
                priority=1,
                risk_level="low",
                reviewer_role_code=human_role_code,
                work_item_type="product_detail_design",
            ),
        ),
        workspace_root=str(repo_path),
    )
    fixture = setup.fixture
    _assert(
        fixture.requirement_id == requirement["id"]
        and fixture.version_id == version["id"],
        f"Full regression collaboration scope drifted: {fixture}",
    )
    results.append(
        StepResult(
            "requirement_schedule",
            f"{requirement['id']} -> {version['id']} / run={fixture.run_id}",
        )
    )
    design_work_item = next(
        item
        for item in fixture.work_items
        if item.get("work_item_type") == "product_detail_design"
    )
    wait_for_ai_work_item(
        client,
        run_id=fixture.run_id,
        status="running",
        timeout_seconds=30.0,
        work_item_id=str(design_work_item["id"]),
    )
    design_result = complete_ai_work_item_via_runner_protocol(
        client,
        setup.session,
        fixture.run_id,
        str(design_work_item["id"]),
        client,
        30.0,
    )
    task_id = design_result.ai_task_id
    results.append(
        StepResult(
            "ai_task_review",
            f"{design_result.step_detail} / mode=simulated_runner",
        )
    )

    deposit = find_deposit_for_task(client, task_id)
    _assert(deposit is not None, f"No pending knowledge deposit found for task {task_id}.")
    knowledge_space = select_active_knowledge_space(client)
    approved_deposit = client.post(
        f"/api/knowledge/deposits/{deposit['id']}/approve",
        {
            "knowledge_space_id": knowledge_space["id"],
            "permission_roles": ["admin", "product_owner", "rd_owner"],
            "title": f"全链路回归知识沉淀 {slug}",
        },
    )
    _assert(approved_deposit.get("status") == "approved", f"Knowledge deposit was not approved: {approved_deposit}")
    knowledge_document_id = str(approved_deposit.get("knowledge_document_id") or "")
    _assert(knowledge_document_id, f"Knowledge deposit did not return a knowledge_document_id: {approved_deposit}")
    results.append(
        StepResult(
            "knowledge_deposit",
            f"{deposit['id']} -> {knowledge_document_id} / space={knowledge_space['id']}",
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

    scan_config = {
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
    }
    scan_job = client.post(
        "/api/system/scheduled-jobs",
        {
            "config_json": scan_config,
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
        int(governance_pressure.get("uncovered_requirement_finding_count") or 0) == 0,
        f"Code inspection governance pressure did not close requirement coverage: {governance_pressure}",
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
    report_bug_ids = {str(item) for item in report.get("created_bug_ids") or []}
    _assert(report_bug_ids, f"Code inspection report did not record created Bug ids: {report}")
    report_requirement_ids = validate_code_inspection_requirement_coverage(
        client,
        committer_governance=committer_governance_item,
        governance_summary=governance_summary,
        product_id=product["id"],
        report=report,
    )
    results.append(StepResult("code_inspection", f"{report_id} / findings={len(findings)} / {scan_run['id']}"))
    results.append(
        StepResult(
            "code_inspection_governance_pressure",
            (
                f"status={governance_pressure.get('status')}, "
                f"gate_failures={governance_pressure.get('quality_gate_failed_report_count')}, "
                f"uncovered_bug={governance_pressure.get('uncovered_bug_finding_count')}, "
                "uncovered_requirement="
                f"{governance_pressure.get('uncovered_requirement_finding_count')}"
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
    results.append(
        StepResult(
            "inspection_writeback",
            f"bugs={len(report_bug_ids)}, requirements={len(report_requirement_ids)}",
        )
    )

    comparison_scan_job = client.post(
        "/api/system/scheduled-jobs",
        {
            "config_json": scan_config,
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": f"全链路代码巡检趋势对比 {slug}",
            "product_id": product["id"],
            "result_actions": [{"type": "write_code_inspection_report"}],
            "schedule_type": "manual",
            "source_system": "native-code-scanner",
        },
    )
    comparison_scan_run = client.post(f"/api/system/scheduled-jobs/{comparison_scan_job['id']}/run")
    _assert(
        comparison_scan_run.get("status") == "succeeded",
        f"Code inspection comparison run failed: {comparison_scan_run}",
    )
    comparison_report_id = (comparison_scan_run.get("result_summary") or {}).get("report_id")
    _assert(
        bool(comparison_report_id),
        f"Code inspection comparison run did not return report_id: {comparison_scan_run}",
    )
    comparison_report_detail = client.get(f"/api/governance/code-inspections/{comparison_report_id}")
    comparison_report = comparison_report_detail["report"]
    comparison_previous = (
        (comparison_report_detail.get("scan_summary") or {}).get("previous_comparison")
        or comparison_report.get("previous_comparison")
        or {}
    )
    _assert(
        comparison_report.get("branch") == version_branch,
        f"Comparison report branch does not match version branch: {comparison_report}",
    )
    _assert(
        comparison_report.get("previous_report_id") == report_id,
        f"Comparison report did not persist previous_report_id={report_id}: {comparison_report}",
    )
    _assert(
        comparison_previous.get("previous_report_id") == report_id,
        f"Comparison report missed previous comparison report id: {comparison_previous}",
    )
    _assert(
        int(comparison_previous.get("previous_finding_count") or -1) == int(report.get("finding_count") or 0),
        f"Comparison report previous finding count mismatch: {comparison_previous}",
    )
    _assert(
        int(comparison_previous.get("previous_severe_finding_count") or -1)
        == int(report.get("severe_finding_count") or 0),
        f"Comparison report previous severe finding count mismatch: {comparison_previous}",
    )
    _assert(
        int(comparison_previous.get("finding_delta") or 0) == 0,
        f"Comparison report should have stable finding_delta for unchanged fixture: {comparison_previous}",
    )
    _assert(
        int(comparison_previous.get("severe_finding_delta") or 0) == 0,
        f"Comparison report should have stable severe_finding_delta for unchanged fixture: {comparison_previous}",
    )
    results.append(
        StepResult(
            "code_inspection_trend_comparison",
            f"{comparison_report_id} / previous={comparison_previous.get('previous_report_id')}",
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
    branch_quality = validate_version_dashboard_branch_quality(
        dashboard,
        branch_config_id=branch_config["id"],
        branch_name=version_branch,
        expected_status="action_required",
        report_id=comparison_report_id,
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
    validate_version_dashboard_next_actions(dashboard, dashboard_blockers)
    validate_version_dashboard_governance_conclusion(dashboard, dashboard_blockers)
    validate_version_dashboard_delivery_stage_overview(dashboard)
    dashboard_evidence_coverage = validate_version_dashboard_evidence_coverage(
        dashboard,
        require_blockers=True,
    )
    validate_version_dashboard_release_readiness(dashboard, require_blockers=True)
    dashboard_status_impact = validate_version_dashboard_status_impact(dashboard)
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
        if blocker.get("source_type") == "deployment_request"
        and str(blocker.get("action_target_id")) == version["id"]
        and blocker.get("action_target_type") == "product_version"
    ]
    _assert(
        release_evidence_blockers,
        f"Version dashboard missed deployment evidence blocker for product version: {dashboard_blockers}",
    )
    _assert(
        any("缺少成功运维部署" in str(blocker.get("reason") or "") for blocker in release_evidence_blockers),
        f"Version dashboard deployment blocker did not explain missing successful deployment: {release_evidence_blockers}",
    )
    results.append(
        StepResult(
            "version_dashboard",
            (
                f"blockers={dashboard['summary']['blockers']}, "
                f"blocker_actions={len(dashboard_blockers)}, "
                f"evidence_score={dashboard_evidence_coverage['score']}, "
                f"branch_quality={branch_quality['status']}"
            ),
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
    validate_code_inspection_report_full_chain_requirement(
        report_full_chain,
        report_requirement_ids,
    )
    results.append(StepResult("full_chain", f"timeline={len(full_chain.get('timeline', []))}"))

    team_dashboard = client.get("/api/dashboard/it-team", {"product_id": product["id"], "refresh": "true", "time_range": "all"})
    dashboard_summary = team_dashboard.get("summary") or {}
    _assert(int(dashboard_summary.get("requirements") or 0) >= 1, f"IT team dashboard missed requirements: {dashboard_summary}")
    _assert(int(dashboard_summary.get("bugs") or 0) >= 1, f"IT team dashboard missed Bugs: {dashboard_summary}")
    _assert(
        int(dashboard_summary.get("knowledge_documents") or 0) >= 1,
        f"IT team dashboard missed knowledge documents: {dashboard_summary}",
    )
    _assert(_status_count(team_dashboard.get("user_feedback_status_counts", []), "linked") >= 1, "Dashboard missed linked feedback count.")
    _assert(_status_count(team_dashboard.get("bug_status_counts", []), "open") >= 1, "Dashboard missed open Bug count.")
    validate_full_team_dashboard_collaboration_task(team_dashboard, task_id)
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
            "message": (
                f"请基于产品 {product['name']} 的这次全链路回归引用，"
                "总结版本总览阻塞项、下一步行动和后续跟进任务。"
            ),
            "product_id": product["id"],
            "references": [
                {"id": requirement["id"], "type": "requirement"},
                {"id": version["id"], "type": "product_version"},
                {"id": report_id, "type": "code_inspection_report"},
            ],
        },
    )
    assistant_message = assistant.get("message", {})
    _assert(
        assistant.get("model") == "assistant-deterministic",
        f"Assistant version governance question should be deterministic: {assistant}",
    )
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
    assistant_tool_results = assistant_message.get("tool_results") or []
    assistant_iteration_tools = [
        item for item in assistant_tool_results if item.get("tool") == "assistant.iteration"
    ]
    _assert(
        assistant_iteration_tools,
        f"Assistant response missed iteration governance tool result: {assistant_tool_results}",
    )
    assistant_iteration_items = assistant_iteration_tools[0].get("items") or []
    assistant_version_items = [
        item for item in assistant_iteration_items if str(item.get("id")) == version["id"]
    ]
    _assert(
        assistant_version_items,
        f"Assistant iteration tool missed product version {version['id']}: {assistant_iteration_items}",
    )
    assistant_version_item = assistant_version_items[0]
    _assert(
        int(assistant_version_item.get("blocker_count") or 0)
        == int(dashboard["summary"].get("blockers") or 0),
        f"Assistant iteration blocker count drifted: {assistant_version_item}",
    )
    dashboard_next_action_sources = [
        str(item.get("source_type") or "") for item in dashboard.get("next_actions", [])
    ]
    assistant_next_action_sources = [
        str(item.get("source_type") or "")
        for item in assistant_version_item.get("next_actions", [])
    ]
    _assert(
        assistant_next_action_sources == dashboard_next_action_sources[:3],
        (
            "Assistant iteration tool did not carry version dashboard next_actions: "
            f"assistant={assistant_version_item.get('next_actions')}, "
            f"dashboard={dashboard.get('next_actions')}"
        ),
    )
    dashboard_stage_keys = [
        str(item.get("key") or "")
        for item in dashboard.get("delivery_stage_overview", [])
    ]
    assistant_stage_keys = [
        str(item.get("key") or "")
        for item in assistant_version_item.get("delivery_stage_overview", [])
    ]
    _assert(
        assistant_stage_keys == dashboard_stage_keys[:9],
        (
            "Assistant iteration tool did not carry version dashboard delivery_stage_overview: "
            f"assistant={assistant_version_item.get('delivery_stage_overview')}, "
            f"dashboard={dashboard.get('delivery_stage_overview')}"
        ),
    )
    dashboard_conclusion = dashboard.get("governance_conclusion") or {}
    assistant_conclusion = assistant_version_item.get("governance_conclusion") or {}
    for field in ("level", "value"):
        _assert(
            assistant_conclusion.get(field) == dashboard_conclusion.get(field),
            (
                "Assistant iteration tool did not carry version dashboard governance_conclusion: "
                f"field={field}, assistant={assistant_conclusion}, dashboard={dashboard_conclusion}"
            ),
        )
    validate_version_dashboard_status_impact_projection(
        dashboard_status_impact,
        assistant_version_item.get("status_impact"),
        label="Assistant iteration tool",
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
    persisted_iteration_tools = [
        item
        for item in persisted_assistant_messages[0].get("tool_results", [])
        if item.get("tool") == "assistant.iteration"
    ]
    _assert(
        persisted_iteration_tools,
        f"Persisted assistant message missed iteration tool result: {persisted_assistant_messages[0]}",
    )
    persisted_version_items = [
        item
        for item in persisted_iteration_tools[0].get("items", [])
        if str(item.get("id")) == version["id"]
    ]
    _assert(
        persisted_version_items,
        f"Persisted assistant iteration tool missed version {version['id']}: {persisted_iteration_tools}",
    )
    _assert(
        persisted_version_items[0].get("next_actions"),
        f"Persisted assistant iteration tool missed version next_actions: {persisted_version_items[0]}",
    )
    _assert(
        persisted_version_items[0].get("delivery_stage_overview"),
        (
            "Persisted assistant iteration tool missed version "
            f"delivery_stage_overview: {persisted_version_items[0]}"
        ),
    )
    validate_version_dashboard_status_impact_projection(
        dashboard_status_impact,
        persisted_version_items[0].get("status_impact"),
        label="Persisted assistant iteration tool",
    )
    results.append(StepResult("assistant_qa", f"{assistant_message_id} / conversation={conversation_id}"))

    results.extend(
        validate_assistant_draft_governance(
            client,
            username=username,
            password=password,
        )
    )
    results.extend(
        validate_permission_visibility_quick_regression(
            client,
            username=username,
            password=password,
        )
    )

    results.append(StepResult("fixture_repository", str(repo_path)))
    return results


def run_regression_suite(
    client: ApiClient,
    *,
    suite: str,
    username: str,
    password: str,
    rd_e2e_scenario: str = "happy-path",
) -> list[StepResult]:
    results = regression_suite_header_results(suite)
    if suite == "full":
        results.extend(
            run_regression(
                client,
                username=username,
                password=password,
            )
        )
        return results
    if suite == "all-targeted":
        for targeted_suite in REGRESSION_TARGETED_SUITE_NAMES:
            child_results = run_regression_suite(
                client,
                suite=targeted_suite,
                username=username,
                password=password,
            )
            for child_result in child_results:
                if child_result.name in {"suite", "coverage"}:
                    continue
                results.append(
                    StepResult(
                        f"{targeted_suite}:{child_result.name}",
                        child_result.detail,
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
    if suite == "assistant-qa":
        results.extend(
            validate_assistant_qa_quick_regression(
                client,
                username=username,
                password=password,
            )
        )
        return results
    if suite == "code-inspection-governance":
        results.extend(
            validate_code_inspection_governance_quick_regression(
                client,
                username=username,
                password=password,
            )
        )
        return results
    if suite == "knowledge-index-health":
        results.extend(
            validate_knowledge_index_health_quick_regression(
                client,
                username=username,
                password=password,
            )
        )
        return results
    if suite == "permission-visibility":
        results.extend(
            validate_permission_visibility_quick_regression(
                client,
                username=username,
                password=password,
            )
        )
        return results
    if suite == "rd-collaboration":
        results.extend(
            validate_rd_collaboration_quick_regression(
                client,
                username=username,
                password=password,
            )
        )
        return results
    if suite == "rd-delivery-e2e":
        config = RdDeliveryE2EConfig.from_env()
        validation = (
            validate_rd_delivery_e2e(
                client,
                username,
                password,
                config,
            )
            if rd_e2e_scenario == "happy-path"
            else validate_rd_delivery_e2e(
                client,
                username,
                password,
                config,
                scenario=rd_e2e_scenario,
            )
        )
        results.extend(validation)
        return results
    raise RegressionError(f"Unsupported regression suite: {suite}")


def build_argument_parser() -> argparse.ArgumentParser:
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
        default=os.getenv("FULL_CHAIN_PASSWORD", os.getenv("READINESS_PASSWORD")),
        help="Login password. Defaults to FULL_CHAIN_PASSWORD or READINESS_PASSWORD.",
    )
    parser.add_argument(
        "--timeout",
        default=90.0,
        type=float,
        help="HTTP timeout in seconds per request.",
    )
    parser.add_argument(
        "--task-execution-mode",
        choices=["simulated_runner"],
        default=os.getenv("FULL_CHAIN_TASK_EXECUTION_MODE", "simulated_runner"),
        type=parse_task_execution_mode,
        help=(
            "AI task execution mode for tasks created internally by v2 collaboration. "
            "Only simulated_runner is supported by these regression suites; it validates "
            "the public Runner protocol without calling an external model gateway."
        ),
    )
    parser.add_argument(
        "--suite",
        choices=[
            "full",
            "all-targeted",
            "runner-reliability",
            "version-dashboard",
            "assistant-qa",
            "assistant-draft-governance",
            "code-inspection-governance",
            "knowledge-index-health",
            "permission-visibility",
            "rd-collaboration",
            "rd-delivery-e2e",
        ],
        default=os.getenv("FULL_CHAIN_SUITE", "full"),
        help=(
            "Regression suite to run. full executes the end-to-end product workflow; "
            "all-targeted executes every fast governance suite without the full "
            "feedback-to-assistant product workflow; "
            "runner-reliability executes only the AI executor Runner lease/dead-letter/cancel-retry gate; "
            "version-dashboard executes a quick product version dashboard aggregation "
            "with Bug, branch, review, release, and blocker gates; "
            "assistant-draft-governance executes the AI action draft "
            "governance/audit gate; assistant-qa executes deterministic assistant "
            "iteration governance Q&A, references, next_actions, and history gates; "
            "code-inspection-governance executes native scan, "
            "quality gate, Bug/task writeback, committer governance, trend comparison, "
            "and version dashboard blocker gates; knowledge-index-health executes a "
            "knowledge document, index health, permission scope, retrieval mode, and "
            "search hit gate; permission-visibility executes role list, permission "
            "matrix, readable scope names, menu permission gap, and user permission "
            "diagnostic gates; rd-collaboration executes requirement assessment, "
            "compatible-version grouping, a dependency-gated work-item DAG, and "
            "independent review through public APIs, stopping before delivery or deployment; "
            "rd-delivery-e2e is the explicit opt-in real Codex Runner, remote Git, "
            "independent gate, and ready-for-release suite and never deploys."
        ),
    )
    parser.add_argument(
        "--rd-e2e-scenario",
        choices=RD_E2E_SCENARIOS,
        default="happy-path",
        help=(
            "Governance scenario for the explicit rd-delivery-e2e suite. "
            "It is ignored by every other suite."
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
        default=os.getenv("FULL_CHAIN_USERNAME", os.getenv("READINESS_USERNAME")),
        help="Login username. Defaults to FULL_CHAIN_USERNAME or READINESS_USERNAME.",
    )
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    results: list[StepResult] = []
    started_at_iso = _utc_now_iso()
    started_at = time.perf_counter()
    try:
        username, password = validate_login_credentials(args.username, args.password)
        client = ApiClient(args.api_base_url, timeout=args.timeout)
        results = run_regression_suite(
            client,
            suite=args.suite,
            username=username,
            password=password,
            rd_e2e_scenario=args.rd_e2e_scenario,
        )
    except (RegressionError, AssertionError) as exc:
        finished_at_iso = _utc_now_iso()
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        if not results:
            try:
                results = regression_suite_header_results(args.suite)
            except RegressionError:
                results = [StepResult("suite", args.suite)]
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
