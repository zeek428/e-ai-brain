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

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from full_chain_regression_runner import validate_ai_executor_runner_reliability  # noqa: E402
from full_chain_regression_suites import (  # noqa: E402
    REGRESSION_TARGETED_SUITE_NAMES,
    regression_suite_coverage,
)
from full_chain_regression_version_dashboard import (  # noqa: E402
    validate_version_dashboard_blocker_actions,
    validate_version_dashboard_branch_quality,
    validate_version_dashboard_delivery_stage_overview,
    validate_version_dashboard_governance_conclusion,
    validate_version_dashboard_next_actions,
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


def validate_knowledge_index_health_quick_regression(
    client: ApiClient,
    *,
    username: str,
    password: str,
) -> list[StepResult]:
    slug = _slug()
    marker = f"knowledge-health-{slug}"
    results: list[StepResult] = []

    user = client.login(username, password).get("user", {})
    results.append(StepResult("login", f"logged in as {user.get('username') or username}"))

    document = client.post(
        "/api/knowledge/documents",
        {
            "content": (
                f"{marker}\n\n"
                "知识索引健康快速回归文档，用于验证文档创建、分块、权限命中、"
                "检索模式和搜索结果能够通过公开 API 闭环。"
            ),
            "doc_type": "runbook",
            "permission_roles": ["admin", "knowledge_owner", "rd_owner"],
            "tags": ["full-chain", "knowledge-index-health"],
            "title": f"知识索引健康快速回归 {slug}",
        },
    )
    document_id = str(document.get("id") or "")
    _assert(document_id, f"Knowledge document creation did not return id: {document}")
    _assert(
        document.get("index_status") in {"indexed", "text_indexed", "vector_indexed"},
        f"Knowledge document was not searchable after creation: {document}",
    )
    _assert(
        int(document.get("chunk_count") or 0) >= 1,
        f"Knowledge document creation did not create chunks: {document}",
    )
    results.append(
        StepResult(
            "knowledge_document",
            f"{document_id} / status={document.get('index_status')}",
        )
    )

    documents = client.get(
        "/api/knowledge/documents",
        {
            "keyword": marker,
            "page": 1,
            "page_size": 10,
            "permission_role": "admin",
            "sort_by": "created_at",
            "sort_order": "desc",
        },
    )
    document_items = documents.get("items", [])
    _assert_contains(_ids(document_items), document_id, "Knowledge document list missed created document")
    listed_document = next(item for item in document_items if str(item.get("id")) == document_id)
    _assert(
        int(listed_document.get("chunk_count") or 0) >= 1,
        f"Knowledge document list missed chunk count: {listed_document}",
    )
    _assert(
        "admin" in set(listed_document.get("permission_roles") or []),
        f"Knowledge document list missed permission role projection: {listed_document}",
    )

    knowledge_health = client.get(
        "/api/knowledge/index-health",
        {"issue_limit": 20, "keyword": marker, "permission_role": "admin"},
    )
    knowledge_health_summary = knowledge_health.get("summary") or {}
    _assert(
        int(knowledge_health_summary.get("total_documents") or 0) >= 1,
        f"Knowledge index health missed created document: {knowledge_health}",
    )
    _assert(
        int(knowledge_health_summary.get("searchable_documents") or 0) >= 1,
        f"Knowledge index health did not mark document searchable: {knowledge_health_summary}",
    )
    _assert(
        int(knowledge_health_summary.get("chunk_ready_documents") or 0) >= 1,
        f"Knowledge index health missed chunk-ready document: {knowledge_health_summary}",
    )
    _assert(
        int(knowledge_health_summary.get("total_chunks") or 0) >= 1,
        f"Knowledge index health missed chunks: {knowledge_health_summary}",
    )
    retrieval_modes = knowledge_health.get("retrieval_modes") or {}
    _assert(
        int(retrieval_modes.get("hybrid_ready") or 0) + int(retrieval_modes.get("keyword_fallback") or 0) >= 1,
        f"Knowledge index health did not expose usable retrieval mode: {retrieval_modes}",
    )
    _assert(
        int(retrieval_modes.get("unavailable") or 0) == 0,
        f"Knowledge index health marked the new searchable document unavailable: {retrieval_modes}",
    )
    permission_scope = knowledge_health.get("permission_scope") or {}
    _assert(
        permission_scope.get("mode") == "role_based",
        f"Knowledge index health missed role-based permission scope: {permission_scope}",
    )
    _assert(
        "admin" in set(permission_scope.get("matched_roles") or []),
        f"Knowledge index health missed admin role match: {permission_scope}",
    )
    _assert(
        permission_scope.get("scope_labels"),
        f"Knowledge index health missed readable permission scope labels: {permission_scope}",
    )
    document_health_issues = [
        issue for issue in knowledge_health.get("items", []) if str(issue.get("document_id")) == document_id
    ]
    if document.get("index_status") == "text_indexed":
        _assert(
            any(
                issue.get("action") == "retry_index"
                and issue.get("severity") == "warning"
                and issue.get("status") == "text_indexed"
                for issue in document_health_issues
            ),
            f"Knowledge index health missed vector-backfill warning for text-indexed document: {document_health_issues}",
        )
    else:
        _assert(
            not document_health_issues,
            f"Knowledge index health reported an issue for a vector-ready document: {document_health_issues}",
        )

    knowledge_search = client.post("/api/knowledge/search", {"query": marker, "top_k": 5})
    search_items = knowledge_search.get("items", [])
    search_document_ids = {str(item.get("document_id")) for item in search_items}
    _assert_contains(
        search_document_ids,
        document_id,
        "Knowledge search did not retrieve created document",
    )
    _assert(
        any(item.get("retrieval_mode") in {"keyword", "vector"} for item in search_items),
        f"Knowledge search did not return retrieval mode: {search_items}",
    )
    results.append(
        StepResult(
            "knowledge_index_health_quick",
            (
                f"{document_id} / chunks={knowledge_health_summary.get('total_chunks')} / "
                f"mode={permission_scope.get('mode')}"
            ),
        )
    )
    results.append(
        StepResult(
            "knowledge_search",
            f"hits={len(search_items)} / document={document_id}",
        )
    )
    return results


def validate_permission_visibility_quick_regression(
    client: ApiClient,
    *,
    username: str,
    password: str,
) -> list[StepResult]:
    slug = _slug()
    code_suffix = slug.replace("-", "_")
    results: list[StepResult] = []

    user = client.login(username, password).get("user", {})
    results.append(StepResult("login", f"logged in as {user.get('username') or username}"))

    scoped_product = client.post(
        "/api/products",
        {
            "code": f"permission-scope-{slug}",
            "description": "权限可视化快速回归脚本创建的产品范围。",
            "name": f"权限可视化产品范围 {slug}",
            "status": "active",
        },
    )
    blocked_product = client.post(
        "/api/products",
        {
            "code": f"permission-blocked-{slug}",
            "description": "权限可视化快速回归脚本创建的未授权产品范围。",
            "name": f"权限可视化未授权产品 {slug}",
            "status": "active",
        },
    )
    knowledge_space = client.post(
        "/api/knowledge/spaces",
        {
            "code": f"permission-space-{slug}",
            "description": "权限可视化快速回归脚本创建的知识空间范围。",
            "name": f"权限可视化知识空间 {slug}",
        },
    )
    results.append(
        StepResult(
            "permission_visibility_scope_resources",
            f"{scoped_product['id']} / {knowledge_space['id']}",
        )
    )

    gap_role_code = f"perm_gap_{code_suffix}"
    gap_role = client.post(
        "/api/system/roles",
        {
            "category": "workspace",
            "code": gap_role_code,
            "description": "权限可视化快速回归：菜单已授权但缺少权限点。",
            "name": f"权限可视化菜单缺口 {slug}",
        },
    )
    client.request(
        "PUT",
        f"/api/system/roles/{gap_role['id']}/menus",
        body={"menu_codes": ["workspace.dashboard"]},
    )

    scope_role_code = f"perm_scope_{code_suffix}"
    scope_role = client.post(
        "/api/system/roles",
        {
            "category": "workspace",
            "code": scope_role_code,
            "description": "权限可视化快速回归：产品和知识空间范围投影。",
            "name": f"权限可视化范围角色 {slug}",
        },
    )
    client.request(
        "PUT",
        f"/api/system/roles/{scope_role['id']}/menus",
        body={"menu_codes": ["task.center"]},
    )
    client.request(
        "PUT",
        f"/api/system/roles/{scope_role['id']}/scopes",
        body={
            "scopes": [
                {
                    "access_level": "read",
                    "scope_id": scoped_product["id"],
                    "scope_type": "product",
                },
                {
                    "access_level": "read",
                    "scope_id": knowledge_space["id"],
                    "scope_type": "knowledge_space",
                },
            ]
        },
    )
    results.append(
        StepResult(
            "permission_visibility_roles",
            f"{gap_role_code} / {scope_role_code}",
        )
    )

    listed_roles = client.get(
        "/api/system/roles",
        {
            "page": 1,
            "page_size": 10,
            "role": "权限可视化",
            "sort_by": "code",
            "sort_order": "asc",
            "status": "active",
        },
    )
    role_codes = {str(item.get("code") or "") for item in listed_roles.get("items", [])}
    _assert_contains(role_codes, gap_role_code, "Role list missed permission gap role")
    _assert_contains(role_codes, scope_role_code, "Role list missed scoped role")
    _assert(
        listed_roles.get("performance"),
        f"Role list did not include observability metadata: {listed_roles}",
    )
    _assert(
        (listed_roles.get("query") or {}).get("sort_by") == "code",
        f"Role list did not echo remote sort field: {listed_roles}",
    )

    matrix = client.get("/api/system/permissions/matrix")
    matrix_rows = matrix.get("rows") or []
    gap_row = next(
        (row for row in matrix_rows if row.get("role_code") == gap_role_code),
        None,
    )
    _assert(gap_row is not None, f"Permission matrix missed gap role: {matrix_rows}")
    _assert(
        "workspace.read" in set(gap_row.get("missing_menu_permission_codes") or []),
        f"Permission matrix missed workspace.read menu gap: {gap_row}",
    )
    _assert(
        any(item.get("code") == "menu_permission_gap" for item in gap_row.get("diagnostics") or []),
        f"Permission matrix missed menu_permission_gap diagnostic: {gap_row}",
    )

    scope_row = next(
        (row for row in matrix_rows if row.get("role_code") == scope_role_code),
        None,
    )
    _assert(scope_row is not None, f"Permission matrix missed scoped role: {matrix_rows}")
    scope_entries = scope_row.get("scopes") or []
    product_scope = next(
        (
            scope
            for scope in scope_entries
            if scope.get("scope_type") == "product"
            and scope.get("scope_id") == scoped_product["id"]
        ),
        None,
    )
    knowledge_scope = next(
        (
            scope
            for scope in scope_entries
            if scope.get("scope_type") == "knowledge_space"
            and scope.get("scope_id") == knowledge_space["id"]
        ),
        None,
    )
    _assert(
        product_scope and product_scope.get("scope_name") == scoped_product["name"],
        f"Permission matrix missed product scope name: {scope_row}",
    )
    _assert(
        knowledge_scope and knowledge_scope.get("scope_name") == knowledge_space["name"],
        f"Permission matrix missed knowledge space scope name: {scope_row}",
    )
    _assert(
        "产品 1 项" in str(scope_row.get("scope_summary") or "")
        and "知识空间 1 项" in str(scope_row.get("scope_summary") or ""),
        f"Permission matrix missed readable scope summary: {scope_row}",
    )
    _assert(
        int((matrix.get("summary") or {}).get("roles_with_menu_permission_gaps") or 0) >= 1,
        f"Permission matrix summary missed menu gap count: {matrix.get('summary')}",
    )
    results.append(
        StepResult(
            "permission_visibility_matrix",
            (
                f"gap={gap_row.get('missing_menu_permission_codes')} / "
                f"scopes={scope_row.get('scope_summary')}"
            ),
        )
    )

    role_detail = client.get(f"/api/system/roles/{scope_role['id']}")
    _assert(
        str(role_detail.get("code") or "") == scope_role_code,
        f"Role detail returned the wrong role: {role_detail}",
    )
    _assert(
        any(scope.get("scope_id") == scoped_product["id"] for scope in role_detail.get("scopes") or []),
        f"Role detail missed product scope grant: {role_detail}",
    )
    access_preview = role_detail.get("access_preview") or {}
    _assert(
        access_preview.get("role_code") == scope_role_code,
        f"Role detail access preview missed role code: {role_detail}",
    )
    _assert(
        any(menu.get("code") == "task.center" and menu.get("path") == "/delivery/rd-tasks" for menu in access_preview.get("visible_menus") or []),
        f"Role detail access preview missed visible menu path: {access_preview}",
    )
    _assert(
        access_preview.get("missing_menu_permission_codes") == ["task.read"],
        f"Role detail access preview missed menu permission gap: {access_preview}",
    )
    _assert(
        any(item.get("code") == "menu_permission_gap" for item in access_preview.get("diagnostics") or []),
        f"Role detail access preview missed menu gap diagnostic: {access_preview}",
    )
    _assert(
        not access_preview.get("operation_permissions"),
        f"Role detail access preview should show no granted operation permissions: {access_preview}",
    )
    _assert(
        {group.get("scope_type") for group in access_preview.get("scope_groups") or []}
        >= {"knowledge_space", "product"},
        f"Role detail access preview missed scope groups: {access_preview}",
    )
    _assert(
        any(
            scope.get("scope_id") == scoped_product["id"]
            and scope.get("scope_name") == scoped_product["name"]
            for scope in access_preview.get("scopes") or []
        ),
        f"Role detail access preview missed readable product scope: {access_preview}",
    )
    results.append(
        StepResult(
            "permission_visibility_role_preview",
            (
                f"menus={access_preview.get('menu_count')} / "
                f"scopes={access_preview.get('scope_summary')}"
            ),
        )
    )

    diagnostic_user = client.post(
        "/api/users",
        {
            "display_name": f"权限诊断用户 {slug}",
            "password": "diagnostic123",
            "roles": ["viewer"],
            "status": "active",
            "username": f"permission-visibility-{slug}@example.com",
        },
    )
    client.request(
        "PUT",
        f"/api/users/{diagnostic_user['id']}/roles",
        body={"role_codes": [scope_role_code]},
    )
    diagnostic = client.get(
        "/api/system/permissions/diagnostics",
        {
            "path": "/delivery/rd-tasks",
            "permission_code": "task.read",
            "scope_id": blocked_product["id"],
            "scope_type": "product",
            "user_id": diagnostic_user["id"],
        },
    )
    blocked_reasons = diagnostic.get("decision", {}).get("blocked_reasons") or []
    _assert(
        diagnostic.get("decision", {}).get("allowed") is False,
        f"Permission diagnostics unexpectedly allowed blocked user: {diagnostic}",
    )
    _assert(
        "缺少菜单权限：task.read" in blocked_reasons,
        f"Permission diagnostics missed menu permission block: {diagnostic}",
    )
    _assert(
        "缺少权限点：task.read" in blocked_reasons,
        f"Permission diagnostics missed permission block: {diagnostic}",
    )
    _assert(
        f"缺少范围：product:{blocked_product['id']}" in blocked_reasons,
        f"Permission diagnostics missed product scope block: {diagnostic}",
    )
    checks = {check.get("code"): check for check in diagnostic.get("checks") or []}
    _assert(
        (checks.get("menu_path") or {}).get("granted_menu_code") == "task.center",
        f"Permission diagnostics missed granted menu evidence: {diagnostic}",
    )
    _assert(
        (checks.get("permission") or {}).get("status") == "blocked",
        f"Permission diagnostics missed blocked permission check: {diagnostic}",
    )
    _assert(
        (checks.get("scope") or {}).get("status") == "blocked",
        f"Permission diagnostics missed blocked scope check: {diagnostic}",
    )
    effective_scopes = diagnostic.get("effective", {}).get("scopes") or []
    _assert(
        any(
            scope.get("scope_id") == scoped_product["id"]
            and scope.get("scope_name") == scoped_product["name"]
            for scope in effective_scopes
        ),
        f"Permission diagnostics missed readable effective scope: {diagnostic}",
    )
    results.append(
        StepResult(
            "permission_visibility_diagnostics",
            f"user={diagnostic_user['id']} / blocked={len(blocked_reasons)}",
        )
    )
    return results


def validate_code_inspection_governance_quick_regression(
    client: ApiClient,
    *,
    username: str,
    password: str,
) -> list[StepResult]:
    slug = _slug()
    version_branch = f"inspection/{slug}"
    repo_path = create_fixture_repository(slug, version_branch)
    results: list[StepResult] = []

    user = client.login(username, password).get("user", {})
    results.append(StepResult("login", f"logged in as {user.get('username') or username}"))

    product = client.post(
        "/api/products",
        {
            "code": f"inspection-{slug}",
            "description": "自动代码巡检治理快速回归脚本创建的产品数据。",
            "name": f"代码巡检治理快速回归产品 {slug}",
            "status": "active",
        },
    )
    version = client.post(
        f"/api/products/{product['id']}/versions",
        {
            "code": f"inspection-{slug}",
            "description": "自动代码巡检治理快速回归版本。",
            "name": f"代码巡检治理快速回归版本 {slug}",
            "status": "active",
        },
    )
    results.append(StepResult("code_inspection_product", f"{product['id']} / {version['id']}"))

    repository = client.post(
        f"/api/products/{product['id']}/git-repositories",
        {
            "default_branch": "main",
            "git_provider": "github",
            "name": f"代码巡检治理快速回归仓库 {slug}",
            "project_path": f"inspection/{slug}",
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
            "description": "代码巡检治理快速回归分支。",
            "repository_id": repository["id"],
            "working_branch": version_branch,
        },
    )
    results.append(
        StepResult("code_inspection_branch", f"{branch_config['id']} / {version_branch}")
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
            "name": f"代码巡检治理快速回归 {slug}",
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
    scan_run_summary = scan_run.get("result_summary") or {}
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
    report_id = str(scan_run_summary.get("report_id") or "")
    _assert(report_id, f"Code inspection run did not return report_id: {scan_run}")

    report_detail = client.get(f"/api/governance/code-inspections/{report_id}")
    report = report_detail["report"]
    findings = report_detail.get("findings", [])
    scan_summary = report_detail.get("scan_summary") or {}
    governance_summary = report_detail.get("governance_summary") or {}
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
    for expected_rule in {"secrets.hardcoded_credential", "metadata.internal_address_exposure"}:
        _assert(
            any(finding.get("rule_id") == expected_rule for finding in findings),
            f"Native scan did not detect {expected_rule}: {findings}",
        )
    coverage = scan_summary.get("coverage") or {}
    _assert(int(coverage.get("files_scanned") or 0) >= 2, f"Scan coverage is incomplete: {coverage}")
    _assert(
        any(
            item.get("email") == "full-chain@example.com"
            for item in scan_summary.get("committer_distribution", [])
        ),
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
        any(
            int(item.get("quality_gate_failed_count") or 0) >= 1
            for item in inspection_dashboard.get("trend", [])
        ),
        f"Code inspection dashboard trend missed quality gate failure: {inspection_dashboard.get('trend')}",
    )
    _assert(
        inspection_dashboard.get("quality_gate_violations"),
        f"Code inspection dashboard missed quality gate violation aggregation: {inspection_dashboard}",
    )
    governance_pressure = inspection_dashboard.get("governance_pressure") or {}
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
    bugs = client.get("/api/bugs", {"product_id": product["id"], "source": "code_inspection"})
    bug_items = bugs.get("items", [])
    bug_ids = _ids(bug_items)
    for bug_id in report_bug_ids:
        _assert_contains(bug_ids, bug_id, "Code inspection Bug writeback missing from Bug list")
    _assert(
        all(
            item.get("evidence", {}).get("code_inspection_report_id") == report_id
            for item in bug_items
            if item["id"] in report_bug_ids
        ),
        "Code inspection Bug evidence did not point back to the report.",
    )
    remediation_tasks = client.get(
        "/api/ai-tasks",
        {"product_id": product["id"], "task_type": "code_inspection_remediation"},
    )
    remediation_task_ids = _ids(remediation_tasks.get("items", []))
    for remediation_task_id in report_task_ids:
        _assert_contains(
            remediation_task_ids,
            remediation_task_id,
            "Code inspection remediation task writeback missing from AI task list",
        )

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
    results.append(
        StepResult(
            "inspection_writeback",
            f"bugs={len(report_bug_ids)}, tasks={len(report_task_ids)}",
        )
    )

    comparison_scan_job = client.post(
        "/api/system/scheduled-jobs",
        {
            "config_json": scan_config,
            "enabled": True,
            "execution_mode": "deterministic",
            "job_type": "code_repository_inspection",
            "name": f"代码巡检治理趋势对比 {slug}",
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
    comparison_report_id = str((comparison_scan_run.get("result_summary") or {}).get("report_id") or "")
    _assert(
        comparison_report_id,
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
        comparison_report.get("previous_report_id") == report_id,
        f"Comparison report did not persist previous_report_id={report_id}: {comparison_report}",
    )
    _assert(
        comparison_previous.get("previous_report_id") == report_id,
        f"Comparison report missed previous comparison report id: {comparison_previous}",
    )
    _assert(
        int(comparison_previous.get("previous_finding_count") or -1)
        == int(report.get("finding_count") or 0),
        f"Comparison report previous finding count mismatch: {comparison_previous}",
    )
    _assert(
        int(comparison_previous.get("finding_delta") or 0) == 0,
        f"Comparison report should have stable finding_delta for unchanged fixture: {comparison_previous}",
    )
    _assert(
        int(comparison_previous.get("severe_finding_delta") or 0) == 0,
        f"Comparison report should have stable severe_finding_delta: {comparison_previous}",
    )
    results.append(
        StepResult(
            "code_inspection_trend_comparison",
            f"{comparison_report_id} / previous={comparison_previous.get('previous_report_id')}",
        )
    )

    dashboard = client.get(f"/api/product-versions/{version['id']}/dashboard")
    _assert_contains(
        _ids(dashboard.get("branch_configs", [])),
        branch_config["id"],
        "Version dashboard missed code inspection branch config",
    )
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
    dashboard_blockers = dashboard.get("blockers", [])
    validate_version_dashboard_blocker_actions(dashboard_blockers)
    validate_version_dashboard_next_actions(dashboard, dashboard_blockers)
    validate_version_dashboard_governance_conclusion(dashboard, dashboard_blockers)
    validate_version_dashboard_delivery_stage_overview(dashboard)
    validate_version_dashboard_status_impact(dashboard)
    inspection_blockers = [
        blocker
        for blocker in dashboard_blockers
        if blocker.get("source_type") == "code_inspection_report"
        and str(blocker.get("action_target_id")) == report_id
    ]
    _assert(inspection_blockers, "Version dashboard missed actionable code inspection blocker.")
    bug_blockers = [
        blocker
        for blocker in dashboard_blockers
        if blocker.get("source_type") == "bug" and str(blocker.get("action_target_id")) in report_bug_ids
    ]
    _assert(bug_blockers, "Version dashboard missed actionable Bug blocker.")
    results.append(
        StepResult(
            "version_dashboard_code_inspection_governance",
            f"blockers={dashboard['summary']['blockers']} / branch_quality={branch_quality['status']}",
        )
    )
    results.append(StepResult("fixture_repository", str(repo_path)))
    return results


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
    validate_version_dashboard_status_impact(dashboard)
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
    code_review_blockers = [
        blocker
        for blocker in dashboard_blockers
        if blocker.get("source_type") == "code_review_report"
        and str(blocker.get("action_target_id")) == code_review_report["id"]
    ]
    _assert(
        code_review_blockers,
        f"Version dashboard quick check missed pending code review blocker: {dashboard_blockers}",
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
            f"blockers={dashboard['summary']['blockers']}, tasks={dashboard['summary']['tasks']}",
        )
    )
    results.append(StepResult("fixture_repository", str(repo_path)))
    return results


def validate_assistant_qa_quick_regression(
    client: ApiClient,
    *,
    username: str,
    password: str,
) -> list[StepResult]:
    slug = _slug()
    results: list[StepResult] = []

    user = client.login(username, password).get("user", {})
    results.append(StepResult("login", f"logged in as {user.get('username') or username}"))

    product = client.post(
        "/api/products",
        {
            "code": f"assistant-qa-{slug}",
            "description": "自动 AI 助手问答快速回归脚本创建的产品数据。",
            "name": f"AI 助手问答快速回归产品 {slug}",
            "status": "active",
        },
    )
    version = client.post(
        f"/api/products/{product['id']}/versions",
        {
            "code": f"assistant-qa-{slug}",
            "description": "自动 AI 助手问答快速回归版本。",
            "name": f"AI 助手问答快速回归版本 {slug}",
            "status": "active",
        },
    )
    requirement = client.post(
        "/api/requirements",
        {
            "content": "AI 助手需要能回答迭代版本阻塞项、版本总览和下一步行动。",
            "priority": "P1",
            "product_id": product["id"],
            "source": "product_planning",
            "title": f"AI 助手问答快速回归需求 {slug}",
            "version_id": version["id"],
        },
    )
    approved = client.post(
        f"/api/requirements/{requirement['id']}/approve",
        {"comment": "AI 助手问答快速回归审批通过"},
    )
    _assert(
        approved.get("status") in {"approved", "planned"},
        f"Assistant QA requirement was not approved: {approved}",
    )
    task = client.post(f"/api/requirements/{requirement['id']}/generate-task")
    task_id = str(task["task_id"])
    started = client.post(
        f"/api/ai-tasks/{task_id}/start",
        {
            "execution_mode": "deterministic",
            "reason": "assistant QA quick regression prepares progress context",
        },
    )
    _assert(
        started.get("status") == "waiting_review",
        f"Assistant QA task did not enter waiting_review: {started}",
    )
    approved_review = client.post(
        f"/api/reviews/{started['review_id']}/approve",
        {"version": 1},
    )
    _assert(
        approved_review.get("task_status") == "completed",
        f"Assistant QA review did not complete task: {approved_review}",
    )

    bug = client.post(
        "/api/bugs",
        {
            "description": "AI 助手问答快速回归制造一个版本阻塞缺陷。",
            "product_id": product["id"],
            "related_task_id": task_id,
            "requirement_id": requirement["id"],
            "severity": "critical",
            "source": "manual_test",
            "title": f"AI 助手问答阻塞 Bug {slug}",
            "version_id": version["id"],
        },
    )
    version_testing = client.post(
        f"/api/product-versions/{version['id']}/advance-status",
        {
            "force": True,
            "reason": "assistant QA quick regression checks iteration governance answer",
            "target_status": "testing",
        },
    )
    _assert(
        version_testing.get("version", {}).get("status") == "testing",
        f"Assistant QA version did not advance to testing: {version_testing}",
    )

    dashboard = client.get(f"/api/product-versions/{version['id']}/dashboard")
    dashboard_blockers = dashboard.get("blockers", [])
    _assert(
        int((dashboard.get("summary") or {}).get("blockers") or 0) >= 1,
        f"Assistant QA fixture did not expose version blockers: {dashboard}",
    )
    validate_version_dashboard_blocker_actions(dashboard_blockers)
    validate_version_dashboard_next_actions(dashboard, dashboard_blockers)
    validate_version_dashboard_governance_conclusion(dashboard, dashboard_blockers)
    validate_version_dashboard_delivery_stage_overview(dashboard)
    dashboard_status_impact = validate_version_dashboard_status_impact(dashboard)

    assistant = client.post(
        "/api/assistant/chat",
        {
            "client_request_id": f"assistant-qa-regression-{slug}",
            "message": "请总结当前迭代版本阻塞项、版本总览和下一步行动",
            "product_id": product["id"],
            "references": [{"id": version["id"], "type": "product_version"}],
        },
    )
    _assert(
        assistant.get("model") == "assistant-deterministic",
        f"Assistant QA quick check should use deterministic iteration governance: {assistant}",
    )
    assistant_message = assistant.get("message") or {}
    assistant_message_id = str(assistant_message.get("id") or "")
    _assert(assistant_message_id, f"Assistant QA response missed message id: {assistant}")
    assistant_reference_keys = {
        (reference.get("type"), reference.get("id"))
        for reference in assistant_message.get("references", [])
    }
    _assert(
        ("product_version", version["id"]) in assistant_reference_keys,
        f"Assistant QA response missed product version reference: {assistant_message.get('references')}",
    )
    iteration_tools = [
        item
        for item in assistant_message.get("tool_results", [])
        if item.get("tool") == "assistant.iteration"
    ]
    _assert(iteration_tools, f"Assistant QA response missed iteration tool result: {assistant_message}")
    version_items = [
        item
        for item in iteration_tools[0].get("items", [])
        if str(item.get("id")) == version["id"]
    ]
    _assert(version_items, f"Assistant QA iteration tool missed version {version['id']}: {iteration_tools}")
    version_item = version_items[0]
    _assert(
        int(version_item.get("blocker_count") or 0)
        == int((dashboard.get("summary") or {}).get("blockers") or 0),
        f"Assistant QA blocker count drifted from version dashboard: {version_item}",
    )
    dashboard_next_action_sources = [
        str(item.get("source_type") or "") for item in dashboard.get("next_actions", [])
    ]
    assistant_next_action_sources = [
        str(item.get("source_type") or "")
        for item in version_item.get("next_actions", [])
    ]
    _assert(
        assistant_next_action_sources == dashboard_next_action_sources[:3],
        (
            "Assistant QA next_actions drifted from version dashboard: "
            f"assistant={version_item.get('next_actions')}, dashboard={dashboard.get('next_actions')}"
        ),
    )
    dashboard_stage_keys = [
        str(item.get("key") or "")
        for item in dashboard.get("delivery_stage_overview", [])
    ]
    assistant_stage_keys = [
        str(item.get("key") or "") for item in version_item.get("delivery_stage_overview", [])
    ]
    _assert(
        assistant_stage_keys == dashboard_stage_keys[:9],
        (
            "Assistant QA delivery_stage_overview drifted from version dashboard: "
            f"assistant={version_item.get('delivery_stage_overview')}, "
            f"dashboard={dashboard.get('delivery_stage_overview')}"
        ),
    )
    dashboard_conclusion = dashboard.get("governance_conclusion") or {}
    assistant_conclusion = version_item.get("governance_conclusion") or {}
    for field in ("level", "value"):
        _assert(
            assistant_conclusion.get(field) == dashboard_conclusion.get(field),
            (
                "Assistant QA governance_conclusion drifted from version dashboard: "
                f"field={field}, assistant={assistant_conclusion}, dashboard={dashboard_conclusion}"
            ),
        )
    validate_version_dashboard_status_impact_projection(
        dashboard_status_impact,
        version_item.get("status_impact"),
        label="Assistant QA",
    )
    conversation_id = assistant.get("conversation_id") or assistant.get("run", {}).get("conversation_id")
    _assert(conversation_id, f"Assistant QA response missing conversation id: {assistant}")
    conversation_messages = client.get(f"/api/assistant/conversations/{conversation_id}/messages")
    persisted_messages = conversation_messages.get("items", [])
    _assert(
        len(persisted_messages) >= 2,
        f"Assistant QA conversation history was not persisted: {conversation_messages}",
    )
    persisted_assistant = [
        item for item in persisted_messages if item.get("id") == assistant_message_id
    ]
    _assert(persisted_assistant, f"Assistant QA message not found in history: {conversation_messages}")
    persisted_iteration_tools = [
        item
        for item in persisted_assistant[0].get("tool_results", [])
        if item.get("tool") == "assistant.iteration"
    ]
    _assert(
        persisted_iteration_tools,
        f"Assistant QA history missed iteration tool result: {persisted_assistant[0]}",
    )
    persisted_version_items = [
        item
        for item in persisted_iteration_tools[0].get("items", [])
        if str(item.get("id")) == version["id"]
    ]
    _assert(
        persisted_version_items and persisted_version_items[0].get("next_actions"),
        f"Assistant QA history missed version next_actions: {persisted_iteration_tools}",
    )
    _assert(
        persisted_version_items[0].get("delivery_stage_overview"),
        f"Assistant QA history missed version delivery_stage_overview: {persisted_version_items[0]}",
    )
    validate_version_dashboard_status_impact_projection(
        dashboard_status_impact,
        persisted_version_items[0].get("status_impact"),
        label="Assistant QA history",
    )
    results.append(
        StepResult(
            "assistant_qa_quick",
            (
                f"{assistant_message_id} / version={version['id']} / "
                f"bug={bug['id']} / blockers={version_item.get('blocker_count')}"
            ),
        )
    )
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
            (
                f"blockers={dashboard['summary']['blockers']}, "
                f"blocker_actions={len(dashboard_blockers)}, "
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
    task_execution_mode: str,
    username: str,
    password: str,
) -> list[StepResult]:
    results = regression_suite_header_results(suite)
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
    if suite == "all-targeted":
        for targeted_suite in REGRESSION_TARGETED_SUITE_NAMES:
            child_results = run_regression_suite(
                client,
                suite=targeted_suite,
                task_execution_mode=task_execution_mode,
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
        ],
        default=os.getenv("FULL_CHAIN_SUITE", "full"),
        help=(
            "Regression suite to run. full executes the end-to-end product workflow; "
            "all-targeted executes every fast governance suite without the full "
            "feedback-to-assistant product workflow; "
            "runner-reliability executes only the AI executor Runner lease/dead-letter gate; "
            "version-dashboard executes a quick product version dashboard aggregation "
            "and blocker gate; assistant-draft-governance executes the AI action draft "
            "governance/audit gate; assistant-qa executes deterministic assistant "
            "iteration governance Q&A, references, next_actions, and history gates; "
            "code-inspection-governance executes native scan, "
            "quality gate, Bug/task writeback, committer governance, trend comparison, "
            "and version dashboard blocker gates; knowledge-index-health executes a "
            "knowledge document, index health, permission scope, retrieval mode, and "
            "search hit gate; permission-visibility executes role list, permission "
            "matrix, readable scope names, menu permission gap, and user permission "
            "diagnostic gates."
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
